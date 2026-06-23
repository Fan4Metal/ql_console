"""Application entry point."""

from __future__ import annotations

import sys

import wx

from .ui.main_frame import MainFrame


def _enable_hidpi() -> None:
    """Opt into per-monitor DPI awareness on Windows for crisp HiDPI rendering.

    Must run before the first window is created. No-op on other platforms.
    """
    if sys.platform != "win32":
        return
    import ctypes

    try:  # Windows 10 1703+: per-monitor-v2 (best scaling for moving between monitors)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except (AttributeError, OSError):
        pass
    try:  # Windows 8.1+: per-monitor aware
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass
    try:  # Vista+: system DPI aware
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def main() -> None:
    _enable_hidpi()
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
