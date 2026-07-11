"""
KeyCaptureEdit: a read-only QLineEdit that records the actual key
combination pressed, instead of accepting typed text.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QLineEdit

from theme import t


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
            parts.append("win")

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
