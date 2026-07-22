"""
HotkeyHUD: the main frameless overlay widget - hotkey list with search and
drag-and-drop reordering, the add/settings/minimize/close header buttons,
the tray icon lifecycle, and the launch toast notifications.
"""

import os
import threading

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QMenu, QLineEdit, QPushButton, QDialog,
    QMessageBox, QListWidgetItem, QAbstractItemView
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect, QSize
)
from PySide6.QtGui import QGuiApplication, QColor, QAction, QPixmap

import theme
from theme import t, fs, cs, hex_to_rgba_css, TYPE_ACCENT, CARD_BG, CARD_BG_HOVER, FONT_UI, FONT_MONO, load_theme, save_theme, apply_theme
import storage
import listener
from launcher import launch_target
from system_integration import build_tray_icon
from hotkey_dialog import HotkeyDialog
from settings_dialog import ThemeSettingsDialog
from drag_list import DragReorderList
import version


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

        # guards self.config, which is read from the listener thread in
        # trigger() while the GUI thread mutates it via add/edit/delete/reorder
        self._config_lock = threading.Lock()

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

        self.title_label = QLabel(self._title_text())

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

        self.show_error_signal.connect(self._show_error_toast)

        self.setWindowOpacity(theme.HUD_OPACITY)

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
            background-color: {theme.ACCENT_TEAL};
            border-radius: 3px;
        """)

        self.title_label.setStyleSheet(f"""
            color: {theme.TEXT_PRIMARY};
            font-size: {fs(13)}px;
            font-family: {FONT_UI};
            font-weight: 700;
            letter-spacing: 3px;
        """)

        self.count_badge.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            background-color: rgba(255, 255, 255, 8);
            border-radius: 9px;
            font-size: {fs(11)}px;
            font-family: {FONT_MONO};
            padding: 0px 8px;
        """)

        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme.TEXT_MUTED};
                background-color: rgba(255, 255, 255, 8);
                border: none;
                border-radius: 11px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                color: {theme.TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 30)};
            }}
        """)

        self.minimize_btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme.TEXT_MUTED};
                background-color: rgba(255, 255, 255, 8);
                border: none;
                border-radius: 11px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                color: {theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 20);
            }}
        """)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme.TEXT_MUTED};
                background-color: rgba(255, 255, 255, 8);
                border: none;
                border-radius: 11px;
                font-size: {fs(11)}px;
            }}
            QPushButton:hover {{
                color: {theme.TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(theme.ACCENT_ERROR, 45)};
            }}
        """)

        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme.TEXT_PRIMARY};
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 18)};
                border: 1px solid {hex_to_rgba_css(theme.ACCENT_TEAL, 60)};
                border-radius: 10px;
                padding: 7px;
                font-size: {fs(12)}px;
                font-family: {FONT_UI};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 32)};
                border: 1px solid {hex_to_rgba_css(theme.ACCENT_TEAL, 110)};
            }}
            QPushButton:pressed {{
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 45)};
            }}
        """)

        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                color: {theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 6);
                border: 1px solid rgba(255, 255, 255, 14);
                border-radius: 10px;
                padding: 7px 12px;
                font-size: {fs(12)}px;
                font-family: {FONT_UI};
                selection-background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 60)};
            }}
            QLineEdit:focus {{
                border: 1px solid {hex_to_rgba_css(theme.ACCENT_TEAL, 130)};
                background-color: rgba(255, 255, 255, 9);
            }}
        """)

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.PANEL_BG};
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

    def _title_text(self):
        """The HUD header label: localized title plus the app version."""
        return t("hud_title") + "     v" + version.__version__

    def retranslate_ui(self):
        """Refresh every static UI string (not user data) after a language
        change - hotkey titles/paths themselves are user data and are
        never translated."""
        self.title_label.setText(self._title_text())
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
            self.setWindowOpacity(theme.HUD_OPACITY)
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
        color = theme.TEXT_MUTED if paused else theme.ACCENT_TEAL
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
        return storage.load_state()

    def save_state(self):
        storage.save_state({
            "x": self.x(),
            "y": self.y(),
            "w": self.width(),
            "h": self.height(),
            "scale": self.scale
        })

    # =========================
    # ➕ ADD / ✏️ EDIT / 🗑 DELETE
    # =========================
    def open_add_dialog(self):
        dialog = HotkeyDialog(self, existing_config=self.config)
        if dialog.exec() == QDialog.Accepted:
            hk = dialog.result_hotkey
            with self._config_lock:
                self.config[hk] = dialog.result_data
            self.save_config()
            self.update_hotkey_list()

    def open_edit_dialog(self, hk):
        data = self.config.get(hk, {})
        dialog = HotkeyDialog(self, edit_hotkey=hk, edit_data=data, existing_config=self.config)

        if dialog.exec() == QDialog.Accepted:
            new_hk = dialog.result_hotkey

            with self._config_lock:
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
            with self._config_lock:
                del self.config[hk]
            self.save_config()
            self.update_hotkey_list()

    def save_config(self):
        storage.save_config(self.config)
        # Re-register global hotkeys so add/edit/delete/reorder take effect
        # immediately instead of only after an app restart.
        listener.reload_hotkeys()

    # =========================
    # 🧾 HOTKEY CARDS
    # =========================
    def load_config(self):
        return storage.load_config()

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
                    color: {theme.TEXT_MUTED};
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
        color = data.get("color") or TYPE_ACCENT.get(data.get("type"), theme.ACCENT_TEAL)
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
            color: {theme.TEXT_PRIMARY};
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
                color: {theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 6);
                border: none;
                border-radius: 8px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(theme.ACCENT_TEAL, 30)};
            }}
        """)
        edit_btn.clicked.connect(lambda: self.open_edit_dialog(hk))

        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(cs(26), cs(26))
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                color: {theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 6);
                border: none;
                border-radius: 8px;
                font-size: {fs(12)}px;
            }}
            QPushButton:hover {{
                background-color: {hex_to_rgba_css(theme.ACCENT_ERROR, 35)};
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
            color: {theme.TEXT_MUTED};
            font-size: {fs(28)}px;
            background: transparent;
        """)

        text = QLabel(t("empty_state"))
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
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

        with self._config_lock:
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

        # Called from the listener thread - snapshot the entry under the lock
        # so a concurrent add/edit/delete/reorder on the GUI thread can't
        # corrupt the read.
        with self._config_lock:
            data = self.config.get(hotkey)

        if data is None:
            return

        title = data.get("title", "Unknown")

        success, error = launch_target(data)

        if success:
            self.show_signal.emit(title)
        else:
            self.show_error_signal.emit(title, error or t("unknown_error"))

    def _display_toast(self, text, border_rgba, duration_ms):
        self.toast_label.setText(text)
        self.toast_label.setStyleSheet(f"""
            color: {theme.TEXT_PRIMARY};
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
            border_rgba=f"{hex_to_rgba_css(theme.ACCENT_TEAL, 110)}",
            duration_ms=1500
        )

    def _show_error_toast(self, title, message):
        self._display_toast(
            t("launch_failed", title=title, message=message),
            border_rgba=f"{hex_to_rgba_css(theme.ACCENT_ERROR, 160)}",
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

            # Apply the new size directly - animating toward a moving target on
            # every mouse-move event produced a laggy, rubber-banding resize.
            self.setGeometry(new_rect)
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
