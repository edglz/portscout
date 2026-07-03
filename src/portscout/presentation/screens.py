"""Modal screens: disclaimer gate, settings editor and dependency report."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from ..domain.ports import AppConfig, DependencyStatus
from .themes import PREDEFINED_THEMES, normalize_theme


class DisclaimerScreen(ModalScreen[bool]):
    """Blocks all scanning until the user accepts the responsible-use terms."""

    DISCLAIMER = (
        "Portscout is a front-end for nmap, for AUTHORIZED use only.\n\n"
        "Port scanning systems you do not own or lack written permission to test "
        "may be illegal in your jurisdiction. You accept full and sole "
        "responsibility for your use of this tool. The authors provide it "
        "\"as is\", with no warranty and no liability for misuse or damage.\n\n"
        "Only scan systems you own or are explicitly authorized to assess."
    )

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("⚠  Legal Disclaimer & Responsible Use", classes="title")
            yield Static(self.DISCLAIMER)
            with Vertical(id="dialog-buttons"):
                yield Button("I understand and accept", variant="success", id="accept")
                yield Button("Quit", variant="error", id="decline")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "accept")


class DependencyScreen(ModalScreen[None]):
    """Shows the status of nmap and packet-capture libraries."""

    def __init__(self, statuses: list[DependencyStatus]) -> None:
        super().__init__()
        self._statuses = statuses

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("System dependencies", classes="title")
            for status in self._statuses:
                mark = "✔" if status.found else "✘"
                css = "status-ok" if status.found else (
                    "status-bad" if status.required else "status-warn"
                )
                tag = "required" if status.required else "recommended"
                yield Static(f"{mark} {status.name} [{tag}] — {status.detail}", classes=css)
            with Vertical(id="dialog-buttons"):
                yield Button("Close", variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class SettingsScreen(ModalScreen[AppConfig | None]):
    """Edits and returns the persisted configuration."""

    def __init__(self, config: AppConfig, config_location: str) -> None:
        super().__init__()
        self._config = config
        self._location = config_location
        self._original_theme = normalize_theme(config.theme)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Settings", classes="title")
            yield Static(f"Saved to: {self._location}", classes="status-warn")
            yield Label("nmap path")
            yield Input(value=self._config.nmap_path, id="nmap_path")
            yield Label("Default profile key")
            yield Input(value=self._config.default_profile, id="default_profile")
            yield Label("Output directory (for saved XML)")
            yield Input(value=self._config.output_dir, id="output_dir")
            yield Label("Timeout (seconds)")
            yield Input(value=str(self._config.timeout_seconds), id="timeout_seconds")
            yield Label("Theme (previews live as you change it)")
            yield Select(
                [(label, key) for key, label in PREDEFINED_THEMES],
                value=self._original_theme,
                id="theme",
                allow_blank=False,
            )
            with Vertical(id="dialog-buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "theme" and event.value is not Select.BLANK:
            self.app.theme = normalize_theme(str(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save":
            self.app.theme = self._original_theme  # revert the live preview
            self.dismiss(None)
            return
        try:
            timeout = int(self.query_one("#timeout_seconds", Input).value)
        except ValueError:
            timeout = self._config.timeout_seconds
        self._config.nmap_path = self.query_one("#nmap_path", Input).value.strip() or "nmap"
        self._config.default_profile = (
            self.query_one("#default_profile", Input).value.strip() or "standard"
        )
        self._config.output_dir = self.query_one("#output_dir", Input).value.strip()
        self._config.timeout_seconds = max(1, timeout)
        theme = self.query_one("#theme", Select).value
        if theme is not Select.BLANK:
            self._config.theme = normalize_theme(str(theme))
        self.dismiss(self._config)
