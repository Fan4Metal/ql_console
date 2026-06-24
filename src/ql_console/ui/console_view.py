"""Colored, append-aware log view built on Scintilla.

``wx.TextCtrl`` (the native RichEdit on MSW) force-scrolls to the end on every
append and drops the active selection, so a busy console can't be read
scrolled-up or copied from. Scintilla draws its own viewport, so appending never
moves the view on its own: a reader scrolled up stays put, a view pinned to the
bottom follows new lines, and selection/copy survive untouched.

Lines are lists of ``(rgb, text)`` runs. Each distinct color is mapped to a
Scintilla style index (the palette is small and fixed), so coloring is a cheap
``SetStyling`` over the appended bytes rather than per-segment attribute objects.
"""

from __future__ import annotations

import wx
import wx.stc as stc

from ..colors import WHITE, RGB

# A rendered line is a list of (rgb, text) runs.
Line = list[tuple[RGB, str]]

# Scintilla styles 0..31 are free for application use; the console palette
# (10 Quake colors + a handful of role colors) fits comfortably below this.
_MAX_STYLES = 32


class ConsoleView(stc.StyledTextCtrl):
    """Read-only colored log with tail-following scroll."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, style=wx.BORDER_NONE)
        self._style_for: dict[RGB, int] = {}
        self._font: wx.Font | None = None
        self._bg = wx.Colour(0, 0, 0)

        # A plain log view: UTF-8 (so byte offsets match), word wrap like the old
        # control, no margins, no blinking caret, and a native dark scrollbar.
        self.SetCodePage(stc.STC_CP_UTF8)
        self.SetWrapMode(stc.STC_WRAP_WORD)
        self.SetUseHorizontalScrollBar(False)
        for margin in range(self.GetMarginCount()):
            self.SetMarginWidth(margin, 0)
        self.SetCaretWidth(0)
        self.SetCaretLineVisible(False)
        self.SetReadOnly(True)

    # -- theming ----------------------------------------------------------

    def configure(self, font: wx.Font, bg: wx.Colour) -> None:
        """Apply the console font and background, re-styling existing colors."""
        self._font = font
        self._bg = bg
        self.StyleSetFont(stc.STC_STYLE_DEFAULT, font)
        self.StyleSetBackground(stc.STC_STYLE_DEFAULT, bg)
        self.StyleSetForeground(stc.STC_STYLE_DEFAULT, wx.Colour(*WHITE))
        self.StyleClearAll()  # propagate the default to every style index
        # StyleClearAll wiped per-color foregrounds; restore them (font/bg are
        # already correct from the clear).
        for rgb, idx in self._style_for.items():
            self.StyleSetForeground(idx, wx.Colour(*rgb))
        # Selection that stays readable on a dark background.
        self.SetSelBackground(True, wx.Colour(60, 70, 90))
        self.SetBackgroundColour(bg)

    def _style(self, rgb: RGB) -> int:
        """Style index for a color, allocating one on first use."""
        idx = self._style_for.get(rgb)
        if idx is None:
            idx = len(self._style_for)
            if idx >= _MAX_STYLES:  # palette overflow: fall back to default fg
                return stc.STC_STYLE_DEFAULT
            self._style_for[rgb] = idx
            self.StyleSetForeground(idx, wx.Colour(*rgb))
            if self._font is not None:
                self.StyleSetFont(idx, self._font)
            self.StyleSetBackground(idx, self._bg)
        return idx

    # -- output -----------------------------------------------------------

    def _emit(self, runs: Line) -> None:
        """Append one colored line at the tail without touching the viewport."""
        self.SetReadOnly(False)
        for rgb, text in runs:
            start = self.GetLength()  # byte offset before the run
            self.AppendText(text)
            self.StartStyling(start)
            self.SetStyling(len(text.encode("utf-8")), self._style(rgb))
        self.AppendText("\n")
        self.SetReadOnly(True)

    def append_line(self, runs: Line) -> None:
        """Append a live line, following the tail only if the view is at it."""
        follow = self._follows_tail()
        self._emit(runs)
        if follow:
            self.ScrollToEnd()

    def render_all(self, lines: list[Line]) -> None:
        """Replace all content (used on server switch / settings change)."""
        self.SetReadOnly(False)
        self.ClearAll()
        self.SetReadOnly(True)
        for runs in lines:
            self._emit(runs)
        self.ScrollToEnd()

    def clear(self) -> None:
        self.SetReadOnly(False)
        self.ClearAll()
        self.SetReadOnly(True)

    def _follows_tail(self) -> bool:
        """True when the last line is visible (view pinned to the bottom)."""
        bottom = self.GetFirstVisibleLine() + self.LinesOnScreen()
        return bottom >= self.VisibleFromDocLine(self.GetLineCount() - 1)
