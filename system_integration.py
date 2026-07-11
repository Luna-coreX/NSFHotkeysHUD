"""
OS-level integration: Windows autostart (registry Run key), a
programmatically-drawn tray icon (so it stays in sync with the user's
accent color), and a single-instance lock via QSharedMemory.
"""

import os
import sys

from PySide6.QtCore import Qt, QSharedMemory
from PySide6.QtGui import QColor, QPainter, QBrush, QPixmap, QIcon

import theme

if sys.platform == "win32":
    import winreg


# =========================
# 🪟 AUTOSTART (Windows only)
# =========================
AUTOSTART_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = "NSFHotkeyHUD"


def _autostart_command():
    """Build the command line that should run at login.

    Two cases, detected automatically via `sys.frozen` (set by PyInstaller
    and similar packagers) - no manual editing needed either way:
      - Frozen .exe: sys.executable IS the app itself, no python.exe and
        no separate script path involved - just point at it directly.
      - Plain `python main.py`: sys.executable is python.exe, so we need
        to pass this script's path as an argument too.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    script_path = os.path.abspath(sys.argv[0])
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
    painter.setBrush(QBrush(QColor(theme.ACCENT_TEAL)))
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
