"""Dialog for adding or editing a single server's connection settings."""

from __future__ import annotations

import wx

from ..config import ServerConfig
from ..i18n import t


class ServerDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, server: ServerConfig | None = None) -> None:
        title = t("dlg_edit_server") if server else t("dlg_add_server")
        super().__init__(parent, title=title)
        self.SetMinSize(self.FromDIP(wx.Size(420, -1)))
        self._server = server or ServerConfig()

        grid = wx.FlexGridSizer(rows=0, cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        self.name = wx.TextCtrl(self, value=self._server.name)
        self.host = wx.TextCtrl(self, value=self._server.host)
        self.rcon_port = wx.SpinCtrl(self, min=1, max=65535, initial=self._server.rcon_port)
        self.rcon_password = wx.TextCtrl(
            self, value=self._server.rcon_password, style=wx.TE_PASSWORD
        )
        self.stats_enabled = wx.CheckBox(self, label=t("chk_stats"))
        self.stats_enabled.SetValue(self._server.stats_enabled)
        self.stats_port = wx.SpinCtrl(self, min=1, max=65535, initial=self._server.stats_port)
        self.stats_password = wx.TextCtrl(
            self, value=self._server.stats_password, style=wx.TE_PASSWORD
        )

        def row(label: str, ctrl: wx.Window) -> None:
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        row(t("lbl_name"), self.name)
        row(t("lbl_host"), self.host)
        row(t("lbl_rcon_port"), self.rcon_port)
        row(t("lbl_rcon_password"), self.rcon_password)
        grid.Add((0, 0))
        grid.Add(self.stats_enabled, 0, wx.EXPAND)
        row(t("lbl_stats_port"), self.stats_port)
        row(t("lbl_stats_password"), self.stats_password)

        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(grid, 1, wx.EXPAND | wx.ALL, 12)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)

        self.stats_enabled.Bind(wx.EVT_CHECKBOX, self._on_toggle_stats)
        self._on_toggle_stats()

    def _on_toggle_stats(self, _event: wx.Event | None = None) -> None:
        enabled = self.stats_enabled.GetValue()
        self.stats_port.Enable(enabled)
        self.stats_password.Enable(enabled)

    def get_server(self) -> ServerConfig:
        """Return a ServerConfig built from the current field values."""
        return ServerConfig(
            name=self.name.GetValue().strip() or t("server_unnamed"),
            host=self.host.GetValue().strip(),
            rcon_port=self.rcon_port.GetValue(),
            rcon_password=self.rcon_password.GetValue(),
            stats_port=self.stats_port.GetValue(),
            stats_password=self.stats_password.GetValue(),
            stats_enabled=self.stats_enabled.GetValue(),
        )
