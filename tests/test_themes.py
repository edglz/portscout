from portscout.presentation.themes import (
    DEFAULT_THEME,
    PREDEFINED_THEMES,
    normalize_theme,
)


def test_known_theme_is_kept() -> None:
    assert normalize_theme("dracula") == "dracula"
    assert normalize_theme(DEFAULT_THEME) == DEFAULT_THEME


def test_unknown_theme_falls_back_to_default() -> None:
    assert normalize_theme("not-a-theme") == DEFAULT_THEME
    assert normalize_theme("") == DEFAULT_THEME


def test_default_theme_is_offered() -> None:
    assert DEFAULT_THEME in {key for key, _ in PREDEFINED_THEMES}
