"""The Portscout Textual application (driving adapter for the use cases)."""

from __future__ import annotations

import re
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
    Switch,
)

from ..application.services import ConfigService, DependencyService, ScanService
from ..domain.entities import ScanRequest, ScanResult
from ..domain.ports import ScanError
from ..domain.value_objects import (
    BUILTIN_PROFILES,
    InvalidPortSpecError,
    InvalidTargetError,
    get_profile,
)
from .screens import DependencyScreen, DisclaimerScreen, SettingsScreen

# nmap "--stats-every" emits lines like "SYN Stealth Scan Timing: About 42.10% done".
_PERCENT_RE = re.compile(r"About\s+([\d.]+)%\s+done")
_ETC_RE = re.compile(r"\(([^)]*remaining)\)")


class PortscoutApp(App[None]):
    """A friendly, graphical nmap front-end."""

    CSS_PATH = "styles.tcss"
    TITLE = "Portscout"
    SUB_TITLE = "a friendly nmap TUI"

    BINDINGS = [
        ("s", "scan", "Scan"),
        ("x", "cancel", "Stop"),
        ("c", "settings", "Settings"),
        ("d", "dependencies", "Deps"),
        ("ctrl+l", "clear_log", "Clear log"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        scan_service: ScanService,
        dependency_service: DependencyService,
        config_service: ConfigService,
    ) -> None:
        super().__init__()
        self._scan = scan_service
        self._deps = dependency_service
        self._config_service = config_service
        self._config = config_service.load()
        self._scan_worker = None

    # --- Layout ---------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="controls"):
                yield Label("Target (IP, CIDR or hostname)")
                yield Input(placeholder="192.168.1.0/24", id="target")
                yield Label("Scan profile")
                yield Select(
                    [(p.label, p.key) for p in BUILTIN_PROFILES],
                    value=self._default_profile_key(),
                    id="profile",
                    allow_blank=False,
                )
                yield Static("", id="profile-desc", classes="status-warn")
                yield Label("Custom ports (optional)")
                yield Input(placeholder="22,80,8000-8100", id="ports")
                with Horizontal():
                    yield Label("Elevated (sudo) scan")
                    yield Switch(id="privileged")
                yield Button("▶  Start scan", variant="success", id="scan-button")
            with Vertical(id="results"):
                yield Static("$ command preview appears here", id="command-preview")
                yield ProgressBar(id="progress", show_eta=False, total=None)
                yield RichLog(id="log", highlight=True, markup=True, wrap=True)
                yield DataTable(id="table", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("Host", "Hostname", "Port", "Proto", "State", "Service")
        self.query_one("#progress", ProgressBar).display = False
        self._update_profile_description()
        self._refresh_preview()
        if not self._config.disclaimer_accepted:
            self._prompt_disclaimer()
        else:
            self._warn_missing_dependencies()

    # --- Disclaimer gate ------------------------------------------------------

    def _prompt_disclaimer(self) -> None:
        def handle(accepted: bool | None) -> None:
            if not accepted:
                self.exit()
                return
            self._config = self._config_service.accept_disclaimer()
            self.notify("Thanks — scan responsibly and only what you're authorized to.")
            self._warn_missing_dependencies()

        self.push_screen(DisclaimerScreen(), handle)

    def _warn_missing_dependencies(self) -> None:
        issue = self._deps.blocking_issue()
        if issue:
            self.notify(issue, title="Dependency missing", severity="error", timeout=10)

    # --- Reactivity: keep the command preview live ----------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._update_profile_description()
        self._refresh_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        self._refresh_preview()

    def _default_profile_key(self) -> str:
        try:
            get_profile(self._config.default_profile)
            return self._config.default_profile
        except KeyError:
            return "standard"

    def _current_profile_key(self) -> str:
        value = self.query_one("#profile", Select).value
        return str(value) if value is not None else "standard"

    def _update_profile_description(self) -> None:
        profile = get_profile(self._current_profile_key())
        note = "  (needs sudo)" if profile.requires_privilege else ""
        self.query_one("#profile-desc", Static).update(profile.description + note)

    def _build_request(self) -> ScanRequest:
        target = self.query_one("#target", Input).value
        ports = self.query_one("#ports", Input).value
        privileged = self.query_one("#privileged", Switch).value
        profile = get_profile(self._current_profile_key())
        return self._scan.build_request(target, profile, ports, privileged)

    def _refresh_preview(self) -> None:
        preview = self.query_one("#command-preview", Static)
        try:
            request = self._build_request()
        except (InvalidTargetError, InvalidPortSpecError) as exc:
            preview.update(f"[dim]awaiting valid input — {exc}[/dim]")
            return
        preview.update(f"$ {self._scan.preview(request)}")

    # --- Scanning -------------------------------------------------------------

    def action_scan(self) -> None:
        if not self._config.disclaimer_accepted:
            self._prompt_disclaimer()
            return
        if self._scan_worker is not None and self._scan_worker.is_running:
            self.notify("A scan is already running.", severity="warning")
            return
        try:
            request = self._build_request()
        except (InvalidTargetError, InvalidPortSpecError) as exc:
            self.notify(str(exc), title="Invalid input", severity="error")
            return

        log = self.query_one("#log", RichLog)
        log.clear()
        self.query_one("#table", DataTable).clear()
        progress = self.query_one("#progress", ProgressBar)
        progress.display = True
        progress.update(total=None)  # indeterminate until nmap reports a percentage
        self.query_one("#scan-button", Button).disabled = True
        self.notify(f"Scanning {request.target}…", title="Scan started")
        self._scan_worker = self._run_scan(request)

    def action_cancel(self) -> None:
        if self._scan_worker is not None and self._scan_worker.is_running:
            self._scan_worker.cancel()
            self.notify("Scan cancelled.", severity="warning")
            self._finish_scan()

    @work(thread=True, exclusive=True)
    def _run_scan(self, request: ScanRequest) -> None:
        def on_progress(line: str) -> None:
            self.call_from_thread(self._handle_progress_line, line)

        try:
            result = self._scan.run(request, on_progress)
        except ScanError as exc:
            self.call_from_thread(self._on_scan_failed, str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the UI
            self.call_from_thread(self._on_scan_failed, f"Unexpected error: {exc}")
            return
        self.call_from_thread(self._on_scan_complete, result)

    def _handle_progress_line(self, line: str) -> None:
        self.query_one("#log", RichLog).write(line)
        progress = self.query_one("#progress", ProgressBar)
        match = _PERCENT_RE.search(line)
        if match:
            percent = float(match.group(1))
            if progress.total is None:
                progress.update(total=100.0)
            progress.update(progress=percent)
            etc = _ETC_RE.search(line)
            suffix = f" — {etc.group(1)}" if etc else ""
            self.query_one("#command-preview", Static).update(
                f"[b]scanning[/b] {percent:.1f}%{suffix}"
            )

    def _on_scan_complete(self, result: ScanResult) -> None:
        self._populate_table(result)
        self._finish_scan()
        up = result.hosts_up
        open_ports = sum(len(h.open_ports) for h in result.hosts)
        self.query_one("#log", RichLog).write(
            f"[b green]Done[/b green] in {result.duration_seconds:.1f}s — "
            f"{up} host(s) up, {open_ports} open port(s)."
        )
        self.notify(
            f"{up} host(s) up, {open_ports} open port(s) in {result.duration_seconds:.1f}s.",
            title="Scan complete",
            severity="information",
            timeout=8,
        )
        self._maybe_save_xml(result)

    def _on_scan_failed(self, message: str) -> None:
        self._finish_scan()
        self.query_one("#log", RichLog).write(f"[b red]Error:[/b red] {message}")
        self.notify(message, title="Scan failed", severity="error", timeout=10)

    def _finish_scan(self) -> None:
        progress = self.query_one("#progress", ProgressBar)
        if progress.total is not None:
            progress.update(progress=progress.total)
        self.query_one("#scan-button", Button).disabled = False

    def _populate_table(self, result: ScanResult) -> None:
        table = self.query_one("#table", DataTable)
        table.clear()
        for host in result.hosts:
            open_ports = host.open_ports
            if not open_ports:
                table.add_row(host.address, host.hostname or "-", "-", "-", host.state, "-")
                continue
            for port in open_ports:
                service = port.service.describe() if port.service else "-"
                table.add_row(
                    host.address,
                    host.hostname or "-",
                    str(port.number),
                    port.protocol,
                    port.state,
                    service or "-",
                )

    def _maybe_save_xml(self, result: ScanResult) -> None:
        if not self._config.output_dir or not result.raw_xml:
            return
        out_dir = Path(self._config.output_dir).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            target = self.query_one("#target", Input).value.replace("/", "_")
            path = out_dir / f"portscout-{target}.xml"
            path.write_text(result.raw_xml, encoding="utf-8")
            self.notify(f"Saved XML to {path}", severity="information")
        except OSError as exc:
            self.notify(f"Could not save XML: {exc}", severity="warning")

    # --- Modal actions --------------------------------------------------------

    def action_dependencies(self) -> None:
        self.push_screen(DependencyScreen(self._deps.check()))

    def action_settings(self) -> None:
        def handle(config) -> None:  # type: ignore[no-untyped-def]
            if config is None:
                return
            self._config_service.save(config)
            self._config = config
            self.notify("Settings saved. Restart to apply nmap path changes.")

        self.push_screen(
            SettingsScreen(self._config, self._config_service.location), handle
        )

    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan-button":
            self.action_scan()
