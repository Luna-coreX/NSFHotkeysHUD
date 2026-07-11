"""
ThemeSettingsDialog: the full Settings window - color swatches, font/card
size sliders, HUD opacity, language selector, and Windows autostart.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QWidget, QLabel, QLineEdit,
    QComboBox, QPushButton, QCheckBox, QSlider, QColorDialog
)

import theme
from theme import t, fs, hex_to_rgba_css, DEFAULT_THEME, load_theme
from system_integration import is_autostart_enabled, set_autostart

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
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_UI};
                font-size: {fs(12)}px;
                background: transparent;
            }}
            QLabel#sectionLabel {{
                color: {theme.TEXT_MUTED};
                font-size: {fs(10)}px;
                font-weight: 700;
                letter-spacing: 2px;
                padding-top: 6px;
            }}
            QCheckBox {{
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_UI};
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
                background-color: {theme.ACCENT_TEAL};
                border: 1px solid {theme.ACCENT_TEAL};
            }}
            QLineEdit, QComboBox {{
                color: {theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 8px;
                padding: 4px 8px;
                font-family: {theme.FONT_MONO};
                font-size: {fs(11)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1A1F2B;
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 40)};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 18);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                margin: -6px 0;
                background: {theme.ACCENT_TEAL};
                border-radius: 7px;
            }}
            QPushButton#saveBtn {{
                color: {theme.TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 22)};
                border: 1px solid {hex_to_rgba_css(theme.ACCENT_TEAL, 70)};
                border-radius: 8px;
                padding: 7px;
                font-weight: 600;
            }}
            QPushButton#saveBtn:hover {{
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 38)};
            }}
            QPushButton#resetBtn {{
                color: {theme.TEXT_MUTED};
                background-color: rgba(255, 255, 255, 6);
                border: 1px solid rgba(255, 255, 255, 16);
                border-radius: 8px;
                padding: 7px;
            }}
            QPushButton#resetBtn:hover {{
                color: {theme.TEXT_PRIMARY};
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
