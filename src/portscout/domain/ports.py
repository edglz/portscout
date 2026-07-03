"""Ports: the interfaces the application depends on.

Adapters in the infrastructure layer implement these Protocols. The application
core never imports an adapter directly; it only ever talks to these abstractions,
which is what keeps the hexagon's core independent of nmap, the filesystem, etc.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .entities import ScanRequest, ScanResult

# Callback used to stream human-readable progress lines from a running scan.
ProgressCallback = Callable[[str], None]


class ScanError(RuntimeError):
    """Raised when a scan cannot be started or fails to complete."""


@runtime_checkable
class ScannerPort(Protocol):
    """Drives the underlying scanner (e.g. nmap)."""

    def scan(self, request: ScanRequest, on_progress: ProgressCallback) -> ScanResult: ...

    def preview_command(self, request: ScanRequest) -> str:
        """Return the exact command that ``scan`` would run, for display."""
        ...


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    """The availability of a required or recommended system dependency."""

    name: str
    found: bool
    detail: str
    required: bool


@runtime_checkable
class DependencyCheckerPort(Protocol):
    """Verifies that system dependencies (nmap, libpcap/npcap) are present."""

    def check(self) -> list[DependencyStatus]: ...


@runtime_checkable
class ConfigPort(Protocol):
    """Loads and persists user configuration."""

    def load(self) -> AppConfig: ...

    def save(self, config: AppConfig) -> None: ...

    @property
    def location(self) -> str:
        """Human-readable path of the config file, for display."""
        ...


@dataclass(slots=True)
class AppConfig:
    """User-facing configuration, persisted between runs."""

    default_profile: str = "standard"
    nmap_path: str = "nmap"
    output_dir: str = ""
    timeout_seconds: int = 600
    theme: str = "textual-dark"
    disclaimer_accepted: bool = False
