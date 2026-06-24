"""About dialog: program name, version and a link to the GitHub page."""

from __future__ import annotations

import wx
import wx.adv

from .. import __version__
from ..i18n import t

GITHUB_URL = "https://github.com/Fan4Metal/ql_console"


class AboutDialog(wx.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title=t("about_title"))

        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(self, label=t("about_text", version=__version__))
        sizer.Add(text, 0, wx.ALL, 16)

        link = wx.adv.HyperlinkCtrl(self, label=t("about_github"), url=GITHUB_URL)
        sizer.Add(link, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)

        buttons = self.CreateButtonSizer(wx.OK)
        if buttons is not None:
            sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizerAndFit(sizer)
        self.Centre()
