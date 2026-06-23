"""Per-server connection: ties together the RCON and stats clients.

The background ZMQ threads invoke our callbacks off the GUI thread, so every
delivery is marshalled onto the wx main thread with ``wx.CallAfter``. The GUI
supplies one set of handlers per connection.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from .config import ServerConfig
from .rcon_client import RconClient
from .stats_client import StatsClient


class ServerConnection:
    """Owns the RCON + stats clients for a single configured server."""

    def __init__(
        self,
        server: ServerConfig,
        on_rcon_message: Callable[[str], None],
        on_stats_event: Callable[[dict], None],
        on_status: Callable[[str, str, str], None],
    ) -> None:
        """``on_status`` receives (channel, status, detail) where channel is
        'rcon' or 'stats'."""
        self.server = server
        self._on_rcon_message = on_rcon_message
        self._on_stats_event = on_stats_event
        self._on_status = on_status

        self.rcon = RconClient(
            server.rcon_endpoint,
            server.rcon_password,
            on_message=lambda text: wx.CallAfter(self._on_rcon_message, text),
            on_status=lambda status, detail: wx.CallAfter(
                self._on_status, "rcon", status, detail
            ),
        )
        self.stats: StatsClient | None = None
        if server.stats_enabled:
            self.stats = StatsClient(
                server.stats_endpoint,
                server.stats_password,
                on_event=lambda event: wx.CallAfter(self._on_stats_event, event),
                on_status=lambda status, detail: wx.CallAfter(
                    self._on_status, "stats", status, detail
                ),
            )

    def connect(self) -> None:
        self.rcon.start()
        if self.stats:
            self.stats.start()

    def disconnect(self) -> None:
        self.rcon.stop()
        if self.stats:
            self.stats.stop()

    def send(self, command: str) -> None:
        self.rcon.send(command)
