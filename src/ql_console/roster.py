"""Live player roster for a server, fed from RCON output and stats events.

Two sources keep it current:
  * parsing the text returned by the ``players`` RCON command
  * ``PLAYER_CONNECT`` / ``PLAYER_DISCONNECT`` stats events

Players are keyed by Steam ID when known (stable across name changes), else by
name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .colors import strip_colors


@dataclass
class Player:
    name: str
    steam_id: str = ""
    pid: int | None = None  # client slot, when known
    team: str = ""

    @property
    def key(self) -> str:
        return self.steam_id or f"name:{self.name.lower()}"


# A line of `players` output, e.g.:  ` 2 76561190000000001 A Player One`
# The single team column may be a letter (A/R/B/...) or blank:
#   ` 3 76561190000000002   Player Two`  (no team -> extra spaces)
# Lines arrive wrapped by the server as: print " 2 ... Player One\n"
_PLAYER_LINE = re.compile(
    r"^\s*(?P<pid>\d+)\s+(?P<steam>\d{15,18})\s(?P<team>\S?)\s+(?P<name>\S.*?)\s*$"
)


def parse_players_line(text: str) -> Player | None:
    """Parse one line of ``players`` output into a Player, or None if it doesn't match."""
    line = text.strip()
    # Unwrap `print "..."` and any stray surrounding quotes from the rcon stream.
    line = line.lstrip('"').strip()
    if line.startswith("print "):
        line = line[len("print ") :].strip()
    line = line.strip('"').replace("\\n", "").strip()
    match = _PLAYER_LINE.match(line)
    if not match:
        return None
    return Player(
        name=strip_colors(match.group("name")).strip(),
        steam_id=match.group("steam"),
        pid=int(match.group("pid")),
        team=match.group("team").strip(),
    )


@dataclass
class Roster:
    """The set of players currently known for one server."""

    players: dict[str, Player] = field(default_factory=dict)

    def list(self) -> list[Player]:
        return list(self.players.values())

    def upsert(self, player: Player) -> None:
        existing = self.players.get(player.key)
        if existing is None:
            self.players[player.key] = player
            return
        # Merge: keep any field that the new record fills in.
        if player.name:
            existing.name = player.name
        if player.pid is not None:
            existing.pid = player.pid
        if player.team:
            existing.team = player.team

    def remove(self, *, steam_id: str = "", name: str = "") -> None:
        key = steam_id or (f"name:{name.lower()}" if name else "")
        self.players.pop(key, None)

    def clear(self) -> None:
        self.players.clear()
