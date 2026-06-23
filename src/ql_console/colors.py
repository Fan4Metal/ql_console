"""Quake ``^N`` color code handling.

Quake/QL color codes are a caret followed by a single digit (``^1`` red, etc.).
This module maps them to RGB and splits a colored string into runs of
``(rgb, text)`` so the UI can render each run in its color.
"""

from __future__ import annotations

import re

RGB = tuple[int, int, int]

# Default foreground for the dark console.
WHITE: RGB = (220, 220, 220)

# Quake 3 / Quake Live palette for ^0-^9. 8 and 9 wrap back to white/grey.
QUAKE_COLORS: dict[str, RGB] = {
    "0": (40, 40, 40),     # black (lifted so it stays visible on a dark bg)
    "1": (235, 60, 60),    # red
    "2": (70, 215, 90),    # green
    "3": (235, 215, 70),   # yellow
    "4": (80, 120, 235),   # blue
    "5": (80, 215, 235),   # cyan
    "6": (220, 90, 220),   # magenta
    "7": WHITE,            # white
    "8": (235, 150, 70),   # orange
    "9": (150, 150, 150),  # grey
}

_COLOR_RE = re.compile(r"\^([0-9])")


def strip_colors(text: str) -> str:
    """Remove all ``^N`` color codes from a string."""
    return _COLOR_RE.sub("", text)


def parse_hex(value: str, default: RGB = (24, 24, 28)) -> RGB:
    """Parse ``#rrggbb`` (or ``rrggbb``) into an RGB tuple."""
    s = value.lstrip("#")
    if len(s) != 6:
        return default
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return default


def to_hex(rgb: RGB) -> str:
    """Format an RGB tuple as ``#rrggbb``."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def parse_segments(text: str, default: RGB = WHITE) -> list[tuple[RGB, str]]:
    """Split ``text`` into ``(rgb, chunk)`` runs based on its color codes."""
    segments: list[tuple[RGB, str]] = []
    current = default
    pos = 0
    for match in _COLOR_RE.finditer(text):
        if match.start() > pos:
            segments.append((current, text[pos : match.start()]))
        current = QUAKE_COLORS.get(match.group(1), default)
        pos = match.end()
    if pos < len(text):
        segments.append((current, text[pos:]))
    return segments
