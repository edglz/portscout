"""Immutable, self-validating value objects for the domain.

These types make invalid states unrepresentable: a `Target` or `PortSpec` cannot
be constructed with a value that nmap would reject, so the rest of the system can
trust them without re-checking.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

# RFC 1123 hostname: labels of 1-63 chars, no leading/trailing hyphen, total <= 253.
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)

# One or more comma-separated ports or port ranges, e.g. "22,80,8000-8100".
_PORTSPEC_RE = re.compile(r"^\d{1,5}(-\d{1,5})?(,\d{1,5}(-\d{1,5})?)*$")


class InvalidTargetError(ValueError):
    """Raised when a target is not a valid IP address, CIDR network or hostname."""


class InvalidPortSpecError(ValueError):
    """Raised when a port specification is malformed or out of range."""


@dataclass(frozen=True, slots=True)
class Target:
    """A scan target: an IPv4/IPv6 address, a CIDR network, or a hostname."""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip()
        if not raw:
            raise InvalidTargetError("Target cannot be empty.")
        if not self._is_valid(raw):
            raise InvalidTargetError(
                f"'{raw}' is not a valid IP address, CIDR network, or hostname."
            )
        object.__setattr__(self, "value", raw)

    @staticmethod
    def _is_valid(raw: str) -> bool:
        for parser in (ipaddress.ip_network, ipaddress.ip_address):
            try:
                parser(raw, strict=False) if parser is ipaddress.ip_network else parser(raw)
                return True
            except ValueError:
                continue
        # A dotted all-numeric string is a malformed IP, not a hostname.
        if re.fullmatch(r"[\d.]+", raw):
            return False
        return bool(_HOSTNAME_RE.match(raw))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PortSpec:
    """A validated nmap port specification such as "1-1024" or "22,80,443"."""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip()
        if not _PORTSPEC_RE.match(raw):
            raise InvalidPortSpecError(
                f"'{raw}' is not a valid port list (expected e.g. '22,80,8000-8100')."
            )
        for number in re.findall(r"\d{1,5}", raw):
            if not 0 <= int(number) <= 65535:
                raise InvalidPortSpecError(f"Port {number} is out of range (0-65535).")
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ScanProfile:
    """A named preset of nmap flags with a human-friendly description."""

    key: str
    label: str
    description: str
    nmap_args: tuple[str, ...]
    requires_privilege: bool = False


# Built-in profiles, ordered from lightest to most thorough.
BUILTIN_PROFILES: tuple[ScanProfile, ...] = (
    ScanProfile(
        key="ping",
        label="Ping sweep",
        description="Discover which hosts are up. No port scan. Great for mapping a subnet.",
        nmap_args=("-sn",),
    ),
    ScanProfile(
        key="quick",
        label="Quick scan",
        description="Fast scan of the 100 most common ports.",
        nmap_args=("-T4", "-F"),
    ),
    ScanProfile(
        key="standard",
        label="Standard (service versions)",
        description="Common ports with service/version detection. A balanced default.",
        nmap_args=("-T4", "-sV"),
    ),
    ScanProfile(
        key="full",
        label="Full TCP + scripts",
        description="All 65535 TCP ports, versions, default scripts and OS detection. Slow.",
        nmap_args=("-T4", "-sS", "-sV", "-sC", "-O", "-p-"),
        requires_privilege=True,
    ),
    ScanProfile(
        key="udp",
        label="UDP top ports",
        description="Top 20 UDP ports (DNS, SNMP, DHCP...). Slow, needs privileges.",
        nmap_args=("-sU", "--top-ports", "20"),
        requires_privilege=True,
    ),
)

PROFILES_BY_KEY: dict[str, ScanProfile] = {p.key: p for p in BUILTIN_PROFILES}


def get_profile(key: str) -> ScanProfile:
    """Return a built-in profile by key, raising ``KeyError`` if unknown."""
    return PROFILES_BY_KEY[key]
