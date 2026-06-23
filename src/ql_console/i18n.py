"""Minimal in-app internationalization.

Usage:
    from .i18n import t, set_language
    label = t("btn_add")
    label = t("confirm_remove", name="QL4")

Add a new language by giving every key an entry for that language code and
listing it in ``LANGUAGES``.
"""

from __future__ import annotations

# code -> display name (order defines the picker order)
LANGUAGES: dict[str, str] = {"en": "English", "ru": "Русский"}

_DEFAULT = "ru"
_current = _DEFAULT

_TRANSLATIONS: dict[str, dict[str, str]] = {
    # Window / menu
    "app_title": {"en": "Quake Live RCON Console", "ru": "Quake Live RCON Console"},
    "menu_settings": {"en": "Settings", "ru": "Настройки"},
    "menu_open_settings": {"en": "Settings…\tCtrl+,", "ru": "Настройки…\tCtrl+,"},
    # Server list buttons
    "btn_add": {"en": "Add", "ru": "Добавить"},
    "btn_edit": {"en": "Edit", "ru": "Изменить"},
    "btn_remove": {"en": "Remove", "ru": "Удалить"},
    "btn_connect": {"en": "Connect", "ru": "Подключить"},
    "btn_disconnect": {"en": "Disconnect", "ru": "Отключить"},
    # Console
    "tab_console": {"en": "Console", "ru": "Консоль"},
    "tab_events": {"en": "Events", "ru": "События"},
    "btn_send": {"en": "Send", "ru": "Отправить"},
    "btn_clear": {"en": "Clear", "ru": "Очистить"},
    # Status bar
    "status_ready": {"en": "Ready", "ru": "Готово"},
    "status_rcon": {"en": "RCON: {status}", "ru": "RCON: {status}"},
    "status_stats": {"en": "Stats: {status}", "ru": "Stats: {status}"},
    "status_off": {"en": "off", "ru": "выкл"},
    "state_connecting": {"en": "connecting", "ru": "подключение"},
    "state_connected": {"en": "connected", "ru": "подключено"},
    "state_disconnected": {"en": "disconnected", "ru": "отключено"},
    "state_error": {"en": "error", "ru": "ошибка"},
    # Message boxes
    "msg_disconnect_before_edit": {
        "en": "Disconnect before editing this server.",
        "ru": "Отключитесь перед редактированием этого сервера.",
    },
    "title_in_use": {"en": "In use", "ru": "Занято"},
    "confirm_remove": {"en": "Remove server '{name}'?", "ru": "Удалить сервер «{name}»?"},
    "title_confirm": {"en": "Confirm", "ru": "Подтверждение"},
    "msg_not_connected": {"en": "Not connected.", "ru": "Нет подключения."},
    "title_send": {"en": "Send", "ru": "Отправка"},
    # Server dialog
    "dlg_add_server": {"en": "Add Server", "ru": "Добавить сервер"},
    "dlg_edit_server": {"en": "Edit Server", "ru": "Изменить сервер"},
    "lbl_name": {"en": "Name:", "ru": "Имя:"},
    "lbl_host": {"en": "Host / IP:", "ru": "Хост / IP:"},
    "lbl_rcon_port": {"en": "RCON port:", "ru": "RCON-порт:"},
    "lbl_rcon_password": {"en": "RCON password:", "ru": "RCON-пароль:"},
    "chk_stats": {
        "en": "Subscribe to live events (stats)",
        "ru": "Подписка на события (stats)",
    },
    "lbl_stats_port": {"en": "Stats port:", "ru": "Stats-порт:"},
    "lbl_stats_password": {"en": "Stats password:", "ru": "Stats-пароль:"},
    "server_unnamed": {"en": "Unnamed", "ru": "Без имени"},
    # Settings dialog
    "dlg_settings": {"en": "Settings", "ru": "Настройки"},
    "section_general": {"en": "General", "ru": "Общие"},
    "section_view": {"en": "View", "ru": "Вид"},
    "lbl_language": {"en": "Language:", "ru": "Язык:"},
    "chk_hide_echo": {
        "en": "Hide RCON command echo",
        "ru": "Скрывать эхо RCON-команд",
    },
    "chk_clean_output": {
        "en": "Process output (strip print wrappers)",
        "ru": "Обрабатывать вывод (убирать print-обёртки)",
    },
    "lbl_console_font": {"en": "Console font:", "ru": "Шрифт консоли:"},
    "lbl_font_size": {"en": "Font size:", "ru": "Размер шрифта:"},
    "lbl_console_bg": {"en": "Console background:", "ru": "Цвет фона консоли:"},
    "font_default": {"en": "(default)", "ru": "(по умолчанию)"},
    # Console log lines
    "log_connecting_to": {"en": "connecting to {endpoint}", "ru": "подключение к {endpoint}"},
    "log_disconnected": {"en": "disconnected", "ru": "отключено"},
    "log_server_summary": {
        "en": "{name}  ·  map: {map}  ·  players: {players}",
        "ru": "{name}  ·  карта: {map}  ·  игроков: {players}",
    },
}


def set_language(lang: str) -> None:
    global _current
    _current = lang if lang in LANGUAGES else _DEFAULT


def current_language() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    """Translate ``key`` into the current language, formatting any kwargs."""
    entry = _TRANSLATIONS.get(key, {})
    text = entry.get(_current) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text
