"""Curated set of predefined UI themes the user can pick from.

Every key here is a theme that ships built into Textual, so selecting one never
fails. ``DEFAULT_THEME`` is used whenever a persisted theme is unknown (for example
after a Textual downgrade).
"""

from __future__ import annotations

DEFAULT_THEME = "textual-dark"

# (theme key, human-friendly label). Keys must match Textual's built-in theme names.
PREDEFINED_THEMES: tuple[tuple[str, str], ...] = (
    ("textual-dark", "Textual Dark"),
    ("textual-light", "Textual Light"),
    ("nord", "Nord"),
    ("gruvbox", "Gruvbox"),
    ("dracula", "Dracula"),
    ("tokyo-night", "Tokyo Night"),
    ("catppuccin-mocha", "Catppuccin Mocha"),
    ("catppuccin-latte", "Catppuccin Latte"),
    ("monokai", "Monokai"),
    ("solarized-dark", "Solarized Dark"),
    ("solarized-light", "Solarized Light"),
    ("flexoki", "Flexoki"),
)

_THEME_KEYS = frozenset(key for key, _ in PREDEFINED_THEMES)


def normalize_theme(theme: str) -> str:
    """Return ``theme`` if it is one we offer, otherwise the default."""
    return theme if theme in _THEME_KEYS else DEFAULT_THEME
