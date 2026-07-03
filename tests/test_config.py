from pathlib import Path

from portscout.domain.ports import AppConfig
from portscout.infrastructure.config import TomlConfigRepository


def test_round_trip(tmp_path: Path) -> None:
    repo = TomlConfigRepository(config_dir=tmp_path)
    assert repo.load() == AppConfig()  # defaults when no file exists

    config = AppConfig(default_profile="full", timeout_seconds=42, disclaimer_accepted=True)
    repo.save(config)

    loaded = repo.load()
    assert loaded.default_profile == "full"
    assert loaded.timeout_seconds == 42
    assert loaded.disclaimer_accepted is True


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('default_profile = "quick"\nbogus = "x"\n', encoding="utf-8")
    loaded = TomlConfigRepository(config_dir=tmp_path).load()
    assert loaded.default_profile == "quick"
