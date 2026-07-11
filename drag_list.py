"""
DragReorderList: a QListWidget that keeps each row's custom item widget
stretched to the full available width, and notifies a callback after a
drag-and-drop reorder finishes.
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QListWidget


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
