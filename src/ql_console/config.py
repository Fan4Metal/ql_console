"""Server configuration: load/save the list of servers from a JSON file.

The file is a simple JSON document so it can be edited by hand. RCON/stats
passwords are stored in plaintext (per project decision) — keep the file private.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def default_config_path() -> Path:
    """Location of servers.json next to the user's config (override with QL_CONSOLE_CONFIG)."""
    override = os.environ.get("QL_CONSOLE_CONFIG")
    if override:
        return Path(override)
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / "ql_console" / "servers.json"


@dataclass
class ServerConfig:
    """Connection settings for a single Quake Live server."""

    name: str = "New Server"
    host: str = "127.0.0.1"
    rcon_port: int = 28960
    rcon_password: str = ""
    stats_port: int = 27960
    stats_password: str = ""
    stats_enabled: bool = False  # off by default — stats is verbose, mainly for debugging

    @property
    def rcon_endpoint(self) -> str:
        return f"tcp://{self.host}:{self.rcon_port}"

    @property
    def stats_endpoint(self) -> str:
        return f"tcp://{self.host}:{self.stats_port}"

    @property
    def game_port(self) -> int:
        """Port players connect to: QL puts RCON 1000 above the game port."""
        return self.rcon_port - 1000

    @property
    def steam_connect_url(self) -> str:
        return f"steam://connect/{self.host}:{self.game_port}"

    @classmethod
    def from_dict(cls, data: dict) -> "ServerConfig":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class AppSettings:
    """Application-wide preferences (extend with new options as needed)."""

    # General
    language: str = "ru"  # UI language code ("en" / "ru")
    hint_language: str = ""  # autocomplete-hint language; "" = follow the UI language
    hide_default_hints: bool = False  # hide the cvar default value in autocomplete hints
    # View
    hide_rcon_echo: bool = True  # hide "zmq RCON command from ..." echo lines
    clean_output: bool = True  # strip print "..." wrappers/stray quotes from output
    console_font_face: str = "Consolas"  # empty = default monospace font
    console_font_size: int = 11
    console_bg: str = "#000000"  # console/events background color

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class AppConfig:
    """Top-level config: the ordered list of servers plus app settings."""

    servers: list[ServerConfig] = field(default_factory=list)
    settings: AppSettings = field(default_factory=AppSettings)

    def to_dict(self) -> dict:
        return {
            "servers": [asdict(s) for s in self.servers],
            "settings": asdict(self.settings),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        return cls(
            servers=[ServerConfig.from_dict(s) for s in data.get("servers", [])],
            settings=AppSettings.from_dict(data.get("settings", {})),
        )


def load_config(path: Path | None = None) -> AppConfig:
    path = path or default_config_path()
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return AppConfig()
    return AppConfig.from_dict(data)


def save_config(config: AppConfig, path: Path | None = None) -> None:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
