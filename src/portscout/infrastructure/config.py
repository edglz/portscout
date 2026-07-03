"""Adapter that persists configuration as TOML under the user's config directory.

Reading uses the stdlib ``tomllib`` (Python 3.11+). Writing uses a tiny, explicit
serializer for our flat schema, avoiding a third-party TOML writer dependency.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, fields
from pathlib import Path

from ..domain.ports import AppConfig, ConfigPort


def _default_config_dir() -> Path:
    """Resolve an XDG-style config directory across platforms."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "portscout"


class TomlConfigRepository(ConfigPort):
    """Loads/saves :class:`AppConfig` to ``<config-dir>/config.toml``."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self._dir = config_dir or _default_config_dir()
        self._path = self._dir / "config.toml"

    @property
    def location(self) -> str:
        return str(self._path)

    def load(self) -> AppConfig:
        if not self._path.exists():
            return AppConfig()
        try:
            with open(self._path, "rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            return AppConfig()
        known = {f.name for f in fields(AppConfig)}
        return AppConfig(**{k: v for k, v in data.items() if k in known})

    def save(self, config: AppConfig) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        body = "".join(self._to_toml_line(k, v) for k, v in asdict(config).items())
        header = "# Portscout configuration. Edit here or via the in-app settings.\n\n"
        self._path.write_text(header + body, encoding="utf-8")

    @staticmethod
    def _to_toml_line(key: str, value: object) -> str:
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            rendered = f'"{escaped}"'
        return f"{key} = {rendered}\n"
