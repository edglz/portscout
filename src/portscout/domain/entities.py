"""Domain entities describing a scan request and its result."""

from __future__ import annotations

from dataclasses import dataclass, field

from .value_objects import PortSpec, ScanProfile, Target


@dataclass(frozen=True, slots=True)
class ScanRequest:
    """Everything needed to launch one scan, assembled from validated values."""

    target: Target
    profile: ScanProfile
    ports: PortSpec | None = None
    privileged: bool = False


@dataclass(frozen=True, slots=True)
class Service:
    """A network service detected on an open port."""

    name: str = ""
    product: str = ""
    version: str = ""

    def describe(self) -> str:
        parts = [p for p in (self.product, self.version) if p]
        detail = " ".join(parts)
        return f"{self.name} ({detail})" if detail else self.name


@dataclass(frozen=True, slots=True)
class Port:
    """A single port and its observed state."""

    number: int
    protocol: str
    state: str
    service: Service | None = None


@dataclass(frozen=True, slots=True)
class Host:
    """A host discovered by a scan, with its ports."""

    address: str
    hostname: str | None
    state: str
    ports: tuple[Port, ...] = field(default_factory=tuple)

    @property
    def open_ports(self) -> tuple[Port, ...]:
        return tuple(p for p in self.ports if p.state == "open")


@dataclass(frozen=True, slots=True)
class ScanResult:
    """The outcome of a completed scan."""

    command: str
    hosts: tuple[Host, ...]
    duration_seconds: float
    raw_xml: str = ""

    @property
    def hosts_up(self) -> int:
        return sum(1 for h in self.hosts if h.state == "up")
