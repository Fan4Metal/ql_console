"""About dialog: program name, version and a link to the GitHub page."""

from __future__ import annotations

from pathlib import Path

import wx
import wx.adv

from .. import __version__
from ..i18n import t

GITHUB_URL = "https://github.com/Fan4Metal/ql_console"

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_LOGO_DIP = 96  # displayed logo side in DIPs (scaled for HiDPI at runtime)


class AboutDialog(wx.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, title=t("about_title"))

        sizer = wx.BoxSizer(wx.VERTICAL)

        logo = self._load_logo()
        if logo is not None:
            sizer.Add(logo, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.TOP, 16)

        text = wx.StaticText(
            self, label=t("about_text", version=__version__), style=wx.ALIGN_CENTRE_HORIZONTAL
        )
        sizer.Add(text, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 16)

        link = wx.adv.HyperlinkCtrl(self, label=t("about_github"), url=GITHUB_URL)
        sizer.Add(link, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)

        buttons = self.CreateButtonSizer(wx.OK)
        if buttons is not None:
            sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizerAndFit(sizer)
        self.Centre()

    def _load_logo(self) -> wx.StaticBitmap | None:
        """Load the app logo (PNG) scaled to a DPI-aware square, or None if absent."""
        path = _ASSETS / "icon.png"
        if not path.exists():
            return None
        image = wx.Image()
        if not image.LoadFile(str(path), wx.BITMAP_TYPE_ANY) or not image.IsOk():
            return None
        side = self.FromDIP(_LOGO_DIP)
        image = image.Scale(side, side, wx.IMAGE_QUALITY_HIGH)
        return wx.StaticBitmap(self, bitmap=wx.Bitmap(image))
