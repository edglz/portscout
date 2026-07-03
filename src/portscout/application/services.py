"""Use cases. These depend only on domain ports, never on concrete adapters."""

from __future__ import annotations

from ..domain.entities import ScanRequest, ScanResult
from ..domain.ports import (
    AppConfig,
    ConfigPort,
    DependencyCheckerPort,
    DependencyStatus,
    ProgressCallback,
    ScannerPort,
)
from ..domain.value_objects import PortSpec, ScanProfile, Target


class ScanService:
    """Coordinates running a scan through whatever scanner adapter is injected."""

    def __init__(self, scanner: ScannerPort) -> None:
        self._scanner = scanner

    def build_request(
        self,
        raw_target: str,
        profile: ScanProfile,
        raw_ports: str | None = None,
        privileged: bool = False,
    ) -> ScanRequest:
        """Validate raw UI input into a domain ``ScanRequest``.

        Raises ``InvalidTargetError`` / ``InvalidPortSpecError`` on bad input.
        """
        target = Target(raw_target)
        ports = PortSpec(raw_ports) if raw_ports and raw_ports.strip() else None
        return ScanRequest(
            target=target,
            profile=profile,
            ports=ports,
            privileged=privileged or profile.requires_privilege,
        )

    def preview(self, request: ScanRequest) -> str:
        return self._scanner.preview_command(request)

    def run(self, request: ScanRequest, on_progress: ProgressCallback) -> ScanResult:
        return self._scanner.scan(request, on_progress)


class DependencyService:
    """Reports on system dependencies so the UI can guide installation."""

    def __init__(self, checker: DependencyCheckerPort) -> None:
        self._checker = checker

    def check(self) -> list[DependencyStatus]:
        return self._checker.check()

    def blocking_issue(self) -> str | None:
        """Return a message if a *required* dependency is missing, else None."""
        missing = [d for d in self._checker.check() if d.required and not d.found]
        if not missing:
            return None
        names = ", ".join(d.name for d in missing)
        return f"Missing required dependency: {names}. See the README for install steps."


class ConfigService:
    """Loads and mutates persisted configuration through the config port."""

    def __init__(self, config_port: ConfigPort) -> None:
        self._port = config_port

    def load(self) -> AppConfig:
        return self._port.load()

    def save(self, config: AppConfig) -> None:
        self._port.save(config)

    def accept_disclaimer(self) -> AppConfig:
        config = self._port.load()
        config.disclaimer_accepted = True
        self._port.save(config)
        return config

    @property
    def location(self) -> str:
        return self._port.location
