"""Autocomplete popup for the command input.

Shows a small dark popup beneath the input listing cvars/commands that match
what's typed (substring search). Navigate with Up/Down, accept with Enter/Tab
or a mouse click, dismiss with Esc. Only the first token (the command/cvar
name) is completed; once a space is typed the popup hides.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from ..commands import (
    CMD,
    CVAR,
    PLAYER,
    PLAYER_COMMANDS,
    NUMERIC_PLAYER_COMMANDS,
    SET_COMMANDS,
    VALUE,
    Entry,
    search,
    search_values,
)
from ..roster import Player

_BG = wx.Colour(34, 34, 40)
_FG = wx.Colour(220, 220, 220)
_MAX_ROWS = 12

# Per-kind marker shown at the start of each suggestion row.
_TAGS = {CVAR: "$", CMD: ">", VALUE: "=", PLAYER: "@"}


class _Popup(wx.PopupWindow):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, flags=wx.BORDER_SIMPLE)
        self.listbox = wx.ListBox(self, style=wx.LB_SINGLE)
        self.listbox.SetBackgroundColour(_BG)
        self.listbox.SetForegroundColour(_FG)
        self.listbox.SetFont(wx.Font(wx.FontInfo(10).Family(wx.FONTFAMILY_TELETYPE)))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.listbox, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def row_height(self) -> int:
        dc = wx.ClientDC(self.listbox)
        dc.SetFont(self.listbox.GetFont())
        return dc.GetTextExtent("Ag")[1] + self.FromDIP(6)


class AutoComplete:
    """Attaches autocompletion behavior to a ``wx.TextCtrl``."""

    def __init__(
        self,
        text_ctrl: wx.TextCtrl,
        roster_provider: Callable[[], list[Player]] | None = None,
    ) -> None:
        self.text = text_ctrl
        self.frame = wx.GetTopLevelParent(text_ctrl)
        self.popup = _Popup(self.frame)
        self.entries: list[Entry] = []
        self._roster_provider = roster_provider or (lambda: [])
        self._start = 0  # index in the input where the completed token begins
        self._suffix = " "

        self.text.Bind(wx.EVT_TEXT, self._on_text)
        self.text.Bind(wx.EVT_KILL_FOCUS, self._on_kill_focus)
        self.popup.listbox.Bind(wx.EVT_LISTBOX, lambda _e: self.accept())
        # The popup is a separate top-level window; keep it glued to the input
        # by following the frame as it moves or resizes.
        self.frame.Bind(wx.EVT_MOVE, self._on_frame_move)
        self.frame.Bind(wx.EVT_SIZE, self._on_frame_move)

    # -- public API used by the owning frame ------------------------------

    def is_shown(self) -> bool:
        return self.popup.IsShown()

    def handle_key_down(self, event: wx.KeyEvent) -> bool:
        """Handle navigation keys while the popup is visible.

        Returns True if the key was consumed (caller must not process it).
        """
        if not self.is_shown():
            return False
        code = event.GetKeyCode()
        if code == wx.WXK_DOWN:
            self._move(1)
        elif code == wx.WXK_UP:
            self._move(-1)
        elif code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            self.accept()
        elif code == wx.WXK_ESCAPE:
            self.hide()
        else:
            return False
        return True

    def hide(self) -> None:
        if self.popup.IsShown():
            self.popup.Hide()

    def accept(self) -> None:
        idx = self.popup.listbox.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self.entries):
            return
        value = self.text.GetValue()
        # Replace just the active token (value[self._start:]) with the choice.
        new_value = value[: self._start] + self._token_for(self.entries[idx]) + self._suffix
        self.text.ChangeValue(new_value)  # ChangeValue: don't re-trigger EVT_TEXT
        self.text.SetInsertionPointEnd()
        self.hide()
        self.text.SetFocus()

    @staticmethod
    def _token_for(entry: Entry) -> str:
        """Text inserted for a chosen entry.

        Player names can contain spaces (``Player One``); the server would read
        only the first word, so wrap such names in quotes (``"Player One"``).
        Numeric slot entries and single-word names are inserted as-is.
        """
        name = entry.name
        if entry.kind == PLAYER and any(ch.isspace() for ch in name):
            return f'"{name}"'
        return name

    # -- internals --------------------------------------------------------

    def _on_text(self, event: wx.Event) -> None:
        event.Skip()
        value = self.text.GetValue()
        self.entries, self._start, self._suffix = self._analyze(value)
        if not self.entries:
            self.hide()
            return
        self.popup.listbox.Set([self._label(e) for e in self.entries])
        self.popup.listbox.SetSelection(0)
        self._reposition()
        if not self.popup.IsShown():
            self.popup.Show()

    def _analyze(self, value: str) -> tuple[list[Entry], int, str]:
        """Decide what to complete based on the input so far.

        Returns (entries, replace_start, suffix). ``replace_start`` is the index
        in ``value`` where the token being completed begins.
        """
        if not value.strip():
            return [], 0, " "
        parts = value.split(" ")
        cmd = parts[0].lower()
        ntok = len(parts)
        last_start = value.rfind(" ") + 1

        # First token: command / cvar name.
        if ntok == 1:
            return search(parts[0], _MAX_ROWS), 0, " "

        # set/seta/... <cvar> <value>
        if cmd in SET_COMMANDS:
            if ntok == 2:
                return search(parts[1], _MAX_ROWS, kinds={CVAR}), last_start, " "
            if ntok == 3:
                return search_values(parts[1], parts[2], _MAX_ROWS), last_start, " "
            return [], 0, " "

        # Player commands: complete name (or slot number) from the live roster.
        if cmd in PLAYER_COMMANDS:
            start = value.find(" ") + 1
            return self._player_entries(cmd, value[start:]), start, " "

        # Direct "<cvar> <value>" for cvars with known value sets.
        if ntok == 2:
            values = search_values(cmd, parts[1], _MAX_ROWS)
            if values:
                return values, last_start, " "

        return [], 0, " "

    def _player_entries(self, cmd: str, query: str) -> list[Entry]:
        numeric = cmd in NUMERIC_PLAYER_COMMANDS
        q = query.strip().lower()
        entries: list[Entry] = []
        for player in self._roster_provider():
            name = player.name
            if q and q not in name.lower():
                continue
            slot = "" if player.pid is None else f"slot {player.pid}"
            if numeric and player.pid is not None:
                entries.append(Entry(str(player.pid), PLAYER, name))
            else:
                detail = " · ".join(p for p in (slot, player.steam_id) if p)
                entries.append(Entry(name, PLAYER, detail))
            if len(entries) >= _MAX_ROWS:
                break
        return entries

    def _label(self, entry: Entry) -> str:
        tag = _TAGS.get(entry.kind, " ")
        return f"{tag} {entry.name:<26}{entry.desc}"

    def _move(self, delta: int) -> None:
        count = self.popup.listbox.GetCount()
        if not count:
            return
        idx = (self.popup.listbox.GetSelection() + delta) % count
        self.popup.listbox.SetSelection(idx)

    def _reposition(self) -> None:
        rect = self.text.GetScreenRect()
        rows = min(len(self.entries), _MAX_ROWS)
        height = rows * self.popup.row_height() + self.popup.FromDIP(4)
        self.popup.SetSize(rect.width, height)
        self.popup.SetPosition(wx.Point(rect.x, rect.y + rect.height))
        self.popup.Layout()

    def _on_frame_move(self, event: wx.Event) -> None:
        event.Skip()
        if self.popup.IsShown():
            self._reposition()

    def _on_kill_focus(self, event: wx.FocusEvent) -> None:
        event.Skip()
        # Defer: clicking the popup briefly removes focus from the input but
        # should not dismiss it before the click is handled.
        wx.CallAfter(self._hide_unless_popup_focused)

    def _hide_unless_popup_focused(self) -> None:
        focused = wx.Window.FindFocus()
        if focused not in (self.popup, self.popup.listbox):
            self.hide()
