"""Application icon loading.

Loads assets/icon.ico (preferred on Windows) or icon.png; if neither is present
or valid, draws a simple placeholder at runtime so there's always an icon.
"""

from __future__ import annotations

from pathlib import Path

import wx

_ASSETS = Path(__file__).resolve().parent.parent / "assets"


def load_app_icon() -> wx.Icon:
    for name in ("icon.ico", "icon.png"):
        path = _ASSETS / name
        if path.exists():
            icon = wx.Icon()
            if icon.LoadFile(str(path), wx.BITMAP_TYPE_ANY) and icon.IsOk():
                return icon
    return _drawn_icon()


def _drawn_icon(size: int = 64) -> wx.Icon:
    """Minimal fallback icon drawn in memory."""
    bmp = wx.Bitmap(size, size)
    dc = wx.MemoryDC(bmp)
    dc.SetBackground(wx.Brush(wx.Colour(24, 24, 28)))
    dc.Clear()
    dc.SetTextForeground(wx.Colour(235, 60, 60))
    dc.SetFont(wx.Font(wx.FontInfo(int(size * 0.45)).Bold()))
    text = "QL"
    tw, th = dc.GetTextExtent(text)
    dc.DrawText(text, (size - tw) // 2, (size - th) // 2)
    dc.SelectObject(wx.NullBitmap)
    icon = wx.Icon()
    icon.CopyFromBitmap(bmp)
    return icon
