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
    "menu_file": {"en": "File", "ru": "Файл"},
    "menu_save_servers": {
        "en": "Save server list…",
        "ru": "Сохранить список серверов…",
    },
    "menu_load_servers": {
        "en": "Load server list…",
        "ru": "Загрузить список серверов…",
    },
    "menu_clear_servers": {
        "en": "Clear server list",
        "ru": "Очистить список серверов",
    },
    "menu_exit": {"en": "Exit\tAlt+F4", "ru": "Выход\tAlt+F4"},
    "menu_open_settings": {"en": "Settings…\tCtrl+,", "ru": "Настройки…\tCtrl+,"},
    "menu_help": {"en": "Help", "ru": "Справка"},
    "menu_about": {"en": "About…", "ru": "О программе…"},
    "about_title": {"en": "About", "ru": "О программе"},
    "about_text": {
        "en": "Quake Live RCON Console\nVersion {version}\n\nA console for administering Quake Live servers over RCON.",
        "ru": "Quake Live RCON Console\nВерсия {version}\n\nКонсоль для администрирования серверов Quake Live по RCON.",
    },
    "about_github": {"en": "GitHub page", "ru": "Страница на GitHub"},
    # Server list buttons
    "btn_add": {"en": "Add", "ru": "Добавить"},
    "btn_edit": {"en": "Edit", "ru": "Изменить"},
    "btn_remove": {"en": "Remove", "ru": "Удалить"},
    "btn_connect": {"en": "Connect", "ru": "Подключить"},
    "btn_disconnect": {"en": "Disconnect", "ru": "Отключить"},
    "menu_launch_steam": {"en": "Launch in Steam", "ru": "Запустить в Steam"},
    "menu_disconnect_all": {"en": "Disconnect all", "ru": "Отключить все"},
    # Console
    "tab_console": {"en": "Console", "ru": "Консоль"},
    "tab_events": {"en": "Events", "ru": "События"},
    "btn_send": {"en": "Send", "ru": "Отправить"},
    "btn_clear": {"en": "Clear console", "ru": "Очистить консоль"},
    # Status bar
    "status_ready": {"en": "Ready", "ru": "Готово"},
    "status_rcon": {"en": "RCON: {status}", "ru": "RCON: {status}"},
    "status_stats": {"en": "Stats: {status}", "ru": "Stats: {status}"},
    "status_off": {"en": "off", "ru": "выкл"},
    "state_connecting": {"en": "connecting", "ru": "подключение"},
    "state_connected": {"en": "connected", "ru": "подключено"},
    "state_disconnected": {"en": "disconnected", "ru": "отключено"},
    "state_error": {"en": "error", "ru": "ошибка"},
    "err_auth_failed": {
        "en": "authentication failed — check the RCON password",
        "ru": "ошибка аутентификации — проверьте RCON-пароль",
    },
    "err_max_attempts": {
        "en": "could not connect after {n} attempts — check the password/port",
        "ru": "не удалось подключиться за {n} попыток — проверьте пароль/порт",
    },
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
    # Save / load / clear server list
    "dlg_save_servers": {"en": "Save server list", "ru": "Сохранить список серверов"},
    "dlg_load_servers": {"en": "Load server list", "ru": "Загрузить список серверов"},
    "confirm_clear_servers": {
        "en": "Clear the entire server list?",
        "ru": "Очистить весь список серверов?",
    },
    "title_error": {"en": "Error", "ru": "Ошибка"},
    "msg_save_failed": {
        "en": "Could not save the file:\n{error}",
        "ru": "Не удалось сохранить файл:\n{error}",
    },
    "msg_load_failed": {
        "en": "Could not load the file — it is missing or not a valid server list:\n{error}",
        "ru": "Не удалось загрузить файл — он отсутствует или не является корректным списком серверов:\n{error}",
    },
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
    "lbl_hint_language": {"en": "Hint language:", "ru": "Язык подсказок:"},
    "hint_lang_same": {"en": "Same as interface", "ru": "Как в интерфейсе"},
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
