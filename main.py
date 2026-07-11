"""
Entry point for Hotkey HUD.

Run with:  python main.py
"""

import sys
import threading

from PySide6.QtWidgets import QApplication, QMessageBox

from theme import t
from system_integration import acquire_single_instance_lock
from hud import HotkeyHUD
from listener import run_listener


def main():
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


if __name__ == "__main__":
    main()
