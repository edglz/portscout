"""Adapter that drives the real nmap binary and parses its XML output.

Security model (why this is safe despite invoking a subprocess):

* nmap is invoked with an argument *list*, never with ``shell=True``, so there is no
  shell to inject into.
* The target is validated by the ``Target`` value object, which permits only IPs,
  CIDRs, and RFC 1123 hostnames. That regex forbids whitespace and a leading hyphen,
  which also prevents *argument* injection (a target can never be read by nmap as a
  flag).
* Scan flags come exclusively from the fixed ``BUILTIN_PROFILES`` registry, and any
  custom ports are validated by the ``PortSpec`` value object. No free-form user
  string ever reaches argv.

The one operator-controlled value is ``nmap_path`` from local config, resolved via
``shutil.which``; choosing which binary to run on your own machine is not an injection
vector.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from ..domain.entities import Host, Port, ScanRequest, ScanResult, Service
from ..domain.ports import ProgressCallback, ScanError, ScannerPort


class NmapAdapter(ScannerPort):
    """Runs nmap as a subprocess, streaming progress and parsing XML results."""

    def __init__(self, nmap_path: str = "nmap", timeout_seconds: int = 600) -> None:
        self._nmap_path = nmap_path
        self._timeout = timeout_seconds

    def _resolve_binary(self) -> str:
        resolved = shutil.which(self._nmap_path)
        if resolved is None:
            raise ScanError(
                f"nmap executable '{self._nmap_path}' not found on PATH. "
                "Install nmap or set the path in the configuration screen."
            )
        return resolved

    def _build_args(self, request: ScanRequest, xml_path: str) -> list[str]:
        args = [self._resolve_binary(), *request.profile.nmap_args]
        if request.ports is not None:
            args += ["-p", request.ports.value]
        # --stats-every gives us periodic progress lines on stdout.
        args += ["-v", "--stats-every", "2s", "-oX", xml_path, request.target.value]
        return args

    def preview_command(self, request: ScanRequest) -> str:
        args = [self._nmap_path, *request.profile.nmap_args]
        if request.ports is not None:
            args += ["-p", request.ports.value]
        args += ["-oX", "-", request.target.value]
        return " ".join(args)

    def scan(self, request: ScanRequest, on_progress: ProgressCallback) -> ScanResult:
        if request.privileged and os.name != "nt" and os.geteuid() != 0:
            raise ScanError(
                f"The '{request.profile.label}' profile needs elevated privileges. "
                "Re-launch Portscout with sudo, or pick a non-privileged profile."
            )

        fd, xml_path = tempfile.mkstemp(prefix="portscout-", suffix=".xml")
        os.close(fd)
        args = self._build_args(request, xml_path)
        on_progress(f"$ {' '.join(args)}")
        started = time.monotonic()
        try:
            # Safe: no shell; every element of `args` is validated (see module docstring).
            proc = subprocess.Popen(  # noqa: S603  # nosemgrep: subprocess-injection
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                stripped = line.rstrip()
                if stripped:
                    on_progress(stripped)
            returncode = proc.wait(timeout=self._timeout)
            if returncode != 0:
                raise ScanError(f"nmap exited with code {returncode}.")
            duration = time.monotonic() - started
            with open(xml_path, encoding="utf-8") as handle:
                raw_xml = handle.read()
            hosts = self._parse_hosts(raw_xml)
            command = " ".join(args)
            return ScanResult(command, hosts, duration, raw_xml)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            raise ScanError(f"nmap timed out after {self._timeout}s.") from exc
        except FileNotFoundError as exc:
            raise ScanError(str(exc)) from exc
        finally:
            with contextlib.suppress(OSError):
                os.unlink(xml_path)

    @staticmethod
    def _parse_hosts(raw_xml: str) -> tuple[Host, ...]:
        if not raw_xml.strip():
            return ()
        try:
            root = ET.fromstring(raw_xml)  # noqa: S314 - output of our own trusted nmap run
        except ET.ParseError as exc:
            raise ScanError(f"Could not parse nmap XML output: {exc}") from exc

        hosts: list[Host] = []
        for host_el in root.findall("host"):
            status = host_el.find("status")
            state = status.get("state", "unknown") if status is not None else "unknown"

            address = ""
            for addr in host_el.findall("address"):
                address = addr.get("addr", address)
                if addr.get("addrtype") in {"ipv4", "ipv6"}:
                    break

            hostname_el = host_el.find("hostnames/hostname")
            hostname = hostname_el.get("name") if hostname_el is not None else None

            hosts.append(
                Host(
                    address=address,
                    hostname=hostname,
                    state=state,
                    ports=NmapAdapter._parse_ports(host_el),
                )
            )
        return tuple(hosts)

    @staticmethod
    def _parse_ports(host_el: ET.Element) -> tuple[Port, ...]:
        ports: list[Port] = []
        for port_el in host_el.findall("ports/port"):
            state_el = port_el.find("state")
            if state_el is None:
                continue
            service_el = port_el.find("service")
            service = None
            if service_el is not None:
                service = Service(
                    name=service_el.get("name", ""),
                    product=service_el.get("product", ""),
                    version=service_el.get("version", ""),
                )
            ports.append(
                Port(
                    number=int(port_el.get("portid", "0")),
                    protocol=port_el.get("protocol", "tcp"),
                    state=state_el.get("state", "unknown"),
                    service=service,
                )
            )
        return tuple(ports)
