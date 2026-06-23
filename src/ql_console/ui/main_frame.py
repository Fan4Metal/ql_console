"""Main application window.

Layout: a server list on the left; on the right a notebook with an RCON
console (output + command input) and a live-events log. Each server keeps its
own output/event buffers so switching between servers preserves history.
"""

from __future__ import annotations

import json
import re

import wx

from .. import __version__, colors
from ..colors import RGB
from ..config import AppConfig, ServerConfig, load_config, save_config
from ..i18n import set_language, t
from ..connection import ServerConnection
from ..rcon_client import ERR_AUTH_FAILED, ERR_MAX_ATTEMPTS, MAX_ATTEMPTS
from ..roster import Player, Roster, parse_players_line
from .appicon import load_app_icon
from .autocomplete import AutoComplete
from .server_dialog import ServerDialog
from .settings_dialog import SettingsDialog

# A rendered line is a list of (rgb, text) runs.
Line = list[tuple[RGB, str]]

# Console theme / role colors.
CONSOLE_BG: RGB = (24, 24, 28)
CMD_COLOR: RGB = (120, 200, 255)
STATUS_COLOR: RGB = (140, 140, 140)
ERROR_COLOR: RGB = (235, 90, 90)
EVENT_TAG_COLOR: RGB = (120, 215, 140)
EVENT_KEY_COLOR: RGB = (150, 160, 200)

# Colors for connection status lines, keyed by status name.
STATUS_COLORS: dict[str, RGB] = {
    "connecting": (235, 215, 70),    # yellow
    "connected": (70, 215, 90),      # green
    "disconnected": (150, 150, 150),  # grey
    "error": ERROR_COLOR,
}

# Leading indicator glyph per status. Use only characters present in common
# monospace fonts (•, ×): geometric circles like ● ○ are absent from Consolas
# and get font-substituted, which inflates the line height. State is conveyed by
# color instead of glyph shape.
STATUS_GLYPHS: dict[str, str] = {
    "connecting": "•",
    "connected": "•",
    "disconnected": "•",
    "error": "×",
}

# Cap per-server scrollback to keep memory bounded.
MAX_LINES = 5000

# The server echoes every rcon command as "zmq RCON command from <id>: <cmd>".
# Matched anywhere in the line so a stray leading space or merged fragment from
# the frame stream still gets recognized and hidden.
_RCON_ECHO_RE = re.compile(r"zmq RCON command from ")

# Response to querying a single cvar:  "sv_hostname" is:"QL4^7" default:""
_CVAR_RESPONSE_RE = re.compile(r'^"(?P<name>\w+)" is:"(?P<val>.*?)(?:\^7)?"')

INFO_COLOR: RGB = (150, 200, 235)

# Cvars queried silently on connect to build the summary line.
_CONNECT_QUERY = ("players", "sv_hostname", "mapname", "sv_maxclients")


# Non-printable control bytes Quake embeds around chat/names (shown as boxes).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean_output_line(text: str) -> str:
    """Strip QL ``print "..."`` wrappers, stray quotes and control bytes.

    Server output arrives as ``print "payload\\n"`` where the newline is real and
    the closing quote ends up glued to the next ``print "``. This unwraps both
    leading wrappers and the ``prefix: print "..."`` form, drops the dangling
    quote, and removes non-printable control characters that render as boxes.
    """
    s = text.lstrip('"')
    if s.startswith('print "'):
        s = s[len('print "') :]
    s = s.replace(': print "', ': ')
    s = s.rstrip('"')
    return _CONTROL_RE.sub("", s)


class _ServerState:
    """Per-server runtime state held by the frame."""

    def __init__(self) -> None:
        self.connection: ServerConnection | None = None
        self.console: list[Line] = []
        self.events: list[Line] = []
        self.rcon_status: str = "disconnected"
        self.stats_status: str = "disconnected"
        self.history: list[str] = []
        self.roster: Roster = Roster()
        # While True, swallow the silent connect-time queries (players + a few
        # cvars) instead of printing them; used to build the summary line.
        self.seeding_roster: bool = False
        self.connect_info: dict[str, str] = {}
        self.summary_shown: bool = False


class MainFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="Quake Live RCON Console")
        self.SetClientSize(self.FromDIP(wx.Size(1200, 800)))
        self.SetMinSize(self.FromDIP(wx.Size(640, 420)))
        self.Centre()

        self.SetIcon(load_app_icon())
        self.config: AppConfig = load_config()
        set_language(self.config.settings.language)
        self.SetTitle(self._window_title())
        # State keyed by the id() of each ServerConfig object.
        self._state: dict[int, _ServerState] = {}
        self._history_pos: int = 0
        self._console_font: wx.Font | None = None

        self._build_menu()
        self._build_ui()
        self._apply_view_settings()
        self._refresh_server_list()
        if self.config.servers:
            self.server_list.SetSelection(0)
            self._on_select_server()

        self.Bind(wx.EVT_CLOSE, self._on_close)

    # -- UI construction --------------------------------------------------

    def _build_menu(self) -> None:
        self._menubar = wx.MenuBar()
        settings = wx.Menu()
        self._mi_settings = settings.Append(wx.ID_PREFERENCES, t("menu_open_settings"))
        self.Bind(wx.EVT_MENU, self._on_open_settings, self._mi_settings)
        self._menubar.Append(settings, t("menu_settings"))
        self.SetMenuBar(self._menubar)

    def _on_open_settings(self, _event: wx.Event) -> None:
        dialog = SettingsDialog(self, self.config.settings)
        if dialog.ShowModal() == wx.ID_OK:
            new = dialog.get_settings()
            language_changed = new.language != self.config.settings.language
            self.config.settings = new
            self._persist()
            self._apply_view_settings()
            if language_changed:
                set_language(new.language)
                self._retranslate()
        dialog.Destroy()

    def _window_title(self) -> str:
        return f"{t('app_title')} v{__version__}"

    def _retranslate(self) -> None:
        """Update all static UI labels to the current language (no restart)."""
        self.SetTitle(self._window_title())
        self._menubar.SetMenuLabel(0, t("menu_settings"))
        self._mi_settings.SetItemLabel(t("menu_open_settings"))
        self.btn_add.SetLabel(t("btn_add"))
        self.btn_edit.SetLabel(t("btn_edit"))
        self.btn_remove.SetLabel(t("btn_remove"))
        self.btn_connect.SetLabel(t("btn_connect"))
        self.btn_disconnect.SetLabel(t("btn_disconnect"))
        self.btn_send.SetLabel(t("btn_send"))
        self.btn_clear.SetLabel(t("btn_clear"))
        self.notebook.SetPageText(0, t("tab_console"))
        self.notebook.SetPageText(1, t("tab_events"))
        server = self._selected_server()
        if server is not None:
            self._update_status_bar(server)
        else:
            self._set_status(t("status_ready"), 0)
            self._set_status("", 1)

    def _make_console_font(self) -> wx.Font:
        s = self.config.settings
        info = wx.FontInfo(s.console_font_size).Family(wx.FONTFAMILY_TELETYPE)
        if s.console_font_face:
            info = info.FaceName(s.console_font_face)
        return wx.Font(info)

    def _apply_view_settings(self) -> None:
        """Apply font/background settings to the console and events views."""
        self._console_font = self._make_console_font()
        bg = wx.Colour(*colors.parse_hex(self.config.settings.console_bg))
        for ctrl in (self.console_ctrl, self.events_ctrl, self.command_input):
            ctrl.SetFont(self._console_font)
            ctrl.SetBackgroundColour(bg)
        # Re-render the current server so existing lines pick up the new look.
        self._on_select_server()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.HORIZONTAL)

        # Left: server list + buttons.
        left = wx.BoxSizer(wx.VERTICAL)
        self.server_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.server_list.SetMinSize(self.FromDIP(wx.Size(240, -1)))
        self.server_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select_server())
        self.server_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_list_dclick)
        left.Add(self.server_list, 1, wx.EXPAND | wx.BOTTOM, 6)

        btns = wx.GridSizer(rows=3, cols=2, vgap=4, hgap=4)
        self.btn_add = wx.Button(panel, label=t("btn_add"))
        self.btn_edit = wx.Button(panel, label=t("btn_edit"))
        self.btn_remove = wx.Button(panel, label=t("btn_remove"))
        self.btn_connect = wx.Button(panel, label=t("btn_connect"))
        self.btn_disconnect = wx.Button(panel, label=t("btn_disconnect"))
        btns.Add(self.btn_add, 0, wx.EXPAND)
        btns.Add(self.btn_edit, 0, wx.EXPAND)
        btns.Add(self.btn_remove, 0, wx.EXPAND)
        btns.Add((0, 0))
        btns.Add(self.btn_connect, 0, wx.EXPAND)
        btns.Add(self.btn_disconnect, 0, wx.EXPAND)
        left.Add(btns, 0, wx.EXPAND)

        self.btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        self.btn_edit.Bind(wx.EVT_BUTTON, self._on_edit)
        self.btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self.btn_connect.Bind(wx.EVT_BUTTON, self._on_connect)
        self.btn_disconnect.Bind(wx.EVT_BUTTON, self._on_disconnect)

        root.Add(left, 0, wx.EXPAND | wx.ALL, 8)

        # Right: notebook with console + events.
        notebook = wx.Notebook(panel)
        self.notebook = notebook
        # Use the configured console font from the start so the first lines
        # render at the right size (no transient default-font flash).
        self._console_font = self._make_console_font()
        mono = self._console_font
        bg = wx.Colour(*colors.parse_hex(self.config.settings.console_bg))
        fg = wx.Colour(*colors.WHITE)

        console_page = wx.Panel(notebook)
        cp_sizer = wx.BoxSizer(wx.VERTICAL)
        self.console_ctrl = wx.TextCtrl(
            console_page, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self.console_ctrl.SetFont(mono)
        self.console_ctrl.SetBackgroundColour(bg)
        self.console_ctrl.SetForegroundColour(fg)
        cp_sizer.Add(self.console_ctrl, 1, wx.EXPAND | wx.BOTTOM, 4)

        input_row = wx.BoxSizer(wx.HORIZONTAL)
        self.command_input = wx.TextCtrl(console_page, style=wx.TE_PROCESS_ENTER)
        self.command_input.SetFont(mono)
        self.command_input.SetBackgroundColour(bg)
        self.command_input.SetForegroundColour(fg)
        self.command_input.Bind(wx.EVT_TEXT_ENTER, self._on_send)
        self.command_input.Bind(wx.EVT_KEY_DOWN, self._on_input_key)
        self._autocomplete = AutoComplete(self.command_input, roster_provider=self._current_roster)
        self.btn_send = wx.Button(console_page, label=t("btn_send"))
        self.btn_send.Bind(wx.EVT_BUTTON, self._on_send)
        self.btn_clear = wx.Button(console_page, label=t("btn_clear"))
        self.btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_console)
        input_row.Add(self.command_input, 1, wx.EXPAND | wx.RIGHT, 4)
        input_row.Add(self.btn_send, 0, wx.RIGHT, 4)
        input_row.Add(self.btn_clear, 0)
        cp_sizer.Add(input_row, 0, wx.EXPAND)
        console_page.SetSizer(cp_sizer)
        notebook.AddPage(console_page, t("tab_console"))

        events_page = wx.Panel(notebook)
        ep_sizer = wx.BoxSizer(wx.VERTICAL)
        self.events_ctrl = wx.TextCtrl(
            events_page, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self.events_ctrl.SetFont(mono)
        self.events_ctrl.SetBackgroundColour(bg)
        self.events_ctrl.SetForegroundColour(fg)
        ep_sizer.Add(self.events_ctrl, 1, wx.EXPAND)
        events_page.SetSizer(ep_sizer)
        notebook.AddPage(events_page, t("tab_events"))

        root.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)

        self.CreateStatusBar(2)
        self._set_status(t("status_ready"))

    # -- server list / config management ----------------------------------

    def _state_for(self, server: ServerConfig) -> _ServerState:
        return self._state.setdefault(id(server), _ServerState())

    def _current_roster(self) -> list[Player]:
        """Players of the currently selected server (for autocomplete)."""
        server = self._selected_server()
        if server is None:
            return []
        return self._state_for(server).roster.list()

    def _selected_index(self) -> int:
        return self.server_list.GetSelection()

    def _selected_server(self) -> ServerConfig | None:
        idx = self._selected_index()
        if idx == wx.NOT_FOUND:
            return None
        return self.config.servers[idx]

    def _refresh_server_list(self) -> None:
        selection = self._selected_index()
        self.server_list.Set([self._server_label(s) for s in self.config.servers])
        if 0 <= selection < self.server_list.GetCount():
            self.server_list.SetSelection(selection)

    def _server_label(self, server: ServerConfig) -> str:
        state = self._state.get(id(server))
        if state and state.connection:
            marker = "●" if state.rcon_status == "connected" else "○"
        else:
            marker = " "
        return f"{marker} {server.name}  ({server.host}:{server.rcon_port})"

    def _persist(self) -> None:
        save_config(self.config)

    # -- button handlers --------------------------------------------------

    def _on_add(self, _event: wx.Event) -> None:
        dialog = ServerDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            self.config.servers.append(dialog.get_server())
            self._persist()
            self._refresh_server_list()
            self.server_list.SetSelection(len(self.config.servers) - 1)
            self._on_select_server()
        dialog.Destroy()

    def _on_edit(self, _event: wx.Event) -> None:
        server = self._selected_server()
        if server is None:
            return
        state = self._state.get(id(server))
        if state and state.connection:
            wx.MessageBox(
                t("msg_disconnect_before_edit"), t("title_in_use"), wx.OK | wx.ICON_INFORMATION
            )
            return
        dialog = ServerDialog(self, server)
        if dialog.ShowModal() == wx.ID_OK:
            idx = self._selected_index()
            updated = dialog.get_server()
            self._state.pop(id(server), None)
            self.config.servers[idx] = updated
            self._persist()
            self._refresh_server_list()
            self._on_select_server()
        dialog.Destroy()

    def _on_remove(self, _event: wx.Event) -> None:
        server = self._selected_server()
        if server is None:
            return
        if (
            wx.MessageBox(
                t("confirm_remove", name=server.name),
                t("title_confirm"),
                wx.YES_NO | wx.ICON_QUESTION,
            )
            != wx.YES
        ):
            return
        state = self._state.pop(id(server), None)
        if state and state.connection:
            state.connection.disconnect()
        self.config.servers.pop(self._selected_index())
        self._persist()
        self._refresh_server_list()
        self._on_select_server()

    def _on_list_dclick(self, _event: wx.Event) -> None:
        """Double-click a server to connect (no-op if already connected)."""
        server = self._selected_server()
        if server is None:
            return
        if self._state.get(id(server), _ServerState()).connection:
            self.command_input.SetFocus()
            return
        self._on_connect(None)

    def _on_connect(self, _event: wx.Event) -> None:
        server = self._selected_server()
        if server is None:
            return
        state = self._state_for(server)
        if state.connection:
            return
        state.connection = ServerConnection(
            server,
            on_rcon_message=lambda text, s=server: self._handle_rcon_message(s, text),
            on_stats_event=lambda event, s=server: self._handle_stats_event(s, event),
            on_status=lambda ch, st, detail, s=server: self._handle_status(s, ch, st, detail),
        )
        state.connection.connect()
        self._status_line(
            server, "connecting", t("log_connecting_to", endpoint=server.rcon_endpoint)
        )
        self._update_buttons()

    def _on_disconnect(self, _event: wx.Event) -> None:
        server = self._selected_server()
        if server is None:
            return
        state = self._state.get(id(server))
        if not state or not state.connection:
            return
        state.connection.disconnect()
        state.connection = None
        state.rcon_status = "disconnected"
        state.stats_status = "disconnected"
        state.seeding_roster = False
        self._status_line(server, "disconnected", t("log_disconnected"))
        self._refresh_server_list()
        self._update_buttons()

    def _on_send(self, _event: wx.Event) -> None:
        server = self._selected_server()
        if server is None:
            return
        state = self._state.get(id(server))
        command = self.command_input.GetValue().strip()
        if not command:
            return
        if not state or not state.connection:
            wx.MessageBox(t("msg_not_connected"), t("title_send"), wx.OK | wx.ICON_INFORMATION)
            return
        state.connection.send(command)
        state.history.append(command)
        self._history_pos = len(state.history)
        self._console(server, [(CMD_COLOR, f"›  {command}")])
        self.command_input.Clear()

    def _on_clear_console(self, _event: wx.Event) -> None:
        server = self._selected_server()
        if server is None:
            return
        self._state_for(server).console.clear()
        self.console_ctrl.Clear()

    # -- command history (Up/Down in the input box) -----------------------

    def _on_input_key(self, event: wx.KeyEvent) -> None:
        # The autocomplete popup gets first dibs on navigation keys.
        if self._autocomplete.handle_key_down(event):
            return
        server = self._selected_server()
        state = self._state.get(id(server)) if server else None
        if not state or not state.history:
            event.Skip()
            return
        code = event.GetKeyCode()
        if code == wx.WXK_UP:
            self._history_pos = max(0, self._history_pos - 1)
            self.command_input.SetValue(state.history[self._history_pos])
            self.command_input.SetInsertionPointEnd()
        elif code == wx.WXK_DOWN:
            self._history_pos = min(len(state.history), self._history_pos + 1)
            if self._history_pos == len(state.history):
                self.command_input.Clear()
            else:
                self.command_input.SetValue(state.history[self._history_pos])
                self.command_input.SetInsertionPointEnd()
        else:
            event.Skip()

    # -- selection / view sync --------------------------------------------

    def _on_select_server(self) -> None:
        server = self._selected_server()
        if server is None:
            self.console_ctrl.SetValue("")
            self.events_ctrl.SetValue("")
            self._history_pos = 0
            self._update_buttons()
            return
        state = self._state_for(server)
        self._render_all(self.console_ctrl, state.console)
        self._render_all(self.events_ctrl, state.events)
        self._history_pos = len(state.history)
        self._update_buttons()
        self._update_status_bar(server)

    def _update_buttons(self) -> None:
        server = self._selected_server()
        connected = bool(server and self._state.get(id(server), _ServerState()).connection)
        has_server = server is not None
        self.btn_edit.Enable(has_server and not connected)
        self.btn_remove.Enable(has_server)
        self.btn_connect.Enable(has_server and not connected)
        self.btn_disconnect.Enable(connected)
        self.btn_send.Enable(connected)
        self.command_input.Enable(connected)
        self.btn_clear.Enable(has_server)

    # -- callbacks from the connection (already on the GUI thread) --------

    def _handle_rcon_message(self, server: ServerConfig, text: str) -> None:
        # Server output may carry several lines and Quake color codes; render
        # each line as its own colored entry.
        state = self._state_for(server)
        hide_echo = self.config.settings.hide_rcon_echo
        for line in text.rstrip("\n").split("\n"):
            player = parse_players_line(line)
            if player is not None:
                state.roster.upsert(player)
            is_echo = bool(_RCON_ECHO_RE.search(line))
            # During the connect window, swallow our silent queries' responses
            # (cvar replies + echo + player rows + blanks) and build the summary.
            if state.seeding_roster:
                cvar = _CVAR_RESPONSE_RE.match(line)
                if cvar is not None:
                    state.connect_info[cvar.group("name")] = colors.strip_colors(
                        cvar.group("val")
                    ).strip()
                    self._maybe_show_summary(server)
                    continue
                if player is not None or is_echo or not line.strip(' "'):
                    continue
            if hide_echo and is_echo:
                continue
            if self.config.settings.clean_output:
                line = _clean_output_line(line)
                if not line.strip():
                    continue  # nothing left after unwrapping (e.g. a lone quote)
            self._console(server, colors.parse_segments(line))

    def _maybe_show_summary(self, server: ServerConfig) -> None:
        state = self._state_for(server)
        if {"sv_hostname", "mapname", "sv_maxclients"} <= state.connect_info.keys():
            self._show_connect_summary(server)

    def _show_connect_summary(self, server: ServerConfig) -> None:
        state = self._state_for(server)
        if state.summary_shown or state.connection is None:
            return
        state.summary_shown = True
        state.seeding_roster = False
        info = state.connect_info
        name = info.get("sv_hostname") or server.name
        current_map = info.get("mapname") or "?"
        count = len(state.roster.list())
        maxclients = info.get("sv_maxclients")
        players = f"{count}/{maxclients}" if maxclients else str(count)
        self._console(
            server,
            [(INFO_COLOR, t("log_server_summary", name=name, map=current_map, players=players))],
        )

    def _handle_stats_event(self, server: ServerConfig, event: dict) -> None:
        etype = event.get("TYPE", "EVENT")
        data = event.get("DATA", event)
        self._update_roster_from_event(server, etype, data)
        runs: Line = [(EVENT_TAG_COLOR, f"{etype:<18}")]
        runs.extend(self._format_event_data(data))
        self._events(server, runs)

    def _update_roster_from_event(self, server: ServerConfig, etype: str, data: object) -> None:
        if not isinstance(data, dict):
            return
        roster = self._state_for(server).roster
        name = colors.strip_colors(str(data.get("NAME", ""))).strip()
        steam_id = str(data.get("STEAM_ID", ""))
        if etype == "PLAYER_DISCONNECT":
            roster.remove(steam_id=steam_id, name=name)
        elif etype in ("PLAYER_CONNECT", "PLAYER_SWITCHTEAM"):
            if name or steam_id:
                roster.upsert(Player(name=name, steam_id=steam_id, team=str(data.get("TEAM", ""))))

    def _format_event_data(self, data: object) -> Line:
        """Render a stats event payload as compact ``key=value`` colored runs."""
        if isinstance(data, dict):
            runs: Line = []
            for i, (key, value) in enumerate(data.items()):
                if i:
                    runs.append((colors.WHITE, "  "))
                runs.append((EVENT_KEY_COLOR, f"{key}="))
                runs.append((colors.WHITE, colors.strip_colors(str(value))))
            return runs or [(colors.WHITE, "{}")]
        try:
            return [(colors.WHITE, json.dumps(data, ensure_ascii=False))]
        except (TypeError, ValueError):
            return [(colors.WHITE, str(data))]

    def _handle_status(
        self, server: ServerConfig, channel: str, status: str, detail: str
    ) -> None:
        state = self._state_for(server)
        if channel == "rcon":
            state.rcon_status = status
            if status == "connected" and state.connection:
                # Silently query roster + server info to build a summary line;
                # these responses are swallowed (not shown in the console).
                state.seeding_roster = True
                state.connect_info = {}
                state.summary_shown = False
                for cmd in _CONNECT_QUERY:
                    state.connection.send(cmd)
                # Fallback in case some query gets no response.
                wx.CallLater(2000, self._show_connect_summary, server)
            elif status == "disconnected":
                state.roster.clear()
                state.seeding_roster = False
        else:
            state.stats_status = status
        if status == "error":
            self._status_line(server, "error", self._error_message(channel, detail))
            if channel == "rcon" and detail in (ERR_AUTH_FAILED, ERR_MAX_ATTEMPTS):
                # Terminal RCON failure: tear down so the user can retry Connect.
                self._teardown_connection(server)
                return
        else:
            self._status_line(server, status, f"{channel}: {self._state_label(status)}")
        self._refresh_server_list()
        if server is self._selected_server():
            self._update_status_bar(server)
            self._update_buttons()

    # -- output helpers ---------------------------------------------------

    def _console(self, server: ServerConfig, runs: Line) -> None:
        self._emit(server, self._state_for(server).console, self.console_ctrl, runs)

    def _status_line(self, server: ServerConfig, status: str, text: str) -> None:
        """Emit a status line: a colored leading glyph followed by the text."""
        glyph = STATUS_GLYPHS.get(status, "•")
        color = STATUS_COLORS.get(status, STATUS_COLOR)
        self._console(server, [(color, f"{glyph}  {text}")])

    def _events(self, server: ServerConfig, runs: Line) -> None:
        self._emit(server, self._state_for(server).events, self.events_ctrl, runs)

    def _emit(
        self, server: ServerConfig, store: list[Line], ctrl: wx.TextCtrl, runs: Line
    ) -> None:
        store.append(runs)
        if len(store) > MAX_LINES:
            del store[: len(store) - MAX_LINES]
        if server is self._selected_server():
            self._render_line(ctrl, runs)

    def _render_line(self, ctrl: wx.TextCtrl, runs: Line) -> None:
        for rgb, text in runs:
            attr = wx.TextAttr(wx.Colour(*rgb))
            # Pin the font per-segment so the very first lines render at the
            # configured size (the control's font may not be applied yet).
            if self._console_font is not None:
                attr.SetFont(self._console_font)
            ctrl.SetDefaultStyle(attr)
            ctrl.AppendText(text)
        ctrl.AppendText("\n")

    def _render_all(self, ctrl: wx.TextCtrl, lines: list[Line]) -> None:
        ctrl.Clear()
        for runs in lines:
            self._render_line(ctrl, runs)
        ctrl.SetInsertionPointEnd()

    def _set_status(self, text: str, field: int = 0) -> None:
        self.SetStatusText(text, field)

    def _state_label(self, status: str) -> str:
        """Localized word for a connection state, falling back to the raw value."""
        key = f"state_{status}"
        label = t(key)
        return status if label == key else label

    def _teardown_connection(self, server: ServerConfig) -> None:
        """Fully stop a server's connection (used after a terminal error)."""
        state = self._state_for(server)
        if state.connection:
            state.connection.disconnect()
            state.connection = None
        state.rcon_status = "disconnected"
        state.stats_status = "disconnected"
        state.seeding_roster = False
        self._refresh_server_list()
        if server is self._selected_server():
            self._update_buttons()
            self._update_status_bar(server)

    def _error_message(self, channel: str, detail: str) -> str:
        """Localized text for a connection error (known codes) or a generic form."""
        if detail == ERR_AUTH_FAILED:
            return t("err_auth_failed")
        if detail == ERR_MAX_ATTEMPTS:
            return t("err_max_attempts", n=MAX_ATTEMPTS)
        return f"{channel} {self._state_label('error')}: {detail}"

    def _update_status_bar(self, server: ServerConfig) -> None:
        state = self._state_for(server)
        self._set_status(t("status_rcon", status=self._state_label(state.rcon_status)), 0)
        stats = self._state_label(state.stats_status) if server.stats_enabled else t("status_off")
        self._set_status(t("status_stats", status=stats), 1)

    # -- shutdown ---------------------------------------------------------

    def _on_close(self, event: wx.CloseEvent) -> None:
        for state in self._state.values():
            if state.connection:
                state.connection.disconnect()
        event.Skip()
