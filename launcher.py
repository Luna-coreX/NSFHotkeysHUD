"""
Launching a hotkey's target (app / folder / url) and extracting an icon
image from a file/folder path for display in the HUD.
"""

import os
import sys
import subprocess
import webbrowser

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QFileIconProvider

from theme import t
from paths import ICONS_DIR

os.makedirs(ICONS_DIR, exist_ok=True)


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
