"""Catalog of common Quake Live server cvars and console commands.

Used to power input autocompletion. Not exhaustive — covers the cvars/commands
most relevant to server administration. Extend ``CVARS`` / ``COMMANDS`` freely.
"""

from __future__ import annotations

from dataclasses import dataclass

CVAR = "cvar"
CMD = "cmd"
VALUE = "value"
PLAYER = "player"


@dataclass(frozen=True)
class Entry:
    name: str
    kind: str  # CVAR, CMD, VALUE or PLAYER
    desc: str


# Commands whose argument is a player. The autocomplete completes player names
# for these; NUMERIC_PLAYER_COMMANDS complete the client slot number instead.
PLAYER_COMMANDS = {"kick", "clientkick", "put", "mute", "unmute", "tell", "dumpuser"}
NUMERIC_PLAYER_COMMANDS = {"clientkick", "put"}

# Commands that take a "<cvar> <value>" pair.
SET_COMMANDS = {"set", "seta", "sets", "setu"}


# (name, description) — server-relevant cvars.
_CVARS: list[tuple[str, str]] = [
    ("sv_hostname", "имя сервера"),
    ("sv_maxclients", "макс. число слотов"),
    ("sv_privateClients", "число приватных слотов"),
    ("sv_privatePassword", "пароль приватных слотов"),
    ("sv_password", "пароль входа на сервер"),
    ("g_password", "пароль игры"),
    ("sv_fps", "частота тиков сервера"),
    ("sv_pure", "только официальные паки (0/1)"),
    ("sv_floodProtect", "защита от флуда чата"),
    ("sv_maxRate", "макс. rate клиентов"),
    ("sv_minPing", "мин. пинг для входа"),
    ("sv_maxPing", "макс. пинг для входа"),
    ("sv_allowDownload", "разрешить загрузку контента"),
    ("sv_timeout", "таймаут соединения, сек"),
    ("sv_zombietime", "время хранения отключившихся"),
    ("timelimit", "лимит времени матча, мин"),
    ("fraglimit", "лимит фрагов"),
    ("capturelimit", "лимит захватов флага"),
    ("roundlimit", "лимит раундов"),
    ("scorelimit", "лимит очков"),
    ("g_gametype", "режим: 0 FFA,1 Duel,3 TDM,4 CA,5 CTF,..."),
    ("g_instagib", "инстагиб (0/1)"),
    ("g_weaponRespawn", "время респавна оружия, сек"),
    ("g_quadFactor", "множитель урона Quad"),
    ("g_startingHealth", "стартовое здоровье"),
    ("g_startingArmor", "стартовая броня"),
    ("g_friendlyFire", "урон по своим (0/1)"),
    ("g_doWarmup", "включить разминку (0/1)"),
    ("g_warmup", "длительность разминки, сек"),
    ("g_warmupReadyPercentage", "% готовых для старта"),
    ("g_teamForceBalance", "принудительный баланс команд"),
    ("g_teamAutoJoin", "авто-присоединение к команде"),
    ("g_allowVote", "разрешить голосования (0/1)"),
    ("g_voteFlags", "флаги доступных голосований"),
    ("g_inactivity", "время до кика за бездействие, сек"),
    ("g_motd", "сообщение дня"),
    ("g_overtime", "овертайм"),
    ("g_redTeam", "название красной команды (arena)"),
    ("g_blueTeam", "название синей команды (arena)"),
    ("g_spawnProtectionTime", "защита после спавна, мс"),
    ("g_infiniteAmmo", "бесконечные патроны (0/1)"),
    ("g_loadout", "система лоадаутов (0/1)"),
    ("g_itemTimers", "таймеры предметов (0/1)"),
    ("g_gravity", "гравитация"),
    ("g_speed", "скорость движения"),
    ("g_knockback", "сила отбрасывания"),
    ("dmflags", "флаги deathmatch"),
    ("bot_enable", "включить ботов (0/1)"),
    ("bot_minplayers", "добивать ботами до N игроков"),
    ("g_spSkill", "сложность ботов (1-5)"),
    ("pmove_fixed", "фиксированный pmove (0/1)"),
    ("pmove_msec", "шаг pmove, мс"),
    ("com_maxfps", "лимит fps"),
    ("mapname", "текущая карта (read-only)"),
    ("nextmap", "следующая карта/действие"),
    ("zmq_rcon_enable", "включить ZMQ RCON (0/1)"),
    ("zmq_rcon_password", "пароль RCON"),
    ("zmq_rcon_port", "порт RCON"),
    ("zmq_stats_enable", "включить ZMQ stats (0/1)"),
    ("zmq_stats_password", "пароль stats"),
    ("zmq_stats_port", "порт stats"),
    # disable_* — убрать предмет/оружие/боеприпас с карты (0/1)
    ("disable_weapon_gauntlet", "отключить гантлет"),
    ("disable_weapon_machinegun", "отключить пулемёт"),
    ("disable_weapon_shotgun", "отключить дробовик"),
    ("disable_weapon_grenadelauncher", "отключить гранатомёт"),
    ("disable_weapon_rocketlauncher", "отключить ракетницу"),
    ("disable_weapon_lightning", "отключить молнию (LG)"),
    ("disable_weapon_railgun", "отключить рейлган"),
    ("disable_weapon_plasmagun", "отключить плазмаган"),
    ("disable_weapon_bfg", "отключить BFG"),
    ("disable_weapon_grapplinghook", "отключить крюк"),
    ("disable_weapon_nailgun", "отключить нейлган"),
    ("disable_weapon_prox_launcher", "отключить минный гранатомёт"),
    ("disable_weapon_chaingun", "отключить чейнган"),
    ("disable_ammo_shells", "отключить патроны дробовика"),
    ("disable_ammo_bullets", "отключить патроны пулемёта"),
    ("disable_ammo_grenades", "отключить гранаты"),
    ("disable_ammo_cells", "отключить ячейки (плазма)"),
    ("disable_ammo_lightning", "отключить заряды молнии"),
    ("disable_ammo_rockets", "отключить ракеты"),
    ("disable_ammo_slugs", "отключить слаги (рейл)"),
    ("disable_ammo_bfg", "отключить заряды BFG"),
    ("disable_ammo_nails", "отключить гвозди (нейлган)"),
    ("disable_ammo_mines", "отключить мины"),
    ("disable_ammo_belt", "отключить ленту (чейнган)"),
    ("disable_item_armor_shard", "отключить осколок брони"),
    ("disable_item_armor_combat", "отключить жёлтую броню"),
    ("disable_item_armor_body", "отключить красную броню"),
    ("disable_item_health_small", "отключить +5 HP"),
    ("disable_item_health", "отключить +25 HP"),
    ("disable_item_health_large", "отключить +50 HP"),
    ("disable_item_health_mega", "отключить мегахелс"),
    ("disable_item_quad", "отключить Quad Damage"),
    ("disable_item_enviro", "отключить Battle Suit"),
    ("disable_item_haste", "отключить Haste"),
    ("disable_item_invis", "отключить Invisibility"),
    ("disable_item_regen", "отключить Regeneration"),
    ("disable_item_flight", "отключить Flight"),
    ("disable_holdable_teleporter", "отключить телепорт (holdable)"),
    ("disable_holdable_medkit", "отключить аптечку (holdable)"),
    ("disable_holdable_kamikaze", "отключить камикадзе"),
    ("disable_holdable_portal", "отключить портал"),
    ("disable_holdable_invulnerability", "отключить неуязвимость"),
    ("disable_item_scout", "отключить Scout"),
    ("disable_item_guard", "отключить Guard"),
    ("disable_item_doubler", "отключить Doubler"),
    ("disable_item_ammoregen", "отключить Ammo Regen"),
    ("disable_item_redcube", "отключить красный куб (Harvester)"),
    ("disable_item_bluecube", "отключить синий куб (Harvester)"),
    ("disable_team_CTF_redflag", "отключить красный флаг (CTF)"),
    ("disable_team_CTF_blueflag", "отключить синий флаг (CTF)"),
    ("disable_team_CTF_neutralflag", "отключить нейтральный флаг (1FCTF)"),
]

# (name, description) — console commands.
_COMMANDS: list[tuple[str, str]] = [
    ("map", "сменить карту: map <name>"),
    ("devmap", "карта в dev-режиме: devmap <name>"),
    ("map_restart", "перезапустить текущую карту"),
    ("addbot", "добавить бота: addbot <name> [skill] [team]"),
    ("kick", "кикнуть игрока: kick <name>"),
    ("kickall", "кикнуть всех игроков"),
    ("clientkick", "кик по номеру слота: clientkick <num>"),
    ("status", "статус сервера и список игроков"),
    ("players", "список игроков (QL)"),
    ("serverinfo", "серверные cvar'ы"),
    ("systeminfo", "системные cvar'ы"),
    ("dumpuser", "userinfo игрока: dumpuser <name>"),
    ("say", "сообщение от сервера: say <text>"),
    ("tell", "личное сообщение: tell <num> <text>"),
    ("cvarlist", "список cvar'ов: cvarlist [фильтр]"),
    ("cmdlist", "список команд: cmdlist [фильтр]"),
    ("set", "задать cvar: set <name> <value>"),
    ("seta", "задать и сохранить cvar (archive)"),
    ("sets", "задать серверный cvar (serverinfo)"),
    ("setu", "задать userinfo cvar"),
    ("reset", "сбросить cvar: reset <name>"),
    ("exec", "выполнить конфиг: exec <file.cfg>"),
    ("vstr", "выполнить строковую переменную: vstr <var>"),
    ("echo", "вывести текст: echo <text>"),
    ("heartbeat", "пинг мастер-серверу"),
    ("killserver", "остановить сервер"),
    ("quit", "завершить работу сервера"),
    ("shuffle", "перемешать команды (QL)"),
    ("allready", "снять разминку, все готовы (QL)"),
    ("abort", "прервать текущий матч (QL)"),
    ("pause", "поставить матч на паузу (QL)"),
    ("unpause", "снять паузу (QL)"),
    ("lock", "закрыть команду: lock <red|blue|free>"),
    ("unlock", "открыть команду: unlock <red|blue|free>"),
    ("put", "переместить игрока: put <id> <team>"),
    ("mute", "замьютить игрока: mute <id>"),
    ("unmute", "снять мьют: unmute <id>"),
]

# Optional bulk catalog generated from a live server's `cvarlist`/`cmdlist`
# dump (see tools/import_cvarlist.py). Curated entries above take priority;
# generated ones fill in the long tail with the cvar's current value as hint.
try:
    from ._generated import GENERATED_CMDS, GENERATED_CVARS  # type: ignore
except ImportError:
    GENERATED_CVARS: list[tuple[str, str]] = []
    GENERATED_CMDS: list[tuple[str, str]] = []


def _merge(curated: list[tuple[str, str]], generated: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = {name for name, _ in curated}
    merged = list(curated)
    for name, desc in generated:
        if name not in seen:
            merged.append((name, desc))
            seen.add(name)
    return merged


CVARS: list[Entry] = [Entry(n, CVAR, d) for n, d in _merge(_CVARS, GENERATED_CVARS)]
COMMANDS: list[Entry] = [Entry(n, CMD, d) for n, d in _merge(_COMMANDS, GENERATED_CMDS)]
ALL_ENTRIES: list[Entry] = COMMANDS + CVARS


# Discrete value suggestions for specific cvars: cvar -> [(value, label), ...].
_CVAR_VALUES: dict[str, list[tuple[str, str]]] = {
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
        ("1", "очень легко"),
        ("2", "легко"),
        ("3", "средне"),
        ("4", "сложно"),
        ("5", "кошмар"),
    ],
}

# Cvars that are simple 0/1 toggles.
_BOOL_CVARS = {
    "sv_pure", "sv_floodProtect", "sv_allowDownload", "g_instagib",
    "g_friendlyFire", "g_doWarmup", "g_teamForceBalance", "g_teamAutoJoin",
    "g_allowVote", "g_infiniteAmmo", "g_loadout", "g_itemTimers", "pmove_fixed",
    "bot_enable", "zmq_rcon_enable", "zmq_stats_enable",
}

_BOOL_VALUES = [("0", "выкл"), ("1", "вкл")]


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
