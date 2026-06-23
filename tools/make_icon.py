"""Render the placeholder app icon to PNG (and ICO on Windows).

This draws a simple placeholder matching assets/icon.svg — a dark rounded square
with a red border and "QL". Replace the design here (or edit icon.svg and adapt)
when you have a real icon.

    uv run python tools/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

import wx

_ASSETS = Path(__file__).resolve().parents[1] / "src" / "ql_console" / "assets"
_SIZE = 256
_BG = wx.Colour(24, 24, 28)
_ACCENT = wx.Colour(235, 60, 60)


def render(size: int = _SIZE) -> wx.Bitmap:
    bmp = wx.Bitmap(size, size)
    dc = wx.MemoryDC(bmp)
    gc = wx.GraphicsContext.Create(dc)

    dc.SetBackground(wx.Brush(_BG))
    dc.Clear()

    # Accent rounded border.
    inset = size * 0.0625
    gc.SetPen(wx.Pen(_ACCENT, max(2, int(size * 0.03))))
    gc.SetBrush(wx.TRANSPARENT_BRUSH)
    gc.DrawRoundedRectangle(inset, inset, size - 2 * inset, size - 2 * inset, size * 0.14)

    # "QL" centered.
    font = wx.Font(wx.FontInfo(int(size * 0.47)).Bold().Family(wx.FONTFAMILY_DEFAULT))
    gc.SetFont(font, _ACCENT)
    text = "QL"
    tw, th = gc.GetTextExtent(text)
    gc.DrawText(text, (size - tw) / 2, (size - th) / 2)

    dc.SelectObject(wx.NullBitmap)
    return bmp


def main() -> None:
    app = wx.App()  # noqa: F841 — needed for image handlers / GDI
    _ASSETS.mkdir(parents=True, exist_ok=True)

    image = render().ConvertToImage()
    png_path = _ASSETS / "icon.png"
    image.SaveFile(str(png_path), wx.BITMAP_TYPE_PNG)
    print(f"Wrote {png_path}")

    # ICO with a few common sizes (best-effort; ignored if unsupported).
    try:
        ico_path = _ASSETS / "icon.ico"
        image.SaveFile(str(ico_path), wx.BITMAP_TYPE_ICO)
        print(f"Wrote {ico_path}")
    except Exception as exc:  # pragma: no cover
        print(f"ICO not written ({exc}); PNG is enough for the app.")


if __name__ == "__main__":
    main()
