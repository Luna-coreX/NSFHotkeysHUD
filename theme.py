"""
Theme, appearance, and translation settings for Hotkey HUD.

Everything the user can customize in Settings (colors, font size, card
size, HUD opacity, language) lives here as module-level state, persisted
to THEME_FILE. Other modules should `import theme` and reference values
as `theme.TEXT_PRIMARY`, `theme.ACCENT_TEAL`, etc. (NOT
`from theme import TEXT_PRIMARY`) so they always see the live value after
apply_theme() reassigns it - a plain import would freeze a stale copy.

Functions (t, fs, cs, hex_to_rgba_css, apply_theme, load_theme, save_theme)
are safe to import directly with `from theme import ...`, since a function
always reads module globals from the module it was DEFINED in, not the one
that imported it.
"""

import json
from paths import THEME_FILE

# =========================
# 🎨 DESIGN TOKENS / THEME
# =========================
# A small "control deck" palette: deep space background, a cool teal signal
# color as the primary accent (status/active state), violet and amber as
# secondary signals so *type* carries meaning through color, not decoration.
#
# These are user-customizable (see Settings dialog) and persisted to
# THEME_FILE, so the module-level values below are just the defaults /
# current values - they get overwritten by apply_theme() at startup and
# whenever the user saves new colors in Settings.

DEFAULT_THEME = {
    "panel_rgb": "#0A0E16",     # base color the panel background is tinted from
    "text_primary": "#EDF1F8",
    "text_muted": "#7C889C",
    "accent_teal": "#4FE0C7",   # signal / active / default "app" accent
    "accent_violet": "#9B87F5",  # "folder" accent
    "accent_amber": "#F5B95B",  # "url" accent
    "accent_error": "#F2777A",
    # appearance
    "font_scale": 1.0,   # 0.8 - 1.4
    "card_scale": 1.0,   # 0.8 - 1.4
    "hud_opacity": 1.0,  # 0.4 - 1.0
    # language
    "language": "ru",    # "ru" or "en"
}

# Static - never reassigned at runtime, safe for other modules to import directly.
CARD_BG = "rgba(255, 255, 255, 6)"
CARD_BG_HOVER = "rgba(255, 255, 255, 11)"

FONT_UI = '"Segoe UI", "Inter", sans-serif'
FONT_MONO = '"JetBrains Mono", "Consolas", monospace'


# =========================
# 🌍 TRANSLATIONS
# =========================
STRINGS = {
    "ru": {
        "hud_title": "ХОТКЕИ",
        "search_placeholder": "⌕   Поиск по названию, хоткею или пути",
        "add_hotkey": "＋  Добавить хоткей",
        "launched": "🚀  {title} запущен",
        "launch_failed": "⚠️  Не удалось запустить «{title}»\n{message}",
        "dialog_title_add": "Добавить хоткей",
        "dialog_title_edit": "Редактировать хоткей",
        "field_hotkey": "Хоткей:",
        "field_name": "Название:",
        "field_type": "Тип:",
        "field_path": "Путь/URL:",
        "field_icon": "Иконка:",
        "browse": "Обзор...",
        "pick_icon": "Выбрать иконку...",
        "save": "Сохранить",
        "missing_info_title": "Не хватает данных",
        "missing_info_msg": "Заполните хоткей, название и путь/URL.",
        "icon_warning_title": "Иконка",
        "icon_warning_msg": "Не удалось извлечь иконку из этого пути.",
        "delete_title": "Удалить хоткей",
        "delete_msg": "Удалить хоткей «{hk}»?",
        "settings_title": "Настройки",
        "section_colors": "ЦВЕТА",
        "section_appearance": "ВНЕШНИЙ ВИД",
        "section_language": "ЯЗЫК",
        "field_accent_teal": "Акцент приложений",
        "field_accent_violet": "Акцент папок",
        "field_accent_amber": "Акцент ссылок",
        "field_accent_error": "Ошибка / предупреждение",
        "field_text_primary": "Основной текст",
        "field_text_muted": "Приглушённый текст",
        "field_panel_rgb": "Фон панели",
        "font_size": "Размер шрифта",
        "card_size": "Размер карточек",
        "hud_opacity": "Прозрачность HUD",
        "reset_defaults": "Сбросить по умолчанию",
        "press_combo": "Нажмите комбинацию клавиш...",
        "path_not_set": "Путь не указан",
        "path_not_found": "Путь не найден:\n{path}",
        "unknown_type": "Неизвестный тип цели: {type}",
        "unknown_error": "Неизвестная ошибка",
        "select_folder": "Выберите папку",
        "select_app": "Выберите приложение",
        "select_icon_source": "Выберите источник иконки (.exe, файл или папка)",
        "choose_color": "Выбор цвета",
        "tray_open": "Показать",
        "tray_pause": "Пауза хоткеев",
        "tray_exit": "Выход",
        "tray_tooltip": "Hotkey HUD",
        "tray_paused_msg": "Хоткеи на паузе",
        "tray_resumed_msg": "Хоткеи снова активны",
        "duplicate_title": "Хоткей уже занят",
        "duplicate_msg": "Комбинация «{hk}» уже используется другим хоткеем.",
        "empty_state": "Хоткеев пока нет — нажми ＋ чтобы добавить",
        "autostart_label": "Запускать при старте Windows",
        "autostart_unavailable": "Доступно только в Windows",
        "single_instance_title": "Уже запущено",
        "single_instance_msg": "Hotkey HUD уже работает в трее.",
        "minimize_tooltip": "Свернуть",
        "close_tooltip": "Свернуть в трей",
        "minimized_to_tray_msg": "Приложение свернуто в трей и продолжает работать.",
        "section_system": "СИСТЕМА",
    },
    "en": {
        "hud_title": "HOTKEYS",
        "search_placeholder": "⌕   Search by name, hotkey, or path",
        "add_hotkey": "＋  Add Hotkey",
        "launched": "🚀  {title} launched",
        "launch_failed": "⚠️  Failed to launch \"{title}\"\n{message}",
        "dialog_title_add": "Add Hotkey",
        "dialog_title_edit": "Edit Hotkey",
        "field_hotkey": "Hotkey:",
        "field_name": "Name:",
        "field_type": "Type:",
        "field_path": "Path/URL:",
        "field_icon": "Icon:",
        "browse": "Browse...",
        "pick_icon": "Pick Icon...",
        "save": "Save",
        "missing_info_title": "Missing info",
        "missing_info_msg": "Please fill in hotkey, name and path/url.",
        "icon_warning_title": "Icon",
        "icon_warning_msg": "Could not extract an icon from that path.",
        "delete_title": "Delete Hotkey",
        "delete_msg": "Delete the hotkey '{hk}'?",
        "settings_title": "Settings",
        "section_colors": "COLORS",
        "section_appearance": "APPEARANCE",
        "section_language": "LANGUAGE",
        "field_accent_teal": "App accent",
        "field_accent_violet": "Folder accent",
        "field_accent_amber": "URL accent",
        "field_accent_error": "Error / warning",
        "field_text_primary": "Primary text",
        "field_text_muted": "Muted text",
        "field_panel_rgb": "Panel background",
        "font_size": "Font size",
        "card_size": "Card size",
        "hud_opacity": "HUD opacity",
        "reset_defaults": "Reset to Defaults",
        "press_combo": "Press a key combination...",
        "path_not_set": "Path not set",
        "path_not_found": "Path not found:\n{path}",
        "unknown_type": "Unknown target type: {type}",
        "unknown_error": "Unknown error",
        "select_folder": "Select Folder",
        "select_app": "Select Application",
        "select_icon_source": "Select icon source (.exe or any file/folder)",
        "choose_color": "Choose color",
        "tray_open": "Open",
        "tray_pause": "Pause Hotkeys",
        "tray_exit": "Exit",
        "tray_tooltip": "Hotkey HUD",
        "tray_paused_msg": "Hotkeys paused",
        "tray_resumed_msg": "Hotkeys resumed",
        "duplicate_title": "Hotkey already in use",
        "duplicate_msg": "The combination '{hk}' is already assigned to another hotkey.",
        "empty_state": "No hotkeys yet - tap ＋ to add one",
        "autostart_label": "Start with Windows",
        "autostart_unavailable": "Only available on Windows",
        "single_instance_title": "Already running",
        "single_instance_msg": "Hotkey HUD is already running in the tray.",
        "minimize_tooltip": "Minimize",
        "close_tooltip": "Minimize to tray",
        "minimized_to_tray_msg": "The app minimized to the tray and is still running.",
        "section_system": "SYSTEM",
    },
}

LANGUAGE = DEFAULT_THEME["language"]


def t(key, **kwargs):
    """Translate a UI string key into the current language, formatting any
    {placeholders} with kwargs."""
    template = STRINGS.get(LANGUAGE, STRINGS["en"]).get(key) \
        or STRINGS["en"].get(key, key)
    return template.format(**kwargs) if kwargs else template


def fs(base_px):
    """Scale a font size in px by the user's font_scale setting."""
    return max(8, round(base_px * FONT_SCALE))


def cs(base_px):
    """Scale a card/layout dimension in px by the user's card_scale setting."""
    return max(1, round(base_px * CARD_SCALE))


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba_css(hex_color, alpha):
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def load_theme():
    theme = dict(DEFAULT_THEME)
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        theme.update({k: v for k, v in saved.items() if k in DEFAULT_THEME})
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return theme


def save_theme(theme):
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2)


# Current live values, kept as module globals so every stylesheet f-string
# across the app picks up the latest theme. Other modules must access these
# as `theme.TEXT_PRIMARY` etc. (via `import theme`) rather than
# `from theme import TEXT_PRIMARY`, or they'll capture a stale copy that
# never updates after apply_theme() reassigns it.
TEXT_PRIMARY = DEFAULT_THEME["text_primary"]
TEXT_MUTED = DEFAULT_THEME["text_muted"]
ACCENT_TEAL = DEFAULT_THEME["accent_teal"]
ACCENT_VIOLET = DEFAULT_THEME["accent_violet"]
ACCENT_AMBER = DEFAULT_THEME["accent_amber"]
ACCENT_ERROR = DEFAULT_THEME["accent_error"]
ACCENT_SUCCESS = ACCENT_TEAL
PANEL_BG = hex_to_rgba_css(DEFAULT_THEME["panel_rgb"], 190)
FONT_SCALE = DEFAULT_THEME["font_scale"]
CARD_SCALE = DEFAULT_THEME["card_scale"]
HUD_OPACITY = DEFAULT_THEME["hud_opacity"]

# Default accent per hotkey type, used only if a card has no explicit
# "color" field in hotkeys.json - keeps old configs (with their own colors)
# working unchanged while giving new entries meaningful, type-coded color.
# This is a dict that gets MUTATED in place (not reassigned), so importing
# it directly with `from theme import TYPE_ACCENT` stays live safely.
TYPE_ACCENT = {
    "app": ACCENT_TEAL,
    "folder": ACCENT_VIOLET,
    "url": ACCENT_AMBER,
}


def apply_theme(new_theme):
    """Push a theme dict into the module-level color/appearance/language
    globals used throughout the app, and rebuild the derived TYPE_ACCENT map."""
    global TEXT_PRIMARY, TEXT_MUTED, ACCENT_TEAL, ACCENT_VIOLET, ACCENT_AMBER
    global ACCENT_ERROR, ACCENT_SUCCESS, PANEL_BG
    global FONT_SCALE, CARD_SCALE, HUD_OPACITY, LANGUAGE

    TEXT_PRIMARY = new_theme["text_primary"]
    TEXT_MUTED = new_theme["text_muted"]
    ACCENT_TEAL = new_theme["accent_teal"]
    ACCENT_VIOLET = new_theme["accent_violet"]
    ACCENT_AMBER = new_theme["accent_amber"]
    ACCENT_ERROR = new_theme["accent_error"]
    ACCENT_SUCCESS = ACCENT_TEAL
    PANEL_BG = hex_to_rgba_css(new_theme["panel_rgb"], 190)

    FONT_SCALE = new_theme.get("font_scale", 1.0)
    CARD_SCALE = new_theme.get("card_scale", 1.0)
    HUD_OPACITY = new_theme.get("hud_opacity", 1.0)
    LANGUAGE = new_theme.get("language", "ru")

    TYPE_ACCENT["app"] = ACCENT_TEAL
    TYPE_ACCENT["folder"] = ACCENT_VIOLET
    TYPE_ACCENT["url"] = ACCENT_AMBER


# load any previously saved theme immediately so the very first window built
# already reflects the user's saved colors, not the hardcoded defaults
apply_theme(load_theme())
