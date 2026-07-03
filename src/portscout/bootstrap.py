"""Composition root: the only place that knows about concrete adapters.

It wires infrastructure adapters into application services and hands the ready
services to the presentation layer. Swapping nmap for a mock, or TOML for a DB,
means changing only this file.
"""

from __future__ import annotations

from dataclasses import dataclass

from .application.services import ConfigService, DependencyService, ScanService
from .infrastructure.config import TomlConfigRepository
from .infrastructure.dependencies import SystemDependencyChecker
from .infrastructure.nmap_adapter import NmapAdapter


@dataclass(slots=True)
class Container:
    """Holds the wired-up application services."""

    scan: ScanService
    dependencies: DependencyService
    config: ConfigService


def build_container() -> Container:
    config_repo = TomlConfigRepository()
    app_config = config_repo.load()

    scanner = NmapAdapter(
        nmap_path=app_config.nmap_path,
        timeout_seconds=app_config.timeout_seconds,
    )
    checker = SystemDependencyChecker(nmap_path=app_config.nmap_path)

    return Container(
        scan=ScanService(scanner),
        dependencies=DependencyService(checker),
        config=ConfigService(config_repo),
    )
