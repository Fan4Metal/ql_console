"""Main application window.

Layout: a server list on the left; on the right a notebook with an RCON
console (output + command input) and a live-events log. Each server keeps its
own output/event buffers so switching between servers preserves history.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import wx

from .. import __version__, colors
from ..colors import RGB
from ..commands import set_hint_language
from ..config import AppConfig, ServerConfig, load_config, save_config
from ..i18n import set_language, t
from ..connection import ServerConnection
from ..rcon_client import ERR_AUTH_FAILED, ERR_MAX_ATTEMPTS, MAX_ATTEMPTS
from ..roster import Player, Roster, parse_players_line
from .about_dialog import AboutDialog
from .appicon import load_app_icon
from .autocomplete import AutoComplete
from .console_view import ConsoleView
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

# Trailing whitespace and stray closing quote(s) left after unwrapping.
_TRAILING_JUNK_RE = re.compile(r'[\s"]+$')


def _clean_output_line(text: str) -> str:
    """Strip QL ``print "..."`` wrappers, stray quotes and control bytes.

    Server output arrives as ``print "payload\\n"`` where the newline is real and
    the closing quote ends up glued to the next ``print "``. This unwraps both
    leading wrappers and the ``prefix: print "..."`` form, drops the dangling
    quote, and removes non-printable control characters that render as boxes.

    Some lines (e.g. ``broadcast``) embed *literal* escape sequences — a real
    backslash-n the server never interpreted — followed by the stray quote, so
    they render as ``...message\\n"``. Those literal escapes are dropped too.
    """
    s = text.lstrip('"')
    if s.startswith('print "'):
        s = s[len('print "') :]
    s = s.replace(': print "', ': ')
    s = s.replace("\\n", "").replace("\\r", "")  # drop literal escape sequences
    s = _TRAILING_JUNK_RE.sub("", s)  # trailing whitespace + stray quote(s)
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
        set_hint_language(self.config.settings.hint_language)
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

        file_menu = wx.Menu()
        self._mi_save_servers = file_menu.Append(wx.ID_ANY, t("menu_save_servers"))
        self._mi_load_servers = file_menu.Append(wx.ID_ANY, t("menu_load_servers"))
        file_menu.AppendSeparator()
        self._mi_clear_servers = file_menu.Append(wx.ID_ANY, t("menu_clear_servers"))
        file_menu.AppendSeparator()
        self._mi_settings = file_menu.Append(wx.ID_PREFERENCES, t("menu_open_settings"))
        file_menu.AppendSeparator()
        self._mi_exit = file_menu.Append(wx.ID_EXIT, t("menu_exit"))
        self.Bind(wx.EVT_MENU, self._on_save_servers, self._mi_save_servers)
        self.Bind(wx.EVT_MENU, self._on_load_servers, self._mi_load_servers)
        self.Bind(wx.EVT_MENU, self._on_clear_servers, self._mi_clear_servers)
        self.Bind(wx.EVT_MENU, self._on_open_settings, self._mi_settings)
        self.Bind(wx.EVT_MENU, self._on_exit, self._mi_exit)
        self._menubar.Append(file_menu, t("menu_file"))

        help_menu = wx.Menu()
        self._mi_about = help_menu.Append(wx.ID_ABOUT, t("menu_about"))
        self.Bind(wx.EVT_MENU, self._on_about, self._mi_about)
        self._menubar.Append(help_menu, t("menu_help"))

        self.SetMenuBar(self._menubar)

        # Suppress wx's default behavior of writing each menu item's help string
        # (which is empty here) into the status bar on hover — that would blank
        # out our RCON/stats status fields. Handling the event without Skip()
        # leaves the status bar untouched.
        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self._on_menu_highlight)

    def _on_menu_highlight(self, _event: wx.MenuEvent) -> None:
        # Intentionally do nothing (and don't Skip) so the status bar is not overwritten.
        pass

    def _on_about(self, _event: wx.Event) -> None:
        dialog = AboutDialog(self)
        dialog.ShowModal()
        dialog.Destroy()

    def _on_open_settings(self, _event: wx.Event) -> None:
        dialog = SettingsDialog(self, self.config.settings)
        if dialog.ShowModal() == wx.ID_OK:
            new = dialog.get_settings()
            language_changed = new.language != self.config.settings.language
            self.config.settings = new
            self._persist()
            set_hint_language(new.hint_language)
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
        self._menubar.SetMenuLabel(0, t("menu_file"))
        self._mi_save_servers.SetItemLabel(t("menu_save_servers"))
        self._mi_load_servers.SetItemLabel(t("menu_load_servers"))
        self._mi_clear_servers.SetItemLabel(t("menu_clear_servers"))
        self._mi_settings.SetItemLabel(t("menu_open_settings"))
        self._mi_exit.SetItemLabel(t("menu_exit"))
        self._menubar.SetMenuLabel(1, t("menu_help"))
        self._mi_about.SetItemLabel(t("menu_about"))
        self.btn_add.SetLabel(t("btn_add"))
        self.btn_edit.SetLabel(t("btn_edit"))
        self.btn_remove.SetLabel(t("btn_remove"))
        self.btn_connect.SetLabel(t("btn_connect"))
        self.btn_disconnect.SetLabel(t("btn_disconnect"))
        self.btn_send.SetLabel(t("btn_send"))
        self.btn_clear.SetToolTip(t("btn_clear"))
        self.notebook.SetPageText(0, t("tab_console"))
        if self.notebook.GetPageCount() > 1:
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
        self.console_ctrl.configure(self._console_font, bg)
        self.events_ctrl.configure(self._console_font, bg)
        self.command_input.SetFont(self._console_font)
        self.command_input.SetBackgroundColour(bg)
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
        self.server_list.Bind(wx.EVT_CONTEXT_MENU, self._on_list_context_menu)
        # Drag-and-drop reordering of the server list.
        self._drag_index = wx.NOT_FOUND
        self.server_list.Bind(wx.EVT_LEFT_DOWN, self._on_list_left_down)
        self.server_list.Bind(wx.EVT_MOTION, self._on_list_motion)
        self.server_list.Bind(wx.EVT_LEFT_UP, self._on_list_left_up)
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
        self.console_ctrl = ConsoleView(console_page)
        self.console_ctrl.configure(mono, bg)
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
        # Clear is a compact, square, icon-only button (label kept as tooltip).
        clear_bmp = wx.ArtProvider.GetBitmap(
            wx.ART_DELETE, wx.ART_BUTTON, wx.Size(16, 16)
        )
        self.btn_clear = wx.BitmapButton(console_page, bitmap=clear_bmp)
        self.btn_clear.SetToolTip(t("btn_clear"))
        self.btn_clear.Bind(wx.EVT_BUTTON, self._on_clear_console)
        # Square it to the Send button's height so it lines up in the row.
        side = self.btn_send.GetBestSize().height
        self.btn_clear.SetMinSize(wx.Size(side, side))
        input_row.Add(self.command_input, 1, wx.EXPAND | wx.RIGHT, 4)
        input_row.Add(self.btn_send, 0, wx.RIGHT, 4)
        input_row.Add(self.btn_clear, 0)
        cp_sizer.Add(input_row, 0, wx.EXPAND)
        console_page.SetSizer(cp_sizer)
        notebook.AddPage(console_page, t("tab_console"))

        self.events_page = wx.Panel(notebook)
        ep_sizer = wx.BoxSizer(wx.VERTICAL)
        self.events_ctrl = ConsoleView(self.events_page)
        self.events_ctrl.configure(mono, bg)
        ep_sizer.Add(self.events_ctrl, 1, wx.EXPAND)
        self.events_page.SetSizer(ep_sizer)
        notebook.AddPage(self.events_page, t("tab_events"))

        root.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)

        # Three fields: RCON status, stats status, and a filler that eats the
        # remaining width so the first two stay packed on the left edge.
        self.CreateStatusBar(3)
        self.GetStatusBar().SetStatusWidths([self.FromDIP(200), self.FromDIP(180), -1])
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

    def _disconnect_all(self) -> None:
        """Tear down every live connection (used before clearing/replacing the list)."""
        for state in self._state.values():
            if state.connection:
                state.connection.disconnect()

    # -- File menu: save / load / clear server list -----------------------

    def _on_save_servers(self, _event: wx.Event) -> None:
        """Export the server list and app settings to a user-chosen JSON file."""
        with wx.FileDialog(
            self,
            t("dlg_save_servers"),
            defaultFile="servers.json",
            wildcard="JSON (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        try:
            save_config(self.config, path)
        except OSError as exc:
            wx.MessageBox(
                t("msg_save_failed", error=exc), t("title_error"), wx.OK | wx.ICON_ERROR
            )

    def _on_load_servers(self, _event: wx.Event) -> None:
        """Replace the current server list with one imported from a JSON file."""
        with wx.FileDialog(
            self,
            t("dlg_load_servers"),
            wildcard="JSON (*.json)|*.json",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            loaded = AppConfig.from_dict(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            wx.MessageBox(
                t("msg_load_failed", error=exc), t("title_error"), wx.OK | wx.ICON_ERROR
            )
            return
        self._disconnect_all()
        self._state.clear()
        self.config.servers = loaded.servers
        self._persist()
        self._refresh_server_list()
        if self.config.servers:
            self.server_list.SetSelection(0)
        self._on_select_server()

    def _on_clear_servers(self, _event: wx.Event) -> None:
        """Remove every server from the list after confirmation."""
        if not self.config.servers:
            return
        if (
            wx.MessageBox(
                t("confirm_clear_servers"),
                t("title_confirm"),
                wx.YES_NO | wx.ICON_QUESTION,
            )
            != wx.YES
        ):
            return
        self._disconnect_all()
        self._state.clear()
        self.config.servers.clear()
        self._persist()
        self._refresh_server_list()
        self._on_select_server()

    def _on_exit(self, _event: wx.Event) -> None:
        """Close the window (triggers the normal shutdown via EVT_CLOSE)."""
        self.Close()

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

    # -- drag-and-drop reordering -----------------------------------------

    def _on_list_left_down(self, event: wx.MouseEvent) -> None:
        event.Skip()  # let the click select the row as usual
        self._drag_index = self.server_list.HitTest(event.GetPosition())

    def _on_list_motion(self, event: wx.MouseEvent) -> None:
        event.Skip()
        dragging = event.Dragging() and event.LeftIsDown() and self._drag_index != wx.NOT_FOUND
        self.server_list.SetCursor(
            wx.Cursor(wx.CURSOR_HAND if dragging else wx.CURSOR_DEFAULT)
        )

    def _on_list_left_up(self, event: wx.MouseEvent) -> None:
        event.Skip()
        self.server_list.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))
        src = self._drag_index
        self._drag_index = wx.NOT_FOUND
        if src == wx.NOT_FOUND:
            return
        dst = self.server_list.HitTest(event.GetPosition())
        if dst == wx.NOT_FOUND:  # dropped past the last row -> move to the end
            dst = self.server_list.GetCount() - 1
        if dst == src or dst == wx.NOT_FOUND:
            return
        self._move_server(src, dst)

    def _move_server(self, src: int, dst: int) -> None:
        """Reorder the server list, keeping the moved server selected.

        The same ServerConfig object is moved, so per-server state (keyed by
        ``id(server)``) and any live connection are preserved.
        """
        servers = self.config.servers
        servers.insert(dst, servers.pop(src))
        self._persist()
        self._refresh_server_list()
        self.server_list.SetSelection(dst)
        self._on_select_server()

    def _on_list_context_menu(self, event: wx.ContextMenuEvent) -> None:
        """Right-click a server to connect/disconnect, edit or remove it."""
        # Select the row under the cursor first, so the action targets it.
        pos = event.GetPosition()
        if pos != wx.DefaultPosition:  # keyboard menu key reports DefaultPosition
            idx = self.server_list.HitTest(self.server_list.ScreenToClient(pos))
            if idx != wx.NOT_FOUND:
                self.server_list.SetSelection(idx)
                self._on_select_server()
        server = self._selected_server()
        if server is None:
            return
        connected = bool(self._state.get(id(server), _ServerState()).connection)

        menu = wx.Menu()
        if connected:
            mi_toggle = menu.Append(wx.ID_ANY, t("btn_disconnect"))
            self.Bind(wx.EVT_MENU, self._on_disconnect, mi_toggle)
        else:
            mi_toggle = menu.Append(wx.ID_ANY, t("btn_connect"))
            self.Bind(wx.EVT_MENU, self._on_connect, mi_toggle)
        mi_steam = menu.Append(wx.ID_ANY, t("menu_launch_steam"))
        self.Bind(wx.EVT_MENU, self._on_launch_steam, mi_steam)
        menu.AppendSeparator()
        mi_edit = menu.Append(wx.ID_ANY, t("btn_edit"))
        mi_edit.Enable(not connected)
        self.Bind(wx.EVT_MENU, self._on_edit, mi_edit)
        mi_remove = menu.Append(wx.ID_ANY, t("btn_remove"))
        self.Bind(wx.EVT_MENU, self._on_remove, mi_remove)

        self.server_list.PopupMenu(menu)
        menu.Destroy()

    def _on_list_dclick(self, _event: wx.Event) -> None:
        """Double-click a server to connect (no-op if already connected)."""
        server = self._selected_server()
        if server is None:
            return
        if self._state.get(id(server), _ServerState()).connection:
            self.command_input.SetFocus()
            return
        self._on_connect(None)

    def _on_launch_steam(self, _event: wx.Event) -> None:
        """Hand the server's steam://connect/ URL to Steam via the OS handler."""
        server = self._selected_server()
        if server is None:
            return
        wx.LaunchDefaultBrowser(server.steam_connect_url)

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
        self.console_ctrl.clear()

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
            self._update_events_tab(None)
            self.console_ctrl.clear()
            self.events_ctrl.clear()
            self._history_pos = 0
            self._update_buttons()
            return
        state = self._state_for(server)
        self._update_events_tab(server)
        self.console_ctrl.render_all(state.console)
        if server.stats_enabled:
            self.events_ctrl.render_all(state.events)
        self._history_pos = len(state.history)
        self._update_buttons()
        self._update_status_bar(server)

    def _update_events_tab(self, server: ServerConfig | None) -> None:
        """Show the stats/events tab only when the server has stats enabled."""
        show = server is not None and server.stats_enabled
        has_tab = self.notebook.GetPageCount() > 1
        if show and not has_tab:
            self.notebook.AddPage(self.events_page, t("tab_events"))
        elif not show and has_tab:
            self.notebook.RemovePage(1)  # keeps the panel alive (not Delete)
            self.events_page.Hide()

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
                    # QL echoes the canonical casing (e.g. "sv_maxClients"),
                    # so normalize to lowercase for case-insensitive lookups.
                    state.connect_info[cvar.group("name").lower()] = (
                        colors.strip_colors(cvar.group("val")).strip()
                    )
                    self._maybe_show_summary(server)
                    continue
                if player is not None or is_echo or not line.strip(' "'):
                    continue
            if hide_echo and is_echo:
                continue
            # Cvar query replies (`"name" is:"..." default:"..."`) aren't
            # print-wrapped; cleaning would strip their meaningful quotes and
            # mangle the line, so leave such lines untouched.
            if self.config.settings.clean_output and not _CVAR_RESPONSE_RE.match(line):
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
        self, server: ServerConfig, store: list[Line], ctrl: ConsoleView, runs: Line
    ) -> None:
        store.append(runs)
        if len(store) > MAX_LINES:
            del store[: len(store) - MAX_LINES]
        if server is self._selected_server():
            ctrl.append_line(runs)

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
