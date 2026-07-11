"""
HotkeyDialog: the add/edit form for a single hotkey entry - records a key
combination, lets the user pick a target path/url and an icon, and warns
before overwriting an existing hotkey combo.
"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFileDialog, QMessageBox
)

import theme
from theme import t, fs, hex_to_rgba_css
from key_capture import KeyCaptureEdit
from launcher import extract_icon


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
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_UI};
                font-size: {fs(12)}px;
                background: transparent;
            }}
            QLineEdit, QComboBox {{
                color: {theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 8px;
                padding: 5px 8px;
                font-family: {theme.FONT_UI};
                font-size: {fs(12)}px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {hex_to_rgba_css(theme.ACCENT_TEAL, 130)};
            }}
            QComboBox QAbstractItemView {{
                background-color: #1A1F2B;
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 40)};
            }}
            QPushButton {{
                color: {theme.TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 18)};
                border: 1px solid {hex_to_rgba_css(theme.ACCENT_TEAL, 60)};
                border-radius: 8px;
                padding: 6px 10px;
                font-family: {theme.FONT_UI};
                font-size: {fs(12)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 32)};
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
