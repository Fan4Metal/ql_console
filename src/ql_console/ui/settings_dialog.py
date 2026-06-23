"""Application settings dialog.

Organized into sections ("Общие", "Вид"). New options should slot into an
existing section's sizer or a new wx.StaticBox section.
"""

from __future__ import annotations

import wx

from .. import colors
from ..config import AppSettings
from ..i18n import LANGUAGES, t

# Fallback monospace faces if the system enumeration returns nothing.
_FALLBACK_MONO = ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono"]


def _monospace_faces() -> list[str]:
    faces = wx.FontEnumerator.GetFacenames(wx.FONTENCODING_SYSTEM, fixedWidthOnly=True)
    faces = sorted(f for f in faces if not f.startswith("@"))  # skip vertical CJK faces
    return faces or _FALLBACK_MONO


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, settings: AppSettings) -> None:
        super().__init__(parent, title=t("dlg_settings"))
        self._settings = settings
        self._faces = _monospace_faces()
        self._lang_codes = list(LANGUAGES.keys())

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self._build_general_section(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        outer.Add(self._build_view_section(), 0, wx.EXPAND | wx.ALL, 12)
        outer.Add(
            self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12
        )
        self.SetSizerAndFit(outer)
        self.SetMinSize(self.FromDIP(wx.Size(420, -1)))

    def _build_general_section(self) -> wx.Sizer:
        box = wx.StaticBoxSizer(wx.VERTICAL, self, t("section_general"))
        parent = box.GetStaticBox()

        grid = wx.FlexGridSizer(rows=0, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        self.language = wx.Choice(parent, choices=[LANGUAGES[c] for c in self._lang_codes])
        cur = self._settings.language
        self.language.SetSelection(self._lang_codes.index(cur) if cur in self._lang_codes else 0)

        grid.Add(wx.StaticText(parent, label=t("lbl_language")), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self.language, 1, wx.EXPAND)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        return box

    def _build_view_section(self) -> wx.Sizer:
        box = wx.StaticBoxSizer(wx.VERTICAL, self, t("section_view"))
        parent = box.GetStaticBox()

        self.hide_echo = wx.CheckBox(parent, label=t("chk_hide_echo"))
        self.hide_echo.SetValue(self._settings.hide_rcon_echo)
        box.Add(self.hide_echo, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.clean_output = wx.CheckBox(parent, label=t("chk_clean_output"))
        self.clean_output.SetValue(self._settings.clean_output)
        box.Add(self.clean_output, 0, wx.ALL, 8)

        grid = wx.FlexGridSizer(rows=0, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        # Console font (monospace) + size.
        self.font_choice = wx.Choice(parent, choices=[t("font_default")] + self._faces)
        cur = self._settings.console_font_face
        self.font_choice.SetSelection(self._faces.index(cur) + 1 if cur in self._faces else 0)
        self.font_size = wx.SpinCtrl(
            parent, min=6, max=48, initial=self._settings.console_font_size
        )

        # Console background color.
        self.bg_picker = wx.ColourPickerCtrl(
            parent, colour=wx.Colour(*colors.parse_hex(self._settings.console_bg))
        )

        def row(label: str, ctrl: wx.Window) -> None:
            grid.Add(wx.StaticText(parent, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        row(t("lbl_console_font"), self.font_choice)
        row(t("lbl_font_size"), self.font_size)
        row(t("lbl_console_bg"), self.bg_picker)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        return box

    def get_settings(self) -> AppSettings:
        """Return a copy of the input settings with the dialog's values applied."""
        sel = self.font_choice.GetSelection()
        face = "" if sel <= 0 else self._faces[sel - 1]
        bg = colors.to_hex(tuple(self.bg_picker.GetColour().Get()[:3]))
        lang = self._lang_codes[self.language.GetSelection()]
        return AppSettings(
            language=lang,
            hide_rcon_echo=self.hide_echo.GetValue(),
            clean_output=self.clean_output.GetValue(),
            console_font_face=face,
            console_font_size=self.font_size.GetValue(),
            console_bg=bg,
        )
