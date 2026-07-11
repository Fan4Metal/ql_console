# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A wxPython desktop app (Windows-first) for administering **Quake Live** servers over
RCON. It connects to one or more servers, sends console commands, shows the text
responses, and subscribes to a live event stream (kills, chat, connects). UI strings
are bilingual (Russian default, English) — see i18n below.

## Commands

Package manager is **uv**. There is no test suite, linter, or type-check config in
the repo — do not assume `pytest`/`ruff`/`mypy` exist here.

```bash
uv sync                              # create venv + install deps
uv run main.py                       # run the app (or: uv run ql-console)
uv run python tools/build_exe.py     # build dist/ql-console/ (one-dir .exe, PyInstaller)
uv run python tools/import_cvarlist.py cvarlist.txt cmdlist.txt   # regen _generated.py
```

Verifying a change means running the app (`uv run main.py`) and exercising the flow,
since there are no automated tests.

## Architecture

**Threading model is the central constraint.** All ZeroMQ socket I/O runs on
dedicated background threads (`RconClient`, `StatsClient`), one per socket. Those
threads must never touch wx widgets. `ServerConnection` ([connection.py](src/ql_console/connection.py))
is the seam: it wraps every client callback in `wx.CallAfter(...)` so results are
marshalled onto the wx main thread before any UI code sees them. When adding a new
data path from a socket to the UI, route it through this same `wx.CallAfter` bridge.

**Two ZeroMQ protocols** (both PLAIN auth; details in each module's docstring):
- RCON — `DEALER` socket. Must send a `register` frame *after* the monitor reports
  `EVENT_CONNECTED`; only then may commands be sent. Replies arrive as many small
  text frames that must be reassembled on `\n` boundaries (see `_rx_buffer` in
  [rcon_client.py](src/ql_console/rcon_client.py)).
- Stats — `SUB` socket, subscribe to everything, no `register` step. Events are JSON
  objects. [stats_client.py](src/ql_console/stats_client.py) reuses the RCON status/error
  constants.

Both clients watch the ZMQ **monitor socket** to detect handshake success/auth
failure/unreachable-endpoint, because ZeroMQ connects asynchronously and would
otherwise retry a bad endpoint forever with no error surfaced. Connection status is
reported as `(channel, status, detail)` tuples using the `STATUS_*` / `ERR_*`
constants from rcon_client.

**[main_frame.py](src/ql_console/ui/main_frame.py) is the orchestrator** (~1000 lines, the
bulk of the app). It holds one `_ServerState` per configured server, keyed by
`id(ServerConfig)`, so each server keeps its own scrollback, event log, roster, and
command history even while switching between servers. It owns all the messy
QL-text-parsing logic: the server wraps output as `print "...\n"` with quotes glued
to the next frame, so output goes through `_clean_output_line` and several regexes
(`_RCON_ECHO_RE`, `_CVAR_RESPONSE_RE`, `_SERVERINFO_RE`). On connect it silently runs
`players` + `serverinfo` to seed the roster and build a one-line server summary.

**Roster** ([roster.py](src/ql_console/roster.py)) is fed from two sources — parsed
`players` RCON output and `PLAYER_CONNECT`/`PLAYER_DISCONNECT` stats events — and keys
players by Steam ID (stable across name changes) falling back to name.

**Autocomplete** ([ui/autocomplete.py](src/ql_console/ui/autocomplete.py) +
[commands.py](src/ql_console/commands.py)) is a popup over the command input. The catalog
in commands.py is two layers: curated `_CVARS`/`_COMMANDS` (bilingual `(name, ru, en)`
triples, always win) merged with an optional bulk `_generated.py` catalog imported
from a live server's `cvarlist` dump (single-language, carries the cvar's default
value as the hint). `commands.py` holds module-level hint state (`set_hint_language`,
`set_hide_default_values`) that `main_frame` pushes settings into.

## Conventions

- **i18n**: never hardcode user-facing strings. Add a key to `_TRANSLATIONS` in
  [i18n.py](src/ql_console/i18n.py) with both `en` and `ru`, then use `t("key")` /
  `t("key", name=...)`. Language changes retranslate live (`_retranslate` in main_frame),
  so labels are re-fetched, not cached at construction.
- **Settings flow**: a new preference is added to `AppSettings` in
  [config.py](src/ql_console/config.py), a control in
  [ui/settings_dialog.py](src/ql_console/ui/settings_dialog.py) (read in `get_settings`),
  and wired in `main_frame._on_open_settings` — applied live without restart, mirroring
  the existing `hint_language` / `hide_default_hints` handling.
- **Config storage**: servers + settings persist as plain JSON at
  `%APPDATA%\ql_console\servers.json` (override with `QL_CONSOLE_CONFIG`). Passwords are
  stored in plaintext by design. `from_dict` filters unknown keys, so adding a field is
  forward/backward compatible.
- **Generated files**: `_generated.py` (cvar catalog) and `_commit.py` (build-time git
  hash, read by [build_info.py](src/ql_console/build_info.py)) are machine-written — don't
  hand-edit; regenerate via the tools.
- Every module uses `from __future__ import annotations`.
