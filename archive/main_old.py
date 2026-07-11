import sys
import os
import json
import threading
import subprocess
import webbrowser

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QMenu, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect, QFileInfo, QSize, QSharedMemory
from PySide6.QtGui import QGuiApplication, QColor, QAction, QPainter, QBrush
from PySide6.QtWidgets import QLineEdit, QPushButton, QComboBox, QDialog, QFormLayout
from PySide6.QtGui import QKeyEvent, QKeySequence, QPixmap, QIcon
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PySide6.QtWidgets import QFileDialog, QMessageBox, QFileIconProvider, QColorDialog, QSlider
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt
from listener import run_listener

if sys.platform == "win32":
    import winreg

CONFIG_FILE = "hotkeys.json"
STATE_FILE = "hud_state.json"
ICONS_DIR = "icons"

os.makedirs(ICONS_DIR, exist_ok=True)


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
THEME_FILE = "theme.json"

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
    "hud_opacity": 1.0,  # 0.3 - 1.0
    # language
    "language": "ru",    # "ru" or "en"
}

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
# in the file (written once, before Settings existed) picks up the latest
# theme without needing to be rewritten to read from a dict every time.
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
TYPE_ACCENT = {
    "app": ACCENT_TEAL,
    "folder": ACCENT_VIOLET,
    "url": ACCENT_AMBER,
}


def apply_theme(theme):
    """Push a theme dict into the module-level color/appearance/language
    globals used throughout the file, and rebuild the derived TYPE_ACCENT map."""
    global TEXT_PRIMARY, TEXT_MUTED, ACCENT_TEAL, ACCENT_VIOLET, ACCENT_AMBER
    global ACCENT_ERROR, ACCENT_SUCCESS, PANEL_BG
    global FONT_SCALE, CARD_SCALE, HUD_OPACITY, LANGUAGE

    TEXT_PRIMARY = theme["text_primary"]
    TEXT_MUTED = theme["text_muted"]
    ACCENT_TEAL = theme["accent_teal"]
    ACCENT_VIOLET = theme["accent_violet"]
    ACCENT_AMBER = theme["accent_amber"]
    ACCENT_ERROR = theme["accent_error"]
    ACCENT_SUCCESS = ACCENT_TEAL
    PANEL_BG = hex_to_rgba_css(theme["panel_rgb"], 190)

    FONT_SCALE = theme.get("font_scale", 1.0)
    CARD_SCALE = theme.get("card_scale", 1.0)
    HUD_OPACITY = theme.get("hud_opacity", 1.0)
    LANGUAGE = theme.get("language", "ru")

    TYPE_ACCENT["app"] = ACCENT_TEAL
    TYPE_ACCENT["folder"] = ACCENT_VIOLET
    TYPE_ACCENT["url"] = ACCENT_AMBER


# load any previously saved theme immediately so the very first window built
# already reflects the user's saved colors, not the hardcoded defaults
apply_theme(load_theme())


# =========================
# 🪟 AUTOSTART (Windows only)
# =========================
AUTOSTART_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = "HotkeyHUD"


def _autostart_command():
    """Build the command line that should run at login.

    Two cases, detected automatically via `sys.frozen` (set by PyInstaller
    and similar packagers) - no manual editing needed either way:
      - Frozen .exe: sys.executable IS the app itself, no python.exe and
        no separate script path involved - just point at it directly.
      - Plain `python hotkey_hud.py`: sys.executable is python.exe, so we
        need to pass this script's path as an argument too.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    script_path = os.path.abspath(__file__)
    return f'"{sys.executable}" "{script_path}"'


def is_autostart_enabled():
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
            winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_autostart(enabled):
    if sys.platform != "win32":
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError as e:
        print(f"[autostart] Could not update registry: {e}")


# =========================
# 🖼 TRAY ICON
# =========================
def build_tray_icon():
    """Draw a small circular tray icon in the current accent color instead
    of shipping a separate image asset - keeps the tray icon in sync with
    whatever theme color the user picks."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(ACCENT_TEAL)))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    painter.setPen(QColor("#12161F"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(34)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "H")
    painter.end()

    return QIcon(pixmap)


# =========================
# 🔒 SINGLE INSTANCE
# =========================
def acquire_single_instance_lock():
    """Returns a QSharedMemory the caller must keep a reference to for the
    app's lifetime, or None if another instance is already holding it."""
    shared_memory = QSharedMemory("HotkeyHUD-single-instance-lock")

    if shared_memory.attach():
        # Someone else already created this segment - another instance owns it.
        return None

    if not shared_memory.create(1):
        return None

    return shared_memory



# =========================
# 🎹 KEY COMBO CAPTURE
# =========================
class KeyCaptureEdit(QLineEdit):
    """A read-only line edit that records the actual key combination pressed
    instead of accepting typed text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText(t("press_combo"))
        self.combo = ""

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # Ignore lone modifier presses - we wait for a full combo
        if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
            return

        modifiers = event.modifiers()
        parts = []

        if modifiers & Qt.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.MetaModifier:
            parts.append("meta")

        key_text = QKeySequence(key).toString().lower()
        if key_text:
            parts.append(key_text)

        if not parts:
            return

        self.combo = "+".join(parts)
        self.setText(self.combo)

    def mousePressEvent(self, event):
        # clicking clears the field so a new combo can be recorded
        self.clear()
        self.combo = ""
        super().mousePressEvent(event)


# =========================
# 🚀 LAUNCH HELPERS
# =========================
def launch_target(data):
    """Launch an app / folder / url depending on the hotkey's stored type.

    Returns a (success, error_message) tuple so the caller can show the user
    a proper notification instead of failing silently."""
    target_type = data.get("type")
    path = data.get("path", "")

    if not path:
        return False, t("path_not_set")

    # Catch the most common real-world failure early: the file/folder was
    # renamed, moved, or the drive is unplugged.
    if target_type in ("app", "folder") and not os.path.exists(path):
        return False, t("path_not_found", path=path)

    try:
        if target_type == "url":
            webbrowser.open(path)
        elif target_type == "folder":
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        elif target_type == "app":
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen([path])
        else:
            return False, t("unknown_type", type=target_type)
    except Exception as e:
        return False, str(e)

    return True, None


def extract_icon(path, save_key):
    """Extract the OS icon for a given .exe/file/folder path and save it as
    a PNG in ICONS_DIR. Returns the saved icon path, or None on failure."""
    try:
        provider = QFileIconProvider()
        info = QFileInfo(path)
        icon: QIcon = provider.icon(info)
        pixmap: QPixmap = icon.pixmap(64, 64)

        if pixmap.isNull():
            return None

        safe_name = "".join(c if c.isalnum() else "_" for c in save_key)
        icon_path = os.path.join(ICONS_DIR, f"{safe_name}.png")
        pixmap.save(icon_path)
        return icon_path
    except Exception as e:
        print(f"[extract_icon] Error extracting icon for '{path}': {e}")
        return None


# =========================
# 📝 ADD / EDIT HOTKEY DIALOG
# =========================
class HotkeyDialog(QDialog):
    def __init__(self, parent=None, edit_hotkey=None, edit_data=None, existing_config=None):
        super().__init__(parent)
        self.edit_hotkey = edit_hotkey
        self.edit_data = edit_data or {}
        self.icon_path = self.edit_data.get("icon_path")
        # used to warn if the recorded combo already belongs to another entry
        self.existing_config = existing_config or {}

        self.setWindowTitle(t("dialog_title_edit") if edit_hotkey else t("dialog_title_add"))
        self.setFixedSize(360, 340)

        # Dark theme so the dialog doesn't clash with the HUD it belongs to.
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #12161F;
            }}
            QLabel {{
                color: {TEXT_PRIMARY};
                font-family: {FONT_UI};
                font-size: {fs(12)}px;
                background: transparent;
            }}
            QLineEdit, QComboBox {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 8px;
                padding: 5px 8px;
                font-family: {FONT_UI};
                font-size: {fs(12)}px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {hex_to_rgba_css(ACCENT_TEAL, 130)};
            }}
            QComboBox QAbstractItemView {{
                background-color: #1A1F2B;
                color: {TEXT_PRIMARY};
                selection-background-color: {hex_to_rgba_css(ACCENT_TEAL, 40)};
            }}
            QPushButton {{
                color: {TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 18)};
                border: 1px solid {hex_to_rgba_css(ACCENT_TEAL, 60)};
                border-radius: 8px;
                padding: 6px 10px;
                font-family: {FONT_UI};
                font-size: {fs(12)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 32)};
            }}
        """)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(18, 18, 18, 18)

        # --- Hotkey (recorded, not typed) ---
        self.hk_input = KeyCaptureEdit()
        if edit_hotkey:
            self.hk_input.setText(edit_hotkey)
            self.hk_input.combo = edit_hotkey
        form.addRow(t("field_hotkey"), self.hk_input)

        # --- Name ---
        self.name_input = QLineEdit(self.edit_data.get("title", ""))
        form.addRow(t("field_name"), self.name_input)

        # --- Type ---
        self.type_input = QComboBox()
        self.type_input.addItems(["app", "folder", "url"])
        if self.edit_data.get("type") in ("app", "folder", "url"):
            self.type_input.setCurrentText(self.edit_data["type"])
        self.type_input.currentTextChanged.connect(self.on_type_changed)
        form.addRow(t("field_type"), self.type_input)

        # --- Path / URL row ---
        path_row = QHBoxLayout()
        self.path_input = QLineEdit(self.edit_data.get("path", ""))
        self.browse_btn = QPushButton(t("browse"))
        self.browse_btn.clicked.connect(self.browse_path)
        path_row.addWidget(self.path_input)
        path_row.addWidget(self.browse_btn)
        form.addRow(t("field_path"), path_row)

        # --- Icon row ---
        icon_row = QHBoxLayout()
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(32, 32)
        self.update_icon_preview()

        self.icon_btn = QPushButton(t("pick_icon"))
        self.icon_btn.clicked.connect(self.browse_icon)

        icon_row.addWidget(self.icon_preview)
        icon_row.addWidget(self.icon_btn)
        form.addRow(t("field_icon"), icon_row)

        # --- Save button ---
        save_btn = QPushButton(t("save"))
        save_btn.clicked.connect(self.save)
        form.addRow(save_btn)

        self.setLayout(form)
        self.on_type_changed(self.type_input.currentText())

    def on_type_changed(self, type_value):
        self.browse_btn.setEnabled(type_value != "url")
        if type_value == "url":
            self.path_input.setPlaceholderText("https://example.com")
        else:
            self.path_input.setPlaceholderText("")

    def browse_path(self):
        type_value = self.type_input.currentText()

        if type_value == "folder":
            path = QFileDialog.getExistingDirectory(self, t("select_folder"))
        else:  # app
            filter_str = "Executables (*.exe);;All Files (*)" if sys.platform == "win32" else "All Files (*)"
            path, _ = QFileDialog.getOpenFileName(self, t("select_app"), "", filter_str)

        if path:
            self.path_input.setText(path)
            # auto-suggest an icon from the same path if none picked yet
            if not self.icon_path:
                candidate_key = self.hk_input.combo or "temp"
                extracted = extract_icon(path, candidate_key)
                if extracted:
                    self.icon_path = extracted
                    self.update_icon_preview()

    def browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("select_icon_source"), "",
            "All Files (*)"
        )
        if not path:
            return

        candidate_key = self.hk_input.combo or "temp"
        extracted = extract_icon(path, candidate_key)
        if extracted:
            self.icon_path = extracted
            self.update_icon_preview()
        else:
            QMessageBox.warning(self, t("icon_warning_title"), t("icon_warning_msg"))

    def update_icon_preview(self):
        if self.icon_path and os.path.exists(self.icon_path):
            self.icon_preview.setPixmap(QPixmap(self.icon_path).scaled(32, 32, Qt.KeepAspectRatio))
        else:
            self.icon_preview.clear()

    def save(self):
        hk = self.hk_input.combo.strip()
        name = self.name_input.text().strip()
        type_value = self.type_input.currentText()
        path = self.path_input.text().strip()

        if not hk or not name or not path:
            QMessageBox.warning(self, t("missing_info_title"), t("missing_info_msg"))
            return

        # Warn if this combo already belongs to a *different* entry - editing
        # and keeping the same combo you started with is fine, not a conflict.
        conflict = self.existing_config.get(hk)
        if conflict is not None and hk != self.edit_hotkey:
            reply = QMessageBox.question(
                self,
                t("duplicate_title"),
                t("duplicate_msg", hk=hk) + "\n\n" + conflict.get("title", ""),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.result_hotkey = hk
        self.result_data = {
            "title": name,
            "type": type_value,
            "path": path,
            "icon": type_value,
            "icon_path": self.icon_path,
        }
        self.accept()


# Keys for each customizable color swatch, in the order shown in the dialog.
# Labels are resolved via t(f"field_{key}") at dialog-build time so they
# follow whatever language is active.
THEME_COLOR_KEYS = [
    "accent_teal",
    "accent_violet",
    "accent_amber",
    "accent_error",
    "text_primary",
    "text_muted",
    "panel_rgb",
]

LANGUAGE_CHOICES = [("ru", "Русский"), ("en", "English")]


class ThemeSettingsDialog(QDialog):
    """Full appearance settings: a color swatch + hex field for every
    themeable token, sliders for font size / card size / HUD opacity, and
    a language selector - all live-previewed and persisted together."""

    def __init__(self, parent=None, current_theme=None):
        super().__init__(parent)
        self.theme = dict(current_theme or load_theme())
        self.swatches = {}
        self.hex_edits = {}

        self.setWindowTitle(t("settings_title"))
        self.setFixedWidth(360)

        self.setStyleSheet(f"""
            QDialog {{ background-color: #12161F; }}
            QLabel {{
                color: {TEXT_PRIMARY};
                font-family: {FONT_UI};
                font-size: {fs(12)}px;
                background: transparent;
            }}
            QLabel#sectionLabel {{
                color: {TEXT_MUTED};
                font-size: {fs(10)}px;
                font-weight: 700;
                letter-spacing: 2px;
                padding-top: 6px;
            }}
            QCheckBox {{
                color: {TEXT_PRIMARY};
                font-family: {FONT_UI};
                font-size: {fs(12)}px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 30);
                background-color: rgba(255, 255, 255, 8);
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_TEAL};
                border: 1px solid {ACCENT_TEAL};
            }}
            QLineEdit, QComboBox {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 8px;
                padding: 4px 8px;
                font-family: {FONT_MONO};
                font-size: {fs(11)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1A1F2B;
                color: {TEXT_PRIMARY};
                selection-background-color: {hex_to_rgba_css(ACCENT_TEAL, 40)};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 18);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                margin: -6px 0;
                background: {ACCENT_TEAL};
                border-radius: 7px;
            }}
            QPushButton#saveBtn {{
                color: {TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 22)};
                border: 1px solid {hex_to_rgba_css(ACCENT_TEAL, 70)};
                border-radius: 8px;
                padding: 7px;
                font-weight: 600;
            }}
            QPushButton#saveBtn:hover {{
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 38)};
            }}
            QPushButton#resetBtn {{
                color: {TEXT_MUTED};
                background-color: rgba(255, 255, 255, 6);
                border: 1px solid rgba(255, 255, 255, 16);
                border-radius: 8px;
                padding: 7px;
            }}
            QPushButton#resetBtn:hover {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 12);
            }}
        """)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(18, 18, 18, 12)

        # --- colors ---
        colors_label = QLabel(t("section_colors"))
        colors_label.setObjectName("sectionLabel")
        form.addRow(colors_label)

        for key in THEME_COLOR_KEYS:
            row = QHBoxLayout()
            row.setSpacing(6)

            swatch = QPushButton()
            swatch.setFixedSize(28, 24)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.clicked.connect(lambda _, k=key: self.pick_color(k))
            self.swatches[key] = swatch

            hex_edit = QLineEdit(self.theme.get(key, DEFAULT_THEME[key]))
            hex_edit.textChanged.connect(lambda text, k=key: self.on_hex_changed(k, text))
            self.hex_edits[key] = hex_edit

            row.addWidget(swatch)
            row.addWidget(hex_edit)

            row_widget = QWidget()
            row_widget.setLayout(row)
            form.addRow(t(f"field_{key}") + ":", row_widget)

            self._update_swatch(key)

        # --- appearance sliders (font size / card size / HUD opacity) ---
        appearance_label = QLabel(t("section_appearance"))
        appearance_label.setObjectName("sectionLabel")
        form.addRow(appearance_label)

        self.font_slider, self.font_value_label = self._add_slider_row(
            form, t("font_size"),
            80, 140, round(self.theme.get("font_scale", 1.0) * 100),
            lambda v: self._on_slider_changed("font_scale", v)
        )
        self.card_slider, self.card_value_label = self._add_slider_row(
            form, t("card_size"),
            80, 140, round(self.theme.get("card_scale", 1.0) * 100),
            lambda v: self._on_slider_changed("card_scale", v)
        )
        self.opacity_slider, self.opacity_value_label = self._add_slider_row(
            form, t("hud_opacity"),
            40, 100, round(self.theme.get("hud_opacity", 1.0) * 100),
            lambda v: self._on_slider_changed("hud_opacity", v)
        )

        # --- language ---
        language_label = QLabel(t("section_language"))
        language_label.setObjectName("sectionLabel")
        form.addRow(language_label)

        self.language_combo = QComboBox()
        for code, name in LANGUAGE_CHOICES:
            self.language_combo.addItem(name, userData=code)
        current_lang = self.theme.get("language", "ru")
        idx = next((i for i, (code, _) in enumerate(LANGUAGE_CHOICES) if code == current_lang), 0)
        self.language_combo.setCurrentIndex(idx)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        form.addRow(self.language_combo)

        # --- system (autostart) ---
        system_label = QLabel(t("section_system"))
        system_label.setObjectName("sectionLabel")
        form.addRow(system_label)

        self.autostart_checkbox = QCheckBox(t("autostart_label"))
        self.autostart_checkbox.setChecked(is_autostart_enabled())
        if sys.platform != "win32":
            self.autostart_checkbox.setEnabled(False)
            self.autostart_checkbox.setToolTip(t("autostart_unavailable"))
        form.addRow(self.autostart_checkbox)

        # --- buttons ---
        btn_row = QHBoxLayout()
        reset_btn = QPushButton(t("reset_defaults"))
        reset_btn.setObjectName("resetBtn")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self.reset_defaults)

        save_btn = QPushButton(t("save"))
        save_btn.setObjectName("saveBtn")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save)

        btn_row.addWidget(reset_btn)
        btn_row.addWidget(save_btn)
        form.addRow(btn_row)

        self.setLayout(form)

    def _add_slider_row(self, form, label_text, minimum, maximum, initial, on_change):
        row = QHBoxLayout()
        row.setSpacing(8)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(initial)

        value_label = QLabel(f"{initial}%")
        value_label.setFixedWidth(38)

        def handle_change(v):
            value_label.setText(f"{v}%")
            on_change(v)

        slider.valueChanged.connect(handle_change)

        row.addWidget(slider, stretch=1)
        row.addWidget(value_label)

        row_widget = QWidget()
        row_widget.setLayout(row)
        form.addRow(label_text + ":", row_widget)

        return slider, value_label

    def _on_slider_changed(self, key, value):
        self.theme[key] = value / 100.0

    def _on_language_changed(self, index):
        code, _ = LANGUAGE_CHOICES[index]
        self.theme["language"] = code

    def _update_swatch(self, key):
        color = self.theme.get(key, DEFAULT_THEME[key])
        self.swatches[key].setStyleSheet(f"""
            background-color: {color};
            border: 1px solid rgba(255, 255, 255, 30);
            border-radius: 6px;
        """)

    def pick_color(self, key):
        initial = QColor(self.theme.get(key, DEFAULT_THEME[key]))
        color = QColorDialog.getColor(initial, self, t("choose_color"))

        if color.isValid():
            hex_value = color.name()  # "#rrggbb"
            self.theme[key] = hex_value
            self.hex_edits[key].blockSignals(True)
            self.hex_edits[key].setText(hex_value)
            self.hex_edits[key].blockSignals(False)
            self._update_swatch(key)

    def on_hex_changed(self, key, text):
        text = text.strip()
        if QColor(text).isValid() and text.startswith("#") and len(text) == 7:
            self.theme[key] = text
            self._update_swatch(key)

    def reset_defaults(self):
        self.theme = dict(DEFAULT_THEME)

        for key in THEME_COLOR_KEYS:
            self.hex_edits[key].blockSignals(True)
            self.hex_edits[key].setText(self.theme[key])
            self.hex_edits[key].blockSignals(False)
            self._update_swatch(key)

        self.font_slider.setValue(round(self.theme["font_scale"] * 100))
        self.card_slider.setValue(round(self.theme["card_scale"] * 100))
        self.opacity_slider.setValue(round(self.theme["hud_opacity"] * 100))

        default_idx = next(
            (i for i, (code, _) in enumerate(LANGUAGE_CHOICES) if code == self.theme["language"]),
            0
        )
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(default_idx)
        self.language_combo.blockSignals(False)

    def save(self):
        if sys.platform == "win32":
            set_autostart(self.autostart_checkbox.isChecked())

        self.result_theme = dict(self.theme)
        self.accept()


class DragReorderList(QListWidget):
    """QListWidget that keeps each row's item widget stretched to the full
    available width (Qt doesn't do this automatically for custom item
    widgets set via setItemWidget()), and notifies a callback after a
    drag-and-drop reorder finishes.

    Note: QListWidget's built-in model doesn't implement moveRows(), so
    internal-move drag-and-drop ends up as remove+insert rather than an
    actual move - which means the model's rowsMoved signal never fires.
    Overriding dropEvent() is what reliably fires after every reorder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.on_reorder = None

    def dropEvent(self, event):
        super().dropEvent(event)
        if self.on_reorder:
            self.on_reorder()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.viewport().width()
        for i in range(self.count()):
            item = self.item(i)
            item.setSizeHint(QSize(w, item.sizeHint().height()))


class HotkeyHUD(QWidget):
    show_signal = Signal(str)
    show_error_signal = Signal(str, str)

    def __init__(self):
        super().__init__()

        # =========================
        # 🧠 LOAD STATE (POSITION + SIZE)
        # =========================
        self.state = self.load_state()

        self.base_w = self.state.get("w", 420)
        self.base_h = self.state.get("h", 500)
        self.scale = self.state.get("scale", 1.0)

        self.setGeometry(
            self.state.get("x", 1400),
            self.state.get("y", 50),
            self.base_w,
            self.base_h
        )

        # =========================
        # 🪟 WINDOW
        # =========================
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        # drag / resize state
        self.dragging = False
        self.drag_pos = None

        self.resizing = False
        self.resize_start_rect = None
        self.resize_start_pos = None

        # toggled from the tray menu - trigger() skips launching while True
        self.paused = False
        self._exit_requested = False

        self.show_signal.connect(self._show_toast)

        # =========================
        # 🧾 HOTKEY LIST
        # =========================
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- header row: pulsing status dot + eyebrow title + count badge ---
        header_row = QHBoxLayout()
        header_row.setContentsMargins(6, 0, 6, 0)
        header_row.setSpacing(8)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(7, 7)

        self._status_dot_effect = QGraphicsOpacityEffect()
        self.status_dot.setGraphicsEffect(self._status_dot_effect)
        self._pulse_anim = QPropertyAnimation(self._status_dot_effect, b"opacity")
        self._pulse_anim.setDuration(1400)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setKeyValueAt(0.5, 0.25)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.start()

        self.title_label = QLabel(t("hud_title"))

        self.count_badge = QLabel("0")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setFixedHeight(18)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(22, 22)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        self.minimize_btn = QPushButton("—")
        self.minimize_btn.setFixedSize(22, 22)
        self.minimize_btn.setCursor(Qt.PointingHandCursor)
        self.minimize_btn.setToolTip(t("minimize_tooltip"))
        self.minimize_btn.clicked.connect(self.hide)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip(t("close_tooltip"))
        self.close_btn.clicked.connect(self.close)

        header_row.addWidget(self.status_dot)
        header_row.addWidget(self.title_label)
        header_row.addStretch()
        header_row.addWidget(self.count_badge)
        header_row.addWidget(self.settings_btn)
        header_row.addWidget(self.minimize_btn)
        header_row.addWidget(self.close_btn)

        header_container = QWidget()
        header_container.setLayout(header_row)

        self.add_btn = QPushButton(t("add_hotkey"))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.open_add_dialog)

        # =========================
        # 🔍 SEARCH
        # =========================
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_placeholder"))
        self.search_input.textChanged.connect(self.filter_hotkeys)

        # =========================
        # 🧾 HOTKEY LIST (drag-and-drop reorderable)
        # =========================
        self.list_widget = DragReorderList()
        self.list_widget.setViewportMargins(8, 8, 8, 8)
        self.list_widget.setSpacing(8)
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.on_reorder = self._on_rows_moved

        panel_shadow = QGraphicsDropShadowEffect()
        panel_shadow.setBlurRadius(48)
        panel_shadow.setColor(QColor(0, 0, 0, 150))
        panel_shadow.setOffset(0, 10)
        self.list_widget.setGraphicsEffect(panel_shadow)

        # apply all theme-dependent stylesheets now that the widgets exist -
        # also re-called after the user changes colors in Settings
        self.apply_theme_styles()

        layout.addWidget(header_container)
        layout.addWidget(self.search_input)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.add_btn)

        self.setLayout(layout)

        # =========================
        # 🔳 RESIZE HANDLE (SUBTLE)
        # =========================
        self.resize_handle = QLabel("⋰", self)
        self.resize_handle.setFixedSize(14, 14)
        self.resize_handle.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        self.resize_handle.setCursor(Qt.SizeFDiagCursor)
        self.resize_handle.setStyleSheet(f"""
            color: rgba(255, 255, 255, 55);
            font-size: {fs(14)}px;
            font-weight: 700;
            background: transparent;
        """)
        self.resize_handle.raise_()

        # =========================
        # 📦 CONFIG
        # =========================
        self.config = self.load_config()
        self.update_hotkey_list()

        # =========================
        # ⚡ TOAST
        # =========================
        self.toast = QWidget()

        self.toast.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.toast.setAttribute(Qt.WA_TranslucentBackground)
        self.toast.setFixedSize(460, 80)

        self.toast_label = QLabel(self.toast)
        self.toast_label.setGeometry(0, 0, 460, 80)
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setWordWrap(True)
        self.toast_label.setContentsMargins(16, 8, 16, 8)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.toast.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        self.toast.hide()

        self.fade_anim = None
        self.resize_anim = None

        self.show_error_signal.connect(self._show_error_toast)

        self.setWindowOpacity(HUD_OPACITY)

        self._setup_tray_icon()

        QTimer.singleShot(0, self.update_resize_handle)

    # =========================
    # 🎨 THEME
    # =========================
    def apply_theme_styles(self):
        """(Re)apply every stylesheet that depends on the current color
        theme. Called once during __init__ and again after the user saves
        new colors in the Settings dialog."""
        self.status_dot.setStyleSheet(f"""
            background-color: {ACCENT_TEAL};
            border-radius: 3px;
        """)

        self.title_label.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: {fs(13)}px;
            font-family: {FONT_UI};
            font-weight: 700;
            letter-spacing: 3px;
        """)

        self.count_badge.setStyleSheet(f"""
            color: {TEXT_MUTED};
            background-color: rgba(255, 255, 255, 8);
            border-radius: 9px;
            font-size: {fs(11)}px;
            font-family: {FONT_MONO};
            padding: 0px 8px;
        """)

        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_MUTED};
                background-color: rgba(255, 255, 255, 8);
                border: none;
                border-radius: 11px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 30)};
            }}
        """)

        self.minimize_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_MUTED};
                background-color: rgba(255, 255, 255, 8);
                border: none;
                border-radius: 11px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 20);
            }}
        """)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_MUTED};
                background-color: rgba(255, 255, 255, 8);
                border: none;
                border-radius: 11px;
                font-size: {fs(11)}px;
            }}
            QPushButton:hover {{
                color: {TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(ACCENT_ERROR, 45)};
            }}
        """)

        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 18)};
                border: 1px solid {hex_to_rgba_css(ACCENT_TEAL, 60)};
                border-radius: 10px;
                padding: 7px;
                font-size: {fs(12)}px;
                font-family: {FONT_UI};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 32)};
                border: 1px solid {hex_to_rgba_css(ACCENT_TEAL, 110)};
            }}
            QPushButton:pressed {{
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 45)};
            }}
        """)

        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 6);
                border: 1px solid rgba(255, 255, 255, 14);
                border-radius: 10px;
                padding: 7px 12px;
                font-size: {fs(12)}px;
                font-family: {FONT_UI};
                selection-background-color: {hex_to_rgba_css(ACCENT_TEAL, 60)};
            }}
            QLineEdit:focus {{
                border: 1px solid {hex_to_rgba_css(ACCENT_TEAL, 130)};
                background-color: rgba(255, 255, 255, 9);
            }}
        """)

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {PANEL_BG};
                border: 1px solid rgba(255, 255, 255, 12);
                border-radius: 16px;
            }}
            QListWidget::item {{
                border: none;
                background: transparent;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 30);
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def retranslate_ui(self):
        """Refresh every static UI string (not user data) after a language
        change - hotkey titles/paths themselves are user data and are
        never translated."""
        self.title_label.setText(t("hud_title"))
        self.add_btn.setText(t("add_hotkey"))
        self.search_input.setPlaceholderText(t("search_placeholder"))
        self.minimize_btn.setToolTip(t("minimize_tooltip"))
        self.close_btn.setToolTip(t("close_tooltip"))

        if hasattr(self, "tray_icon"):
            self.tray_icon.setToolTip(t("tray_tooltip"))
            self.tray_action_show.setText(t("tray_open"))
            self.tray_action_pause.setText(t("tray_pause"))
            self.tray_action_exit.setText(t("tray_exit"))

    def open_settings_dialog(self):
        dialog = ThemeSettingsDialog(self, current_theme=load_theme())

        if dialog.exec() == QDialog.Accepted:
            new_theme = dialog.result_theme
            apply_theme(new_theme)
            save_theme(new_theme)

            # re-paint everything with the new colors/sizes/language: chrome
            # first, then every card (create_hotkey_card reads the globals
            # we just updated), then window-level opacity and static text
            self.apply_theme_styles()
            self.update_hotkey_list()
            self.setWindowOpacity(HUD_OPACITY)
            self.retranslate_ui()

            if hasattr(self, "tray_icon"):
                self.tray_icon.setIcon(build_tray_icon())

    # =========================
    # 🖥 TRAY ICON / WINDOW LIFECYCLE
    # =========================
    def _setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(build_tray_icon(), self)
        self.tray_icon.setToolTip(t("tray_tooltip"))

        self.tray_menu = QMenu()
        menu = self.tray_menu

        self.tray_action_show = QAction(t("tray_open"), self)
        self.tray_action_show.triggered.connect(self.show_and_raise)
        menu.addAction(self.tray_action_show)

        self.tray_action_pause = QAction(t("tray_pause"), self)
        self.tray_action_pause.setCheckable(True)
        self.tray_action_pause.toggled.connect(self.set_paused)
        menu.addAction(self.tray_action_pause)

        menu.addSeparator()

        self.tray_action_exit = QAction(t("tray_exit"), self)
        self.tray_action_exit.triggered.connect(self.quit_app)
        menu.addAction(self.tray_action_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        # left-click / double-click toggles the HUD; right-click just opens
        # the context menu (handled automatically by Qt)
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def set_paused(self, paused):
        self.paused = paused
        color = TEXT_MUTED if paused else ACCENT_TEAL
        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 3px;
        """)

        if hasattr(self, "tray_icon"):
            message = t("tray_paused_msg") if paused else t("tray_resumed_msg")
            self.tray_icon.showMessage(t("tray_tooltip"), message, QSystemTrayIcon.Information, 1500)

    def quit_app(self):
        self._exit_requested = True
        self.save_state()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """The custom ✕ button (and any other close attempt, e.g. Alt+F4)
        minimizes to the tray instead of quitting - the only real exit path
        is the tray menu's Exit action, so the app can't vanish by accident."""
        if self._exit_requested:
            event.accept()
            return

        event.ignore()
        self.hide()

        if hasattr(self, "tray_icon") and not getattr(self, "_shown_tray_hint", False):
            self._shown_tray_hint = True
            self.tray_icon.showMessage(
                t("tray_tooltip"), t("minimized_to_tray_msg"),
                QSystemTrayIcon.Information, 2000
            )

    # =========================
    # 📦 STATE SAVE / LOAD
    # =========================
    def load_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_state(self):
        data = {
            "x": self.x(),
            "y": self.y(),
            "w": self.width(),
            "h": self.height(),
            "scale": self.scale
        }

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # =========================
    # ➕ ADD / ✏️ EDIT / 🗑 DELETE
    # =========================
    def open_add_dialog(self):
        dialog = HotkeyDialog(self, existing_config=self.config)
        if dialog.exec() == QDialog.Accepted:
            hk = dialog.result_hotkey
            self.config[hk] = dialog.result_data
            self.save_config()
            self.update_hotkey_list()

    def open_edit_dialog(self, hk):
        data = self.config.get(hk, {})
        dialog = HotkeyDialog(self, edit_hotkey=hk, edit_data=data, existing_config=self.config)

        if dialog.exec() == QDialog.Accepted:
            new_hk = dialog.result_hotkey

            # if the hotkey combo changed, remove the old key
            if new_hk != hk and hk in self.config:
                del self.config[hk]

            self.config[new_hk] = dialog.result_data
            self.save_config()
            self.update_hotkey_list()

    def delete_hotkey(self, hk):
        reply = QMessageBox.question(
            self,
            t("delete_title"),
            t("delete_msg", hk=hk),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes and hk in self.config:
            del self.config[hk]
            self.save_config()
            self.update_hotkey_list()

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    # =========================
    # 🧾 HOTKEY CARDS
    # =========================
    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def build_keycap_row(self, hk):
        """Render a hotkey combo as small physical-keycap chips (WIN + CTRL + 3)
        instead of a plain bracketed string - the combo itself is the subject
        of this app, so it gets a treatment that looks like actual keys."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        parts = [p for p in hk.split("+") if p.strip()]

        for i, part in enumerate(parts):
            if i > 0:
                plus = QLabel("+")
                plus.setStyleSheet(f"""
                    color: {TEXT_MUTED};
                    font-size: {fs(10)}px;
                    background: transparent;
                """)
                row.addWidget(plus)

            chip = QLabel(part.strip().upper())
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(f"""
                color: #C7D0E0;
                background-color: rgba(255, 255, 255, 7);
                border: 1px solid rgba(255, 255, 255, 15);
                border-bottom: 2px solid rgba(255, 255, 255, 20);
                border-radius: 5px;
                padding: 1px 6px;
                font-size: {fs(10)}px;
                font-family: {FONT_MONO};
                font-weight: 600;
                letter-spacing: 0.5px;
            """)
            row.addWidget(chip)

        row.addStretch()

        wrapper = QWidget()
        wrapper.setLayout(row)
        return wrapper

    def create_hotkey_card(self, hk, data):
        card = QWidget()
        card.setObjectName("hotkeyCard")
        card.setFixedHeight(cs(62))

        title = data.get("title", "Action")
        # Respect an explicit color from hotkeys.json (old entries keep their
        # own look); otherwise fall back to a color coded by type, so the
        # accent bar actually means something (app / folder / url) rather
        # than being decoration.
        color = data.get("color") or TYPE_ACCENT.get(data.get("type"), ACCENT_TEAL)
        icon_path = data.get("icon_path")

        icon_map = {
            "unity": "🟦",
            "folder": "📁",
            "app": "⚙️",
            "url": "🔗"
        }

        # The card itself only needs a rounded background - no border here.
        # (Mixing `border-left` with `border-radius` on the same widget is what
        # produced the broken "((" bracket artifact - Qt draws the rounded
        # corners and the colored border as separate overlapping arcs instead
        # of one clean bar.) The ID selector keeps :hover scoped to just this
        # widget instead of cascading into its child QWidgets/QLabels.
        card.setStyleSheet(f"""
            QWidget#hotkeyCard {{
                background-color: {CARD_BG};
                border-radius: 12px;
            }}
            QWidget#hotkeyCard:hover {{
                background-color: {CARD_BG_HOVER};
            }}
        """)

        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        card.setLayout(outer)

        # --- accent color bar (separate flat widget, rounded only on its
        # own outer edge so it matches the card's corners cleanly) ---
        accent = QWidget()
        accent.setFixedWidth(max(2, cs(3)))
        accent.setStyleSheet(f"""
            background-color: {color};
            border-top-left-radius: 12px;
            border-bottom-left-radius: 12px;
        """)
        outer.addWidget(accent)

        # --- inner content row (icon + text stack + buttons) ---
        content = QHBoxLayout()
        content.setContentsMargins(cs(11), cs(8), cs(10), cs(8))
        content.setSpacing(cs(11))
        outer.addLayout(content)

        # --- icon (extracted image if available, else emoji), in its own
        # fixed square box so it never overlaps neighboring elements ---
        icon_box = QLabel()
        icon_box.setFixedSize(cs(34), cs(34))
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet("""
            background-color: rgba(255, 255, 255, 6);
            border-radius: 9px;
        """)

        if icon_path and os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(
                cs(22), cs(22), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icon_box.setPixmap(pix)
        else:
            emoji = icon_map.get(data.get("icon", "app"), "⚙️")
            icon_box.setText(emoji)
            icon_box.setStyleSheet(icon_box.styleSheet() + f"font-size: {fs(17)}px;")

        # --- text stack: title on top, keycap chips underneath ---
        text_stack = QVBoxLayout()
        text_stack.setContentsMargins(0, 0, 0, 0)
        text_stack.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: {fs(13)}px;
            font-family: {FONT_UI};
            font-weight: 600;
            background: transparent;
        """)

        text_stack.addWidget(title_label)
        text_stack.addWidget(self.build_keycap_row(hk))

        text_stack_wrapper = QWidget()
        text_stack_wrapper.setLayout(text_stack)

        # --- edit / delete buttons (hover tint hints at the action) ---
        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(cs(26), cs(26))
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 6);
                border: none;
                border-radius: 8px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(ACCENT_TEAL, 30)};
            }}
        """)
        edit_btn.clicked.connect(lambda: self.open_edit_dialog(hk))

        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(cs(26), cs(26))
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 6);
                border: none;
                border-radius: 8px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(ACCENT_ERROR, 35)};
            }}
        """)
        delete_btn.clicked.connect(lambda: self.delete_hotkey(hk))

        content.addWidget(icon_box)
        content.addWidget(text_stack_wrapper, stretch=1)
        content.addWidget(edit_btn)
        content.addWidget(delete_btn)

        return card

    def update_hotkey_list(self):
        self.list_widget.clear()

        initial_width = self.list_widget.viewport().width() or 380

        if not self.config:
            placeholder = QListWidgetItem()
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setSizeHint(QSize(initial_width, cs(140)))
            self.list_widget.addItem(placeholder)
            self.list_widget.setItemWidget(placeholder, self._build_empty_state())
        else:
            for hk, data in self.config.items():
                item = QListWidgetItem()
                item.setData(Qt.UserRole, hk)
                item.setSizeHint(QSize(initial_width, cs(62)))

                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, self.create_hotkey_card(hk, data))

        if hasattr(self, "count_badge"):
            self.count_badge.setText(str(len(self.config)))

        # keep the current search text applied after a rebuild (e.g. after add/edit/delete)
        if hasattr(self, "search_input"):
            self.filter_hotkeys(self.search_input.text())

    def _build_empty_state(self):
        """Shown instead of the list when there are no hotkeys configured yet."""
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        icon = QLabel("⌨")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: {fs(28)}px;
            background: transparent;
        """)

        text = QLabel(t("empty_state"))
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: {fs(12)}px;
            font-family: {FONT_UI};
            background: transparent;
        """)

        layout.addWidget(icon)
        layout.addWidget(text)
        wrapper.setLayout(layout)
        return wrapper

    # =========================
    # 🔍 SEARCH
    # =========================
    def filter_hotkeys(self, text):
        query = text.strip().lower()

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            hk = item.data(Qt.UserRole)

            # skip the empty-state placeholder item (no hotkey data attached)
            if hk is None:
                continue

            data = self.config.get(hk, {})

            haystack = " ".join([
                data.get("title", ""),
                hk,
                data.get("path", "")
            ]).lower()

            item.setHidden(bool(query) and query not in haystack)


    # =========================
    # 🖱 DRAG-AND-DROP REORDER
    # =========================
    def _on_rows_moved(self):
        """After the user drags a card to a new position, rebuild self.config
        in the new order (dicts preserve insertion order) and persist it."""
        new_order = {}

        for i in range(self.list_widget.count()):
            hk = self.list_widget.item(i).data(Qt.UserRole)
            if hk in self.config:
                new_order[hk] = self.config[hk]

        self.config = new_order
        self.save_config()

    # =========================
    # 🚀 TRIGGER / LAUNCH / TOAST
    # =========================
    def trigger(self, hotkey):
        if self.paused:
            return

        if hotkey not in self.config:
            return

        data = self.config[hotkey]
        title = data.get("title", "Unknown")

        success, error = launch_target(data)

        if success:
            self.show_signal.emit(title)
        else:
            self.show_error_signal.emit(title, error or t("unknown_error"))

    def _display_toast(self, text, border_rgba, duration_ms):
        self.toast_label.setText(text)
        self.toast_label.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(13, 17, 26, 235),
                stop:1 rgba(19, 24, 36, 225)
            );
            border-radius: 16px;
            border: 1px solid {border_rgba};
            font-size: {fs(13)}px;
            font-weight: 500;
            font-family: {FONT_UI};
        """)

        self.toast.show()
        self.position_toast()

        if self.fade_anim:
            self.fade_anim.stop()

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

        QTimer.singleShot(duration_ms, self._fade_out_toast)

    def _show_toast(self, title):
        self._display_toast(
            t("launched", title=title),
            border_rgba=f"{hex_to_rgba_css(ACCENT_TEAL, 110)}",
            duration_ms=1500
        )

    def _show_error_toast(self, title, message):
        self._display_toast(
            t("launch_failed", title=title, message=message),
            border_rgba=f"{hex_to_rgba_css(ACCENT_ERROR, 160)}",
            duration_ms=3000
        )

    def _fade_out_toast(self):
        if self.fade_anim:
            self.fade_anim.stop()

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.fade_anim.finished.connect(self.toast.hide)
        self.fade_anim.start()

    def position_toast(self):
        screen = QGuiApplication.primaryScreen().geometry()
        self.toast.move(
            (screen.width() - self.toast.width()) // 2,
            screen.height() - self.toast.height() - 60
        )

    # =========================
    # 🖱 DRAG + RESIZE (SMOOTH)
    # =========================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()

            if self.resize_handle.geometry().contains(pos):
                self.resizing = True
                self.resize_start_rect = self.geometry()
                self.resize_start_pos = event.globalPosition().toPoint()
                return

            self.dragging = True
            self.drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if self.resizing:
            delta = event.globalPosition().toPoint() - self.resize_start_pos

            new_rect = QRect(
                self.resize_start_rect.x(),
                self.resize_start_rect.y(),
                max(300, self.resize_start_rect.width() + delta.x()),
                max(200, self.resize_start_rect.height() + delta.y())
            )

            if self.resize_anim:
                self.resize_anim.stop()

            self.resize_anim = QPropertyAnimation(self, b"geometry")
            self.resize_anim.setDuration(120)
            self.resize_anim.setStartValue(self.geometry())
            self.resize_anim.setEndValue(new_rect)
            self.resize_anim.setEasingCurve(QEasingCurve.OutCubic)
            self.resize_anim.start()

            self.update_resize_handle()
            return

        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.save_state()

    # =========================
    # 🔳 HANDLE
    # =========================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_resize_handle()

    def update_resize_handle(self):
        self.resize_handle.move(
            self.width() - 12,
            self.height() - 12
        )


# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Hiding the HUD (minimize / close-to-tray) should NOT quit the whole
    # app - only the tray menu's "Exit" action should.
    app.setQuitOnLastWindowClosed(False)

    instance_lock = acquire_single_instance_lock()
    if instance_lock is None:
        QMessageBox.warning(
            None,
            t("single_instance_title"),
            t("single_instance_msg")
        )
        sys.exit(0)

    hud = HotkeyHUD()
    hud.show()

    threading.Thread(target=run_listener, args=(hud,), daemon=True).start()

    sys.exit(app.exec())