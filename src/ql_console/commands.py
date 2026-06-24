"""Catalog of common Quake Live server cvars and console commands.

Used to power input autocompletion. Not exhaustive — covers the cvars/commands
most relevant to server administration. Extend ``_CVARS`` / ``_COMMANDS`` freely.

Curated descriptions are bilingual ``(name, ru, en)`` triples; ``Entry.desc``
resolves to the current UI language at lookup time, so switching language updates
the hints without a restart. Generated entries carry a single-language string.
"""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import current_language

CVAR = "cvar"
CMD = "cmd"
VALUE = "value"
PLAYER = "player"

# A description is either a plain string (generated/dynamic entries) or a
# ``{lang: text}`` map (curated entries) resolved per current language.
Desc = str | dict[str, str]

# Language used for curated hint descriptions, chosen independently of the UI.
# ``None`` (the default) means "follow the UI language".
_hint_language: str | None = None


def set_hint_language(lang: str | None) -> None:
    """Set the language for autocomplete hints; falsy/None = follow the UI."""
    global _hint_language
    _hint_language = lang or None


def hint_language() -> str:
    """The active hint language (the explicit override, or the UI language)."""
    return _hint_language or current_language()


@dataclass(frozen=True)
class Entry:
    name: str
    kind: str  # CVAR, CMD, VALUE or PLAYER
    desc_raw: Desc

    @property
    def desc(self) -> str:
        """The description in the active hint language (falls back to en/name)."""
        d = self.desc_raw
        if isinstance(d, dict):
            return d.get(hint_language()) or d.get("en") or self.name
        return d


# Commands whose argument is a player. The autocomplete completes player names
# for these; NUMERIC_PLAYER_COMMANDS complete the client slot number instead.
PLAYER_COMMANDS = {"kick", "clientkick", "put", "mute", "unmute", "tell", "dumpuser"}
NUMERIC_PLAYER_COMMANDS = {"clientkick", "put"}

# Commands that take a "<cvar> <value>" pair.
SET_COMMANDS = {"set", "seta", "sets", "setu"}


# (name, ru, en) — server-relevant cvars.
_CVARS: list[tuple[str, str, str]] = [
    ("sv_hostname", "имя сервера", "server name"),
    ("sv_maxclients", "макс. число слотов", "max player slots"),
    ("sv_privateClients", "число приватных слотов", "number of private slots"),
    ("sv_privatePassword", "пароль приватных слотов", "private slot password"),
    ("sv_password", "пароль входа на сервер", "server join password"),
    ("g_password", "пароль игры", "game password"),
    ("sv_fps", "частота тиков сервера", "server tick rate"),
    ("sv_pure", "только официальные паки (0/1)", "official paks only (0/1)"),
    ("sv_floodProtect", "защита от флуда чата", "chat flood protection"),
    ("sv_maxRate", "макс. rate клиентов", "max client rate"),
    ("sv_minPing", "мин. пинг для входа", "min ping to join"),
    ("sv_maxPing", "макс. пинг для входа", "max ping to join"),
    ("sv_allowDownload", "разрешить загрузку контента", "allow content download"),
    ("sv_timeout", "таймаут соединения, сек", "connection timeout, sec"),
    ("sv_zombietime", "время хранения отключившихся", "disconnected-client retention time"),
    ("timelimit", "лимит времени матча, мин", "match time limit, min"),
    ("fraglimit", "лимит фрагов", "frag limit"),
    ("capturelimit", "лимит захватов флага", "flag capture limit"),
    ("roundlimit", "лимит раундов", "round limit"),
    ("scorelimit", "лимит очков", "score limit"),
    (
        "g_gametype",
        "режим: 0 FFA,1 Duel,3 TDM,4 CA,5 CTF,...",
        "mode: 0 FFA,1 Duel,3 TDM,4 CA,5 CTF,...",
    ),
    ("g_instagib", "инстагиб (0/1)", "instagib (0/1)"),
    ("g_weaponRespawn", "время респавна оружия, сек", "weapon respawn time, sec"),
    ("g_quadFactor", "множитель урона Quad", "Quad damage multiplier"),
    ("g_startingHealth", "стартовое здоровье", "starting health"),
    ("g_startingArmor", "стартовая броня", "starting armor"),
    ("g_friendlyFire", "урон по своим (0/1)", "friendly fire (0/1)"),
    ("g_doWarmup", "включить разминку (0/1)", "enable warmup (0/1)"),
    ("g_warmup", "длительность разминки, сек", "warmup duration, sec"),
    ("g_warmupReadyPercentage", "% готовых для старта", "% ready to start"),
    ("g_teamForceBalance", "принудительный баланс команд", "force team balance"),
    ("g_teamAutoJoin", "авто-присоединение к команде", "auto-join a team"),
    ("g_allowVote", "разрешить голосования (0/1)", "allow voting (0/1)"),
    ("g_voteFlags", "флаги доступных голосований", "allowed vote flags"),
    ("g_inactivity", "время до кика за бездействие, сек", "idle-kick time, sec"),
    ("g_motd", "сообщение дня", "message of the day"),
    ("g_overtime", "овертайм", "overtime"),
    ("g_redTeam", "название красной команды (arena)", "red team name (arena)"),
    ("g_blueTeam", "название синей команды (arena)", "blue team name (arena)"),
    ("g_spawnProtectionTime", "защита после спавна, мс", "spawn protection, ms"),
    ("g_infiniteAmmo", "бесконечные патроны (0/1)", "infinite ammo (0/1)"),
    ("g_loadout", "система лоадаутов (0/1)", "loadout system (0/1)"),
    ("g_itemTimers", "таймеры предметов (0/1)", "item timers (0/1)"),
    ("g_gravity", "гравитация", "gravity"),
    ("g_speed", "скорость движения", "movement speed"),
    ("g_knockback", "сила отбрасывания", "knockback strength"),
    ("dmflags", "флаги deathmatch", "deathmatch flags"),
    ("bot_enable", "включить ботов (0/1)", "enable bots (0/1)"),
    ("bot_minplayers", "добивать ботами до N игроков", "fill with bots up to N players"),
    ("g_spSkill", "сложность ботов (1-5)", "bot difficulty (1-5)"),
    ("pmove_fixed", "фиксированный pmove (0/1)", "fixed pmove (0/1)"),
    ("pmove_msec", "шаг pmove, мс", "pmove step, ms"),
    ("com_maxfps", "лимит fps", "fps limit"),
    ("mapname", "текущая карта (read-only)", "current map (read-only)"),
    ("nextmap", "следующая карта/действие", "next map/action"),
    ("zmq_rcon_enable", "включить ZMQ RCON (0/1)", "enable ZMQ RCON (0/1)"),
    ("zmq_rcon_password", "пароль RCON", "RCON password"),
    ("zmq_rcon_port", "порт RCON", "RCON port"),
    ("zmq_stats_enable", "включить ZMQ stats (0/1)", "enable ZMQ stats (0/1)"),
    ("zmq_stats_password", "пароль stats", "stats password"),
    ("zmq_stats_port", "порт stats", "stats port"),
    # disable_* — убрать предмет/оружие/боеприпас с карты (0/1)
    ("disable_weapon_gauntlet", "отключить гантлет", "disable Gauntlet"),
    ("disable_weapon_machinegun", "отключить пулемёт", "disable Machinegun"),
    ("disable_weapon_shotgun", "отключить дробовик", "disable Shotgun"),
    ("disable_weapon_grenadelauncher", "отключить гранатомёт", "disable Grenade Launcher"),
    ("disable_weapon_rocketlauncher", "отключить ракетницу", "disable Rocket Launcher"),
    ("disable_weapon_lightning", "отключить молнию (LG)", "disable Lightning Gun (LG)"),
    ("disable_weapon_railgun", "отключить рейлган", "disable Railgun"),
    ("disable_weapon_plasmagun", "отключить плазмаган", "disable Plasma Gun"),
    ("disable_weapon_bfg", "отключить BFG", "disable BFG"),
    ("disable_weapon_grapplinghook", "отключить крюк", "disable Grappling Hook"),
    ("disable_weapon_nailgun", "отключить нейлган", "disable Nailgun"),
    ("disable_weapon_prox_launcher", "отключить минный гранатомёт", "disable Proximity Launcher"),
    ("disable_weapon_chaingun", "отключить чейнган", "disable Chaingun"),
    ("disable_ammo_shells", "отключить патроны дробовика", "disable shotgun shells"),
    ("disable_ammo_bullets", "отключить патроны пулемёта", "disable machinegun bullets"),
    ("disable_ammo_grenades", "отключить гранаты", "disable grenades"),
    ("disable_ammo_cells", "отключить ячейки (плазма)", "disable cells (plasma)"),
    ("disable_ammo_lightning", "отключить заряды молнии", "disable lightning charges"),
    ("disable_ammo_rockets", "отключить ракеты", "disable rockets"),
    ("disable_ammo_slugs", "отключить слаги (рейл)", "disable slugs (rail)"),
    ("disable_ammo_bfg", "отключить заряды BFG", "disable BFG ammo"),
    ("disable_ammo_nails", "отключить гвозди (нейлган)", "disable nails (nailgun)"),
    ("disable_ammo_mines", "отключить мины", "disable mines"),
    ("disable_ammo_belt", "отключить ленту (чейнган)", "disable belt (chaingun)"),
    ("disable_item_armor_shard", "отключить осколок брони", "disable armor shard"),
    ("disable_item_armor_combat", "отключить жёлтую броню", "disable yellow armor"),
    ("disable_item_armor_body", "отключить красную броню", "disable red armor"),
    ("disable_item_health_small", "отключить +5 HP", "disable +5 HP"),
    ("disable_item_health", "отключить +25 HP", "disable +25 HP"),
    ("disable_item_health_large", "отключить +50 HP", "disable +50 HP"),
    ("disable_item_health_mega", "отключить мегахелс", "disable mega health"),
    ("disable_item_quad", "отключить Quad Damage", "disable Quad Damage"),
    ("disable_item_enviro", "отключить Battle Suit", "disable Battle Suit"),
    ("disable_item_haste", "отключить Haste", "disable Haste"),
    ("disable_item_invis", "отключить Invisibility", "disable Invisibility"),
    ("disable_item_regen", "отключить Regeneration", "disable Regeneration"),
    ("disable_item_flight", "отключить Flight", "disable Flight"),
    ("disable_holdable_teleporter", "отключить телепорт (holdable)", "disable Teleporter (holdable)"),
    ("disable_holdable_medkit", "отключить аптечку (holdable)", "disable Medkit (holdable)"),
    ("disable_holdable_kamikaze", "отключить камикадзе", "disable Kamikaze"),
    ("disable_holdable_portal", "отключить портал", "disable Portal"),
    ("disable_holdable_invulnerability", "отключить неуязвимость", "disable Invulnerability"),
    ("disable_item_scout", "отключить Scout", "disable Scout"),
    ("disable_item_guard", "отключить Guard", "disable Guard"),
    ("disable_item_doubler", "отключить Doubler", "disable Doubler"),
    ("disable_item_ammoregen", "отключить Ammo Regen", "disable Ammo Regen"),
    ("disable_item_redcube", "отключить красный куб (Harvester)", "disable red cube (Harvester)"),
    ("disable_item_bluecube", "отключить синий куб (Harvester)", "disable blue cube (Harvester)"),
    ("disable_team_CTF_redflag", "отключить красный флаг (CTF)", "disable red flag (CTF)"),
    ("disable_team_CTF_blueflag", "отключить синий флаг (CTF)", "disable blue flag (CTF)"),
    (
        "disable_team_CTF_neutralflag",
        "отключить нейтральный флаг (1FCTF)",
        "disable neutral flag (1FCTF)",
    ),
]

# (name, ru, en) — console commands.
_COMMANDS: list[tuple[str, str, str]] = [
    ("map", "сменить карту: map <name>", "change map: map <name>"),
    ("devmap", "карта в dev-режиме: devmap <name>", "map in dev mode: devmap <name>"),
    ("map_restart", "перезапустить текущую карту", "restart current map"),
    ("addbot", "добавить бота: addbot <name> [skill] [team]", "add a bot: addbot <name> [skill] [team]"),
    ("kick", "кикнуть игрока: kick <name>", "kick a player: kick <name>"),
    ("kickall", "кикнуть всех игроков", "kick all players"),
    ("clientkick", "кик по номеру слота: clientkick <num>", "kick by slot number: clientkick <num>"),
    ("status", "статус сервера и список игроков", "server status and player list"),
    ("players", "список игроков (QL)", "player list (QL)"),
    ("serverinfo", "серверные cvar'ы", "server cvars"),
    ("systeminfo", "системные cvar'ы", "system cvars"),
    ("dumpuser", "userinfo игрока: dumpuser <name>", "player userinfo: dumpuser <name>"),
    ("say", "сообщение от сервера: say <text>", "server message: say <text>"),
    ("tell", "личное сообщение: tell <num> <text>", "private message: tell <num> <text>"),
    ("cvarlist", "список cvar'ов: cvarlist [фильтр]", "list cvars: cvarlist [filter]"),
    ("cmdlist", "список команд: cmdlist [фильтр]", "list commands: cmdlist [filter]"),
    ("set", "задать cvar: set <name> <value>", "set a cvar: set <name> <value>"),
    ("seta", "задать и сохранить cvar (archive)", "set and archive a cvar"),
    ("sets", "задать серверный cvar (serverinfo)", "set a server cvar (serverinfo)"),
    ("setu", "задать userinfo cvar", "set a userinfo cvar"),
    ("reset", "сбросить cvar: reset <name>", "reset a cvar: reset <name>"),
    ("exec", "выполнить конфиг: exec <file.cfg>", "run a config: exec <file.cfg>"),
    ("vstr", "выполнить строковую переменную: vstr <var>", "execute a string variable: vstr <var>"),
    ("echo", "вывести текст: echo <text>", "print text: echo <text>"),
    ("heartbeat", "пинг мастер-серверу", "ping the master server"),
    ("killserver", "остановить сервер", "stop the server"),
    ("quit", "завершить работу сервера", "shut down the server"),
    ("shuffle", "перемешать команды (QL)", "shuffle teams (QL)"),
    ("allready", "снять разминку, все готовы (QL)", "end warmup, all ready (QL)"),
    ("abort", "прервать текущий матч (QL)", "abort the current match (QL)"),
    ("pause", "поставить матч на паузу (QL)", "pause the match (QL)"),
    ("unpause", "снять паузу (QL)", "unpause (QL)"),
    ("lock", "закрыть команду: lock <red|blue|free>", "lock a team: lock <red|blue|free>"),
    ("unlock", "открыть команду: unlock <red|blue|free>", "unlock a team: unlock <red|blue|free>"),
    ("put", "переместить игрока: put <id> <team>", "move a player: put <id> <team>"),
    ("mute", "замьютить игрока: mute <id>", "mute a player: mute <id>"),
    ("unmute", "снять мьют: unmute <id>", "unmute a player: unmute <id>"),
]

# Optional bulk catalog generated from a live server's `cvarlist`/`cmdlist`
# dump (see tools/import_cvarlist.py). Curated entries above take priority;
# generated ones fill in the long tail with the cvar's current value as hint.
try:
    from ._generated import GENERATED_CMDS, GENERATED_CVARS  # type: ignore
except ImportError:
    GENERATED_CVARS: list[tuple[str, str]] = []
    GENERATED_CMDS: list[tuple[str, str]] = []


def _bilingual(rows: list[tuple[str, str, str]]) -> list[tuple[str, Desc]]:
    """Turn ``(name, ru, en)`` triples into ``(name, {lang: text})`` pairs."""
    return [(name, {"ru": ru, "en": en}) for name, ru, en in rows]


def _merge(
    curated: list[tuple[str, Desc]], generated: list[tuple[str, str]]
) -> list[tuple[str, Desc]]:
    seen = {name for name, _ in curated}
    merged: list[tuple[str, Desc]] = list(curated)
    for name, desc in generated:
        if name not in seen:
            merged.append((name, desc))
            seen.add(name)
    return merged


CVARS: list[Entry] = [Entry(n, CVAR, d) for n, d in _merge(_bilingual(_CVARS), GENERATED_CVARS)]
COMMANDS: list[Entry] = [Entry(n, CMD, d) for n, d in _merge(_bilingual(_COMMANDS), GENERATED_CMDS)]
ALL_ENTRIES: list[Entry] = COMMANDS + CVARS


# Discrete value suggestions for specific cvars: cvar -> [(value, label), ...].
# Labels may be a plain string (same in every language) or a ``{lang: text}`` map.
_CVAR_VALUES: dict[str, list[tuple[str, Desc]]] = {
    "g_gametype": [
        ("0", "FFA"),
        ("1", "Duel"),
        ("2", "Race"),
        ("3", "Team Deathmatch"),
        ("4", "Clan Arena"),
        ("5", "CTF"),
        ("6", "One Flag CTF"),
        ("8", "Harvester"),
        ("9", "Freeze Tag"),
        ("10", "Domination"),
        ("11", "Attack & Defend"),
        ("12", "Red Rover"),
    ],
    "g_spSkill": [
        ("1", {"ru": "очень легко", "en": "very easy"}),
        ("2", {"ru": "легко", "en": "easy"}),
        ("3", {"ru": "средне", "en": "medium"}),
        ("4", {"ru": "сложно", "en": "hard"}),
        ("5", {"ru": "кошмар", "en": "nightmare"}),
    ],
}

# Cvars that are simple 0/1 toggles.
_BOOL_CVARS = {
    "sv_pure", "sv_floodProtect", "sv_allowDownload", "g_instagib",
    "g_friendlyFire", "g_doWarmup", "g_teamForceBalance", "g_teamAutoJoin",
    "g_allowVote", "g_infiniteAmmo", "g_loadout", "g_itemTimers", "pmove_fixed",
    "bot_enable", "zmq_rcon_enable", "zmq_stats_enable",
}

_BOOL_VALUES: list[tuple[str, Desc]] = [
    ("0", {"ru": "выкл", "en": "off"}),
    ("1", {"ru": "вкл", "en": "on"}),
]


def search(query: str, limit: int = 12, kinds: set[str] | None = None) -> list[Entry]:
    """Return entries matching ``query``, ranked best-first.

    Ranking: exact prefix on the name, then substring on the name, then
    substring in the description. Case-insensitive. ``kinds`` optionally limits
    to certain entry kinds (e.g. only ``CVAR``).
    """
    q = query.strip().lower()
    if not q:
        return []

    pool = ALL_ENTRIES if kinds is None else [e for e in ALL_ENTRIES if e.kind in kinds]
    prefix: list[Entry] = []
    name_sub: list[Entry] = []
    desc_sub: list[Entry] = []
    for entry in pool:
        name = entry.name.lower()
        if name.startswith(q):
            prefix.append(entry)
        elif q in name:
            name_sub.append(entry)
        elif q in entry.desc.lower():
            desc_sub.append(entry)

    return (prefix + name_sub + desc_sub)[:limit]


def value_entries(cvar: str) -> list[Entry]:
    """Known value suggestions for a cvar, or [] if none are defined."""
    name = cvar.lower()
    pairs = _CVAR_VALUES.get(name)
    if pairs is None and (name in _BOOL_CVARS or name.startswith("disable_")):
        pairs = _BOOL_VALUES
    if not pairs:
        return []
    return [Entry(value, VALUE, label) for value, label in pairs]


def search_values(cvar: str, query: str, limit: int = 12) -> list[Entry]:
    """Filter a cvar's value suggestions by ``query`` (prefix on value/label)."""
    entries = value_entries(cvar)
    q = query.strip().lower()
    if not q:
        return entries[:limit]
    matched = [e for e in entries if e.name.lower().startswith(q) or q in e.desc.lower()]
    return matched[:limit]
