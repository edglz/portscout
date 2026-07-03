"""Adapter that inspects the host system for nmap and packet-capture libraries."""

from __future__ import annotations

import shutil
import subprocess

from ..domain.ports import DependencyCheckerPort, DependencyStatus


class SystemDependencyChecker(DependencyCheckerPort):
    """Best-effort detection of nmap and libpcap/npcap."""

    def __init__(self, nmap_path: str = "nmap") -> None:
        self._nmap_path = nmap_path

    def check(self) -> list[DependencyStatus]:
        return [self._check_nmap(), self._check_pcap()]

    def _check_nmap(self) -> DependencyStatus:
        resolved = shutil.which(self._nmap_path)
        if resolved is None:
            return DependencyStatus(
                name="nmap",
                found=False,
                detail="Not found on PATH. Install it (see README).",
                required=True,
            )
        version = self._nmap_version(resolved)
        return DependencyStatus(
            name="nmap", found=True, detail=f"{resolved} ({version})", required=True
        )

    def _check_pcap(self) -> DependencyStatus:
        """libpcap/npcap ships with nmap; we surface it from nmap's version banner."""
        resolved = shutil.which(self._nmap_path)
        banner = self._nmap_version_banner(resolved) if resolved else ""
        if "libpcap" in banner.lower() or "npcap" in banner.lower():
            line = next(
                (ln for ln in banner.splitlines() if "pcap" in ln.lower()),
                "packet capture available",
            )
            return DependencyStatus(
                name="libpcap / npcap",
                found=True,
                detail=line.strip(),
                required=False,
            )
        return DependencyStatus(
            name="libpcap / npcap",
            found=False,
            detail="Could not confirm packet-capture support. Raw/UDP scans may fail.",
            required=False,
        )

    def _nmap_version(self, path: str) -> str:
        banner = self._nmap_version_banner(path)
        for line in banner.splitlines():
            if line.lower().startswith("nmap version"):
                return line.split("version", 1)[1].strip().split()[0]
        return "unknown version"

    @staticmethod
    def _nmap_version_banner(path: str) -> str:
        try:
            result = subprocess.run(  # noqa: S603 - fixed args, no shell
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.stdout or result.stderr
        except (OSError, subprocess.SubprocessError):
            return ""
