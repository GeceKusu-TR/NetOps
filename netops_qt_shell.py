"""Native Qt Widgets presentation for NetOps.

This module intentionally uses stock PySide6 widgets and no QSS theme layer.
The backend is injected so the UI can be tested without starting NetOps
services or a second application event loop.
"""

from __future__ import annotations

import os
import math
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QStyle,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIcon, QPixmap

from netops_qt_backend import QtBackend, build_qt_backend


_PAGES = (
    ("chat", "Sohbet"),
    ("devices", "Cihazlar"),
    ("now_playing", "Now Playing"),
    ("automations", "Otomasyonlar"),
    ("remote", "Remote"),
    ("system", "Sistem Durumu"),
    ("notifications", "Bildirimler"),
    ("settings", "Ayarlar"),
)


def native_legacy_layout_contract() -> dict[str, tuple[str, ...] | str]:
    """Describe the preserved legacy NetOps layout in stable UI terms."""
    return {
        "top_status": ("SİSTEM", "REMOTE", "BİLDİRİMLER", "NOW PLAYING"),
        "sidebar": (
            "Genel Bakış",
            "Cihazlar",
            "Now Playing",
            "Otomasyonlar",
            "Remote",
            "Ayarlar",
        ),
        "bottom_input": "Mesajını yaz...",
    }


def native_page_keys() -> tuple[str, ...]:
    return tuple(key for key, _label in _PAGES)


def native_motion_contract() -> dict[str, int | str]:
    return {"startup_ms": 220, "page_ms": 180, "property": "windowOpacity"}


def native_animation_contract() -> dict[str, int]:
    return {
        "logo_fade_ms": 260,
        "sidebar_stagger_ms": 35,
        "button_feedback_ms": 120,
    }


def native_brand_contract() -> dict[str, str]:
    return {
        "app_name": "NetOps",
        "version": "1.52",
        "window_title": "NetOps 1.52",
        "logo_file": "Logo.png",
    }


def native_visual_contract() -> dict[str, int]:
    return {
        "now_playing_poll_ms": 1500,
        "system_poll_ms": 1000,
        "button_radius_px": 10,
        "button_feedback_ms": 120,
    }


def native_window_contract() -> dict[str, bool]:
    return {"start_maximized": True}


def native_settings_sections() -> tuple[str, ...]:
    return (
        "Genel",
        "Sistem",
        "Görünüm",
        "Pencere Yöneticisi",
        "Netolab",
        "Güvenlik",
        "Güncellemeler",
        "Hakkında",
    )


def native_sidebar_contract() -> dict[str, int | str]:
    return {
        "settings_button_count": 1,
        "panel_radius_px": 16,
        "status_message": "",
        "settings_position": "bottom",
    }


def native_sidebar_icon_contract() -> dict[str, str]:
    return {
        "chat": "message",
        "devices": "computer",
        "now_playing": "media",
        "automations": "workflow",
        "system": "system",
        "settings": "settings",
    }


def native_now_playing_contract() -> dict[str, int | str]:
    return {
        "fullscreen_title": "ŞU AN ÇALIYOR",
        "standby_title": "BEKLEME MODU",
        "refresh_ms": 1500,
    }


_LEGACY_THEME_PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#09090B",
        "sidebar": "#111114",
        "card": "#1B1B20",
        "entry_bg": "#141418",
        "entry_border": "#34343C",
        "text_main": "#F4F4F5",
        "text_dim": "#A1A1AA",
        "button_hover": "#2A2A31",
    },
    "light": {
        "bg": "#F4F5F7",
        "sidebar": "#FFFFFF",
        "card": "#E8EAEF",
        "entry_bg": "#FFFFFF",
        "entry_border": "#C8CDD6",
        "text_main": "#18181B",
        "text_dim": "#64646F",
        "button_hover": "#D9DDE5",
    },
}

_LEGACY_ACCENTS = {
    "green": "#22C55E",
    "blue": "#3B82F6",
    "dark-blue": "#2563EB",
}


def _blend_hex(source: str, target: str, ratio: float) -> str:
    try:
        source_rgb = [int(source[index:index + 2], 16) for index in (1, 3, 5)]
        target_rgb = [int(target[index:index + 2], 16) for index in (1, 3, 5)]
        values = [round(a + (b - a) * ratio) for a, b in zip(source_rgb, target_rgb)]
        return "#" + "".join(f"{max(0, min(255, value)):02X}" for value in values)
    except (TypeError, ValueError):
        return source


def native_theme_palette(settings: dict[str, Any] | None = None) -> dict[str, str]:
    """Translate the legacy NetOps theme settings into native Qt color tokens."""
    values = dict(settings or {})
    mode = "light" if str(values.get("tema", "dark")).lower() in {"light", "acik", "açık", "white"} else "dark"
    palette = dict(_LEGACY_THEME_PALETTES[mode])
    accent = _LEGACY_ACCENTS.get(str(values.get("renk_temasi", "blue")).lower(), _LEGACY_ACCENTS["blue"])
    palette.update(
        {
            "accent": accent,
            "accent_hover": _blend_hex(accent, "#000000" if mode == "light" else "#FFFFFF", 0.16),
            "accent_text": "#111114" if mode == "light" and accent == _LEGACY_ACCENTS["green"] else "#FFFFFF",
            "button_fg": palette["card"],
            "button_text": palette["text_main"],
            "neon": accent,
        }
    )
    return palette


def _display(value: Any) -> str:
    if isinstance(value, dict):
        if value.get("error"):
            return f"Hata: {value['error']}"
        if value.get("ok") is False:
            return f"İşlem başarısız: {value.get('error', 'bilinmeyen hata')}"
    return str(value)


class NetOpsQtWindow(QMainWindow):
    """Native Qt Widgets window for the NetOps desktop services."""

    def __init__(self, backend: QtBackend | None = None) -> None:
        super().__init__()
        self.backend = backend or build_qt_backend()
        self._pages: dict[str, QWidget] = {}
        self._page_stack = QStackedWidget()
        self._navigation = QListWidget()
        self._status = QLabel("Hazır")
        self._chat_output = QPlainTextEdit()
        self._chat_input = QLineEdit()
        self._chat_composer: QFrame | None = None
        self._chat_send_button: QPushButton | None = None
        self._chat_mode_button: QPushButton | None = None
        self._remote_output = QPlainTextEdit()
        self._remote_input = QLineEdit()
        self._system_values: dict[str, list[QLabel]] = {}
        self._devices_table = QTableWidget()
        self._automations_table = QTableWidget()
        self._notifications_list = QListWidget()
        self._now_playing_values: dict[str, QLabel] = {}
        self._now_playing_cover = QLabel()
        self._now_playing_island = QLabel("♪  Müzik bekleniyor")
        self._now_playing_island_animation: QPropertyAnimation | None = None
        self._now_playing_island_text = ""
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_label = QLabel("Ses: okunuyor")
        self._mute_button = QPushButton("Sessize al")
        self._now_playing_overlay: QWidget | None = None
        self._now_playing_overlay_values: dict[str, QLabel] = {}
        self._now_playing_overlay_cover: QLabel | None = None
        self._now_playing_overlay_platform: QLabel | None = None
        self._now_playing_overlay_album: QLabel | None = None
        self._now_playing_overlay_timeline: QLabel | None = None
        self._now_playing_overlay_progress: QProgressBar | None = None
        self._now_playing_overlay_volume_slider: QSlider | None = None
        self._now_playing_overlay_volume_label: QLabel | None = None
        self._now_playing_overlay_play_pause: QPushButton | None = None
        self._now_playing_overlay_mute: QPushButton | None = None
        self._now_playing_overlay_visualizer: QLabel | None = None
        self._now_playing_visualizer_phase = 0
        self._now_playing_visualizer_timer = QTimer(self)
        self._now_playing_visualizer_timer.setInterval(90)
        self._now_playing_visualizer_timer.timeout.connect(self._refresh_fullscreen_visualizer)
        self._now_playing_overlay_timer = QTimer(self)
        self._now_playing_overlay_timer.setInterval(native_now_playing_contract()["refresh_ms"])
        self._now_playing_overlay_timer.timeout.connect(self._refresh_now_playing_fullscreen)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._top_status_buttons: dict[str, QPushButton] = {}
        self._buttons_with_feedback: list[QPushButton] = []
        self._button_feedback_animations: dict[int, QPropertyAnimation] = {}
        settings = self.backend.run("settings")
        self._settings_data: dict[str, Any] = dict(settings) if isinstance(settings, dict) else {}
        self._native_palette = native_theme_palette(self._settings_data)
        self._settings_controls: dict[str, QWidget] = {}
        self._settings_tabs: QTabWidget | None = None
        self._now_playing_timer = QTimer(self)
        self._now_playing_timer.setInterval(native_visual_contract()["now_playing_poll_ms"])
        self._now_playing_timer.timeout.connect(self._refresh_now_playing)
        self._system_timer = QTimer(self)
        self._system_timer.setInterval(native_visual_contract()["system_poll_ms"])
        self._system_timer.timeout.connect(self._refresh_system)
        self._startup_animation: QPropertyAnimation | None = None
        self._page_animation: QPropertyAnimation | None = None
        self._page_effect: QGraphicsOpacityEffect | None = None
        self._top_logo: QLabel | None = None
        self._logo_animation: QPropertyAnimation | None = None
        self._sidebar_animations: list[QPropertyAnimation] = []

        brand = native_brand_contract()
        logo_path = Path(__file__).with_name(brand["logo_file"])
        self.setWindowTitle(brand["window_title"])
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.resize(1180, 760)
        self._apply_native_visuals()
        self._build_window()
        self._refresh_system()
        self._refresh_now_playing()
        self._refresh_notifications()
        self._now_playing_timer.start()
        self._system_timer.start()

    def _apply_native_visuals(self) -> None:
        radius = native_visual_contract()["button_radius_px"]
        sidebar_radius = native_sidebar_contract()["panel_radius_px"]
        palette = self._native_palette
        self.setStyleSheet(
            f"QMainWindow, QWidget#netopsRoot, QWidget#netopsPage {{ background: {palette['bg']}; color: {palette['text_main']}; }}"
            f"QPushButton {{ background: {palette['button_fg']}; color: {palette['button_text']}; border: 1px solid {palette['entry_border']}; border-radius: {radius}px; padding: 5px 10px; min-height: 24px; }}"
            f"QPushButton:hover {{ background: {palette['button_hover']}; border-color: {palette['accent']}; }}"
            f"QPushButton:pressed {{ background: {palette['accent']}; color: {palette['accent_text']}; border: 2px solid {palette['accent_hover']}; padding-top: 6px; }}"
            f"QWidget#netopsSidebar {{ background: {palette['sidebar']}; border: 1px solid {palette['entry_border']}; border-radius: {sidebar_radius}px; }}"
            f"QLabel#nowPlayingIsland {{ background: {palette['card']}; color: {palette['text_main']}; border: 1px solid {palette['entry_border']}; border-radius: 15px; padding: 6px 14px; }}"
            f"QGroupBox {{ background: {palette['card']}; color: {palette['text_main']}; border: 1px solid {palette['entry_border']}; border-radius: 10px; margin-top: 10px; padding: 12px 8px 8px; }}"
            f"QGroupBox::title {{ color: {palette['text_dim']}; subcontrol-origin: margin; left: 10px; padding: 0 4px; }}"
            f"QPlainTextEdit, QLineEdit, QComboBox, QListWidget, QTableWidget {{ background: {palette['entry_bg']}; color: {palette['text_main']}; border: 1px solid {palette['entry_border']}; border-radius: 8px; padding: 6px; selection-background-color: {palette['accent']}; selection-color: {palette['accent_text']}; }}"
            f"QTabWidget::pane {{ background: {palette['bg']}; border: 1px solid {palette['entry_border']}; border-radius: 8px; top: -1px; }}"
            f"QTabBar {{ background: transparent; }}"
            f"QTabBar::tab {{ background: transparent; color: {palette['text_dim']}; border: 1px solid transparent; border-radius: 7px; padding: 9px 14px; min-height: 34px; margin-right: 4px; }}"
            f"QTabBar::tab:hover {{ background: {palette['button_hover']}; color: {palette['text_main']}; border-color: {palette['entry_border']}; }}"
            f"QTabBar::tab:selected {{ background: {palette['accent']}; color: {palette['accent_text']}; border-color: {palette['accent']}; font-weight: 600; }}"
            f"QTabBar::tab:focus {{ outline: none; border-color: {palette['accent_hover']}; }}"
            f"QCheckBox {{ color: {palette['text_main']}; spacing: 8px; }}"
            f"QCheckBox::indicator {{ width: 16px; height: 16px; background: {palette['entry_bg']}; border: 1px solid {palette['entry_border']}; border-radius: 4px; }}"
            f"QCheckBox::indicator:hover {{ border-color: {palette['accent']}; }}"
            f"QCheckBox::indicator:checked {{ background: {palette['accent']}; border-color: {palette['accent']}; }}"
            f"QAbstractItemView::item:selected {{ background: {palette['accent']}; color: {palette['accent_text']}; }}"
            f"QComboBox QAbstractItemView {{ background: {palette['entry_bg']}; color: {palette['text_main']}; selection-background-color: {palette['accent']}; selection-color: {palette['accent_text']}; }}"
            f"QSlider::groove:horizontal {{ background: {palette['entry_border']}; height: 4px; border-radius: 2px; }}"
            f"QSlider::handle:horizontal {{ background: {palette['accent']}; width: 14px; margin: -5px 0; border-radius: 7px; }}"
            f"QScrollBar:vertical {{ background: {palette['entry_bg']}; width: 10px; margin: 0; }}"
            f"QScrollBar::handle:vertical {{ background: {palette['entry_border']}; border-radius: 5px; min-height: 24px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {palette['accent']}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
            f"QProgressBar {{ background: {palette['entry_bg']}; color: {palette['text_main']}; border: 1px solid {palette['entry_border']}; border-radius: 7px; text-align: center; }}"
            f"QProgressBar::chunk {{ background: {palette['accent']}; border-radius: 6px; }}"
            f"QPlainTextEdit#chatOutput {{ background: {palette['entry_bg']}; color: {palette['text_main']}; border: 1px solid {palette['entry_border']}; border-radius: 16px; padding: 12px; }}"
            f"QFrame#chatComposer {{ background: {palette['entry_bg']}; border: 1px solid {palette['accent']}; border-radius: 18px; padding: 4px; }}"
            f"QLineEdit#chatComposerInput {{ background: transparent; color: {palette['text_main']}; border: none; padding: 8px 10px; min-height: 30px; }}"
            f"QPushButton#chatModeButton {{ background: transparent; border: none; color: {palette['text_dim']}; min-height: 30px; padding: 4px 10px; }}"
            f"QPushButton#chatModeButton:hover {{ color: {palette['accent']}; border: none; }}"
            f"QPushButton#chatSendButton {{ background: {palette['accent']}; color: {palette['accent_text']}; border: none; border-radius: 14px; min-height: 32px; padding: 5px 16px; font-weight: 700; }}"
            f"QPushButton#chatSendButton:hover {{ background: {palette['accent_hover']}; border: none; }}"
        )

    def _build_window(self) -> None:
        root = QWidget()
        root.setObjectName("netopsRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)

        status_bar = QHBoxLayout()
        top_routes = {
            "SİSTEM": "system",
            "REMOTE": "remote",
            "BİLDİRİMLER": "notifications",
            "NOW PLAYING": "now_playing",
        }
        def add_top_button(label: str) -> None:
            button = QPushButton(f"•  {label}")
            button.setFlat(True)
            button.clicked.connect(lambda _checked=False, route=top_routes[label]: self._open_native_page(route))
            self._top_status_buttons[label] = button
            status_bar.addWidget(button)

        top_status = native_legacy_layout_contract()["top_status"]
        for label in top_status[:-1]:
            add_top_button(label)
        status_bar.addStretch(1)
        add_top_button(top_status[-1])
        self._now_playing_island.setObjectName("nowPlayingIsland")
        self._now_playing_island.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._now_playing_island.setMinimumSize(380, 42)
        self._now_playing_island.setToolTip("Now Playing durumu")
        layout.addLayout(status_bar)

        body = QHBoxLayout()
        body.addWidget(self._build_sidebar())

        for key, _label in _PAGES:
            page = getattr(self, f"_build_{key}_page")()
            self._pages[key] = page
            self._page_stack.addWidget(page)
        body.addWidget(self._page_stack, 1)
        layout.addLayout(body, 1)
        self.setCentralWidget(root)
        self._buttons_with_feedback = root.findChildren(QPushButton)
        for button in self._buttons_with_feedback:
            button.clicked.connect(lambda _checked=False, target=button: self._animate_button_feedback(target))
        self._start_intro_animations()
        self._open_native_page("chat")
        self.statusBar().hide()

    def _start_intro_animations(self) -> None:
        if os.environ.get("NETOPS_REDUCE_MOTION") == "1":
            return

        if self._top_logo is not None:
            effect = QGraphicsOpacityEffect(self._top_logo)
            effect.setOpacity(0.15)
            self._top_logo.setGraphicsEffect(effect)
            animation = QPropertyAnimation(effect, b"opacity", self)
            animation.setDuration(native_animation_contract()["logo_fade_ms"])
            animation.setStartValue(0.15)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            self._logo_animation = animation

        self._sidebar_animations = []
        stagger = native_animation_contract()["sidebar_stagger_ms"]
        for index, button in enumerate(self._nav_buttons.values()):
            QTimer.singleShot(index * stagger, lambda target=button: self._animate_sidebar_button_in(target))

    def _animate_sidebar_button_in(self, button: QPushButton) -> None:
        if not button or os.environ.get("NETOPS_REDUCE_MOTION") == "1":
            return
        effect = QGraphicsOpacityEffect(button)
        effect.setOpacity(0.0)
        button.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(native_motion_contract()["page_ms"])
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._sidebar_animations.append(animation)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("netopsSidebar")
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(290)
        layout = QVBoxLayout(sidebar)
        chat_button = QPushButton("＋  Komut konsolu")
        chat_button.setIcon(self._sidebar_icon("chat"))
        chat_button.clicked.connect(lambda: self._open_native_page("chat"))
        layout.addWidget(chat_button)
        layout.addWidget(QLabel("ÇALIŞMA ALANI"))

        labels = native_legacy_layout_contract()["sidebar"]
        routes = ("chat", "devices", "now_playing", "automations", "remote")
        for key, label in zip(routes, labels[:-1]):
            button = QPushButton(label)
            button.setIcon(self._sidebar_icon(key))
            button.clicked.connect(lambda _checked=False, route=key: self._open_native_page(route))
            self._nav_buttons[key] = button
            layout.addWidget(button)

        layout.addWidget(QLabel("SİSTEM DURUMU"))
        for key in ("cpu", "ram", "gpu"):
            metric = QGroupBox(key.upper())
            metric_layout = QHBoxLayout(metric)
            value = QLabel("Ölçülüyor")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._system_values.setdefault(key, []).append(value)
            metric_layout.addWidget(QLabel("Kullanım"))
            metric_layout.addStretch(1)
            metric_layout.addWidget(value)
            layout.addWidget(metric)
        layout.addStretch(1)

        settings = QPushButton(labels[-1])
        settings.setIcon(self._sidebar_icon("settings"))
        settings.clicked.connect(lambda: self._open_native_page("settings"))
        self._nav_buttons["settings"] = settings
        layout.addWidget(settings)
        return sidebar

    def _sidebar_icon(self, route: str):
        icons = {
            "chat": QStyle.StandardPixmap.SP_MessageBoxInformation,
            "devices": QStyle.StandardPixmap.SP_ComputerIcon,
            "now_playing": QStyle.StandardPixmap.SP_MediaPlay,
            "automations": QStyle.StandardPixmap.SP_BrowserReload,
            "system": QStyle.StandardPixmap.SP_FileDialogInfoView,
            "settings": QStyle.StandardPixmap.SP_FileDialogDetailedView,
        }
        return self.style().standardIcon(icons.get(route, QStyle.StandardPixmap.SP_FileDialogInfoView))

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("netopsPage")
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(title))
        layout.addWidget(QLabel(subtitle))
        return page, layout

    def _build_chat_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("netopsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 28, 38, 18)
        logo = QLabel()
        logo_path = str(Path(__file__).with_name("Logo.png"))
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(170, 170, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo.setText("▲")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("Sana nasıl yardımcı olabilirim?")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel("NETOPS  /  OPERATÖR MERKEZİ")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        welcome = QLabel("Merhaba! Ben NetOps. Sana nasıl yardımcı olabilirim?")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)

        self._chat_output.setReadOnly(True)
        self._chat_output.setObjectName("chatOutput")
        layout.addWidget(self._chat_output, 1)

        composer = QFrame()
        composer.setObjectName("chatComposer")
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(8, 5, 8, 5)
        composer_layout.setSpacing(6)

        self._chat_input.setPlaceholderText("Mesajını yaz...")
        self._chat_input.setObjectName("chatComposerInput")
        self._chat_input.setMinimumHeight(34)
        self._chat_input.returnPressed.connect(self._submit_chat)
        send = QPushButton("Gönder  →")
        send.setObjectName("chatSendButton")
        send.setToolTip("Mesajı gönder")
        send.clicked.connect(self._submit_chat)
        composer_layout.addWidget(self._chat_input, 1)
        composer_layout.addWidget(send)
        self._chat_composer = composer
        self._chat_send_button = send
        layout.addWidget(composer)
        return page

    def _build_devices_page(self) -> QWidget:
        page, layout = self._page("Cihazlar", "Bağlı cihazları ve Remote durumunu izle.")
        self._devices_table.setColumnCount(3)
        self._devices_table.setHorizontalHeaderLabels(("Cihaz", "Durum", "Adres"))
        self._devices_table.setAlternatingRowColors(True)
        layout.addWidget(self._devices_table, 1)
        refresh = QPushButton("Cihazları yenile")
        refresh.clicked.connect(self._refresh_devices)
        layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def _build_now_playing_page(self) -> QWidget:
        page, layout = self._page("Now Playing", "Aktif medya oturumunu görüntüle.")
        self._now_playing_cover.setMinimumSize(180, 180)
        self._now_playing_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._now_playing_cover.setText("Kapak bekleniyor")
        layout.addWidget(self._now_playing_cover, alignment=Qt.AlignmentFlag.AlignCenter)
        box = QGroupBox("Şu an çalıyor")
        form = QFormLayout(box)
        for key, label in (
            ("title", "Parça"),
            ("artist", "Sanatçı"),
            ("app", "Kaynak"),
            ("playback_status", "Durum"),
        ):
            value = QLabel("Bekleniyor")
            self._now_playing_values[key] = value
            form.addRow(label, value)
        layout.addWidget(box)
        controls = QHBoxLayout()
        for action, text in (("previous", "Önceki"), ("play_pause", "Oynat / Duraklat"), ("next", "Sonraki")):
            button = QPushButton(text)
            button.clicked.connect(lambda _checked=False, value=action: self._media_action(value))
            controls.addWidget(button)
        layout.addLayout(controls)
        volume_row = QHBoxLayout()
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(50)
        self._volume_slider.setToolTip("Bilgisayar ses seviyesi")
        self._volume_slider.sliderReleased.connect(self._set_volume)
        self._mute_button.clicked.connect(self._toggle_mute)
        volume_row.addWidget(self._volume_label)
        volume_row.addWidget(self._volume_slider, 1)
        volume_row.addWidget(self._mute_button)
        layout.addLayout(volume_row)
        refresh = QPushButton("Medya bilgisini yenile")
        refresh.clicked.connect(self._refresh_now_playing)
        layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
        fullscreen = QPushButton("Tam ekran Now Playing")
        fullscreen.clicked.connect(self._open_now_playing_fullscreen)
        layout.addWidget(fullscreen, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _build_automations_page(self) -> QWidget:
        page, layout = self._page("Otomasyonlar", "Zamanlayıcıları ve çalışma akışlarını görüntüle.")
        self._automations_table.setColumnCount(3)
        self._automations_table.setHorizontalHeaderLabels(("Ad", "Aktif", "Tetikleyici"))
        self._automations_table.setAlternatingRowColors(True)
        layout.addWidget(self._automations_table, 1)
        refresh = QPushButton("Otomasyonları yenile")
        refresh.clicked.connect(self._refresh_automations)
        layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def _build_remote_page(self) -> QWidget:
        page, layout = self._page("Remote", "Bağlı telefon ve Termux cihazlarına güvenli komut gönder.")
        self._remote_output.setReadOnly(True)
        self._remote_output.setPlaceholderText("Remote sonuçları burada görünecek.")
        layout.addWidget(self._remote_output, 1)
        controls = QHBoxLayout()
        self._remote_input.setPlaceholderText("Örnek: telefondaki durumu söyle")
        self._remote_input.returnPressed.connect(self._submit_remote)
        send = QPushButton("Gönder")
        send.clicked.connect(self._submit_remote)
        controls.addWidget(self._remote_input, 1)
        controls.addWidget(send)
        layout.addLayout(controls)
        hint = QLabel("Cihaz bağlı değilse komut gönderilmez; sonuç bu alanda raporlanır.")
        layout.addWidget(hint)
        return page

    def _build_notifications_page(self) -> QWidget:
        page, layout = self._page("Bildirimler", "NetOps, telefon ve komut olaylarının canlı akışı.")
        layout.addWidget(self._notifications_list, 1)
        refresh = QPushButton("Bildirimleri yenile")
        refresh.clicked.connect(self._refresh_notifications)
        layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def _build_system_page(self) -> QWidget:
        page, layout = self._page("Sistem Durumu", "NetOps servisleri ve bilgisayar kaynakları.")
        box = QGroupBox("Durum")
        grid = QGridLayout(box)
        for row, key in enumerate(("cpu", "ram", "gpu", "devices", "remote")):
            value = QLabel("Ölçülüyor")
            self._system_values.setdefault(key, []).append(value)
            grid.addWidget(QLabel(key.upper()), row, 0)
            grid.addWidget(value, row, 1)
        layout.addWidget(box)
        refresh = QPushButton("Durumu yenile")
        refresh.clicked.connect(self._refresh_system)
        layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _build_settings_page(self) -> QWidget:
        page, layout = self._page("Ayarlar", "Native NetOps arayüzünün davranışlarını yönet.")
        self._settings_tabs = QTabWidget()
        self._settings_tabs.setObjectName("settingsTabs")
        self._settings_tabs.setDocumentMode(True)
        self._settings_tabs.setUsesScrollButtons(False)
        self._settings_tabs.setMovable(False)
        self._settings_tabs.tabBar().setExpanding(False)
        self._settings_tabs.tabBar().setMinimumHeight(42)
        builders = (
            self._settings_general_tab,
            self._settings_system_tab,
            self._settings_appearance_tab,
            self._settings_window_tab,
            self._settings_netolab_tab,
            self._settings_security_tab,
            self._settings_updates_tab,
            self._settings_about_tab,
        )
        for title, builder in zip(native_settings_sections(), builders):
            self._settings_tabs.addTab(builder(), title)
        layout.addWidget(self._settings_tabs, 1)
        actions = QHBoxLayout()
        apply_button = QPushButton("Ayarları kaydet")
        status = QLabel("Hazır")
        apply_button.clicked.connect(lambda: self._save_settings(status))
        actions.addWidget(apply_button)
        actions.addWidget(status)
        actions.addStretch(1)
        layout.addLayout(actions)
        return page

    def _setting_checkbox(self, parent: QWidget, key: str, text: str, default: bool = False) -> QCheckBox:
        control = QCheckBox(text, parent)
        control.setChecked(bool(self._settings_data.get(key, default)))
        self._settings_controls[key] = control
        return control

    def _setting_combo(self, parent: QWidget, key: str, values: tuple[tuple[str, Any], ...], default: Any) -> QComboBox:
        control = QComboBox(parent)
        for label, value in values:
            control.addItem(label, value)
        current = self._settings_data.get(key, default)
        index = control.findData(current)
        control.setCurrentIndex(index if index >= 0 else 0)
        self._settings_controls[key] = control
        return control

    def _settings_tab(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(title))
        layout.addWidget(QLabel(description))
        return page, layout

    def _settings_general_tab(self) -> QWidget:
        page, layout = self._settings_tab("Genel", "Dil ve temel NetOps davranışları.")
        layout.addWidget(QLabel("Uygulama dili"))
        layout.addWidget(self._setting_combo(page, "dil", (("Türkçe", "tr"), ("English", "en")), "tr"))
        layout.addWidget(self._setting_checkbox(page, "live_mode_otomatik_baslat", "Live Mode'u açılışta başlat"))
        layout.addWidget(self._setting_checkbox(page, "ogrenme_modu_acik", "Yerel öğrenme modunu etkinleştir"))
        layout.addWidget(self._setting_checkbox(page, "local_api_enabled", "Yerel API erişimine izin ver", True))
        layout.addStretch(1)
        return page

    def _settings_system_tab(self) -> QWidget:
        page, layout = self._settings_tab("Sistem", "Kaynak izleme ve arka plan servisleri.")
        layout.addWidget(QLabel("CPU/RAM ve servis durumu Sistem Durumu sekmesinden izlenir."))
        layout.addWidget(self._setting_checkbox(page, "background_services_enabled", "Arka plan servislerini etkinleştir", True))
        refresh = QPushButton("Sistem durumunu yenile")
        refresh.clicked.connect(self._refresh_system)
        layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _settings_appearance_tab(self) -> QWidget:
        page, layout = self._settings_tab("Görünüm", "Tema, açılış animasyonu ve ses tercihleri.")
        layout.addWidget(QLabel("Tema"))
        layout.addWidget(self._setting_combo(page, "tema", (("Koyu", "dark"), ("Açık", "light")), "dark"))
        layout.addWidget(QLabel("Renk teması"))
        layout.addWidget(
            self._setting_combo(
                page,
                "renk_temasi",
                (("Yeşil", "green"), ("Mavi", "blue"), ("Koyu mavi", "dark-blue")),
                "blue",
            )
        )
        layout.addWidget(self._setting_checkbox(page, "startup_animation_enabled", "Açılış animasyonunu etkinleştir", True))
        layout.addWidget(self._setting_checkbox(page, "startup_sound_enabled", "Açılış sesini etkinleştir", True))
        gif_button = QPushButton("Açılış GIF'i seç")
        gif_button.clicked.connect(lambda: self._choose_setting_file("secilen_gif", "GIF (*.gif)"))
        sound_button = QPushButton("Açılış sesini seç")
        sound_button.clicked.connect(lambda: self._choose_setting_file("secilen_ses", "Ses (*.mp3 *.wav)"))
        layout.addWidget(gif_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(sound_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return page

    def _settings_window_tab(self) -> QWidget:
        page, layout = self._settings_tab("Pencere Yöneticisi", "Native NetOps penceresinin açılış davranışı.")
        layout.addWidget(self._setting_checkbox(page, "netops_native_maximized", "Açılışta pencereyi büyüt", True))
        layout.addWidget(self._setting_checkbox(page, "now_playing_on_start", "Now Playing durumunu açılışta izle"))
        layout.addStretch(1)
        return page

    def _settings_netolab_tab(self) -> QWidget:
        page, layout = self._settings_tab("Netolab", "Yerel eklenti ve beceri altyapısı.")
        layout.addWidget(self._setting_checkbox(page, "netolab_enabled", "Yerel Netolab bileşenlerini etkinleştir", True))
        layout.addWidget(QLabel("Eklentiler kullanıcı onayı olmadan çalıştırılmaz."))
        layout.addStretch(1)
        return page

    def _settings_security_tab(self) -> QWidget:
        page, layout = self._settings_tab("Güvenlik", "Onaylar ve yerel erişim seçenekleri.")
        layout.addWidget(self._setting_checkbox(page, "risk_confirmation_required", "Riskli işlemlerde onay iste", True))
        layout.addWidget(self._setting_checkbox(page, "local_api_enabled", "Yerel API erişimine izin ver", True))
        layout.addStretch(1)
        return page

    def _settings_updates_tab(self) -> QWidget:
        page, layout = self._settings_tab("Güncellemeler", "NetOps sürüm ve güncelleme tercihleri.")
        layout.addWidget(self._setting_checkbox(page, "auto_update_check", "Açılışta güncellemeleri kontrol et"))
        status = QLabel("Henüz kontrol edilmedi")
        check = QPushButton("Güncellemeleri kontrol et")
        check.clicked.connect(lambda: status.setText("Kontrol isteği hazırlandı"))
        layout.addWidget(check, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(status)
        layout.addStretch(1)
        return page

    def _settings_about_tab(self) -> QWidget:
        page, layout = self._settings_tab("Hakkında", "NetOps native masaüstü arayüzü.")
        layout.addWidget(QLabel("NetOps v1.52"))
        layout.addWidget(QLabel("PySide6 Qt Widgets tabanı"))
        layout.addWidget(QLabel(str(Path(__file__).resolve().parent)))
        layout.addStretch(1)
        return page

    def _choose_setting_file(self, key: str, pattern: str) -> None:
        path, _selected = QFileDialog.getOpenFileName(self, "Dosya seç", "", pattern)
        if path:
            self._settings_data[key] = path

    def _save_settings(self, status: QLabel) -> None:
        for key, control in self._settings_controls.items():
            if isinstance(control, QCheckBox):
                self._settings_data[key] = control.isChecked()
            elif isinstance(control, QComboBox):
                self._settings_data[key] = control.currentData()
        result = self.backend.run("save_settings", self._settings_data)
        failed = isinstance(result, dict) and result.get("ok") is False
        if not failed:
            self._native_palette = native_theme_palette(self._settings_data)
            self._apply_native_visuals()
        status.setText("Ayarlar kaydedildi" if not failed else _display(result))

    def _apply_settings(self, maximized: bool, reduce_motion: bool, status: QLabel) -> None:
        if reduce_motion:
            os.environ["NETOPS_REDUCE_MOTION"] = "1"
        else:
            os.environ.pop("NETOPS_REDUCE_MOTION", None)
        if maximized:
            self.showMaximized()
        else:
            self.showNormal()
        status.setText("Ayarlar uygulandı")

    def _animate_button_feedback(self, button: QPushButton) -> None:
        if os.environ.get("NETOPS_REDUCE_MOTION") == "1":
            return
        effect = button.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(button)
            button.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(native_visual_contract()["button_feedback_ms"])
        animation.setStartValue(0.72)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._button_feedback_animations[id(button)] = animation

    def _submit_chat(self) -> None:
        text = self._chat_input.text().strip()
        if not text:
            return
        result = self.backend.run("chat", text)
        reply = _display(result)
        self._chat_output.appendPlainText(f"Sen: {text}\nNetOps: {reply}\n")
        self._chat_input.clear()
        # Text must remain available even when the optional local TTS is absent.
        # Run speech outside the Qt event loop so a voice model never freezes UI.
        if not (isinstance(result, dict) and result.get("error")) and reply:
            threading.Thread(
                target=lambda: self.backend.run("speech", reply),
                daemon=True,
                name="netops-chat-speech",
            ).start()

    def _open_native_page(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        if self._page_stack.currentWidget() is page:
            if key == "now_playing":
                self._refresh_volume()
            return
        self._page_stack.setCurrentWidget(page)
        if key == "now_playing":
            self._refresh_volume()
        for route, button in self._nav_buttons.items():
            button.setChecked(route == key)
        if os.environ.get("NETOPS_REDUCE_MOTION") == "1":
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        self._page_effect = effect
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(int(native_motion_contract()["page_ms"]))
        animation.setStartValue(0.82)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._page_animation = animation

    def _submit_remote(self) -> None:
        text = self._remote_input.text().strip()
        if not text:
            return
        result = self.backend.run("remote", text)
        self._remote_output.appendPlainText(f"> {text}\n{_display(result)}\n")
        self._remote_input.clear()

    def _refresh_notifications(self) -> None:
        result = self.backend.run("notifications")
        events = result if isinstance(result, list) else []
        self._notifications_list.clear()
        if not events:
            self._notifications_list.addItem("Yeni bildirim yok.")
            return
        for event in reversed(events[-50:]):
            event = event if isinstance(event, dict) else {}
            timestamp = str(event.get("at", ""))
            source = str(event.get("source", "NetOps"))
            message = str(event.get("message", event.get("detail", "")))
            command = str(event.get("command", event.get("title", "Olay")))
            self._notifications_list.addItem(f"[{timestamp}] {source} • {command}\n{message}")

    def _refresh_system(self) -> None:
        snapshot = self.backend.snapshot()
        for key, labels in self._system_values.items():
            for label in labels:
                label.setText(str(snapshot.get(key, "Bilinmiyor")))
        self._status.setText("Hazır" if not snapshot.get("error") else "Servis hatası")

    def _refresh_devices(self) -> None:
        result = self.backend.run("devices")
        devices = result.get("devices", []) if isinstance(result, dict) else result
        devices = devices if isinstance(devices, list) else []
        self._devices_table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            device = device if isinstance(device, dict) else {}
            self._devices_table.setItem(row, 0, QTableWidgetItem(str(device.get("display_name", device.get("device_id", "Bilinmiyor")))))
            self._devices_table.setItem(row, 1, QTableWidgetItem("Çevrimiçi" if device.get("online") else "Çevrimdışı"))
            self._devices_table.setItem(row, 2, QTableWidgetItem(str(device.get("ip", ""))))

    def _refresh_now_playing(self) -> None:
        result = self.backend.run("now_playing")
        result = result if isinstance(result, dict) else {}
        title = str(result.get("title", "Müzik bekleniyor") or "Müzik bekleniyor")
        for key, label in self._now_playing_values.items():
            label.setText(str(result.get(key, "Bekleniyor") or "Bekleniyor"))
        cover_path = str(result.get("cover_path", "") or "")
        if cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                self._now_playing_cover.setPixmap(
                    pixmap.scaled(
                        220,
                        220,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self._now_playing_cover.setText("")
        else:
            self._now_playing_cover.setPixmap(QPixmap())
            self._now_playing_cover.setText("Kapak bekleniyor")
        status_button = self._top_status_buttons.get("NOW PLAYING")
        if status_button is not None:
            status_button.setText(f"•  NOW PLAYING - {title}")
        artist = str(result.get("artist", "") or "").strip()
        island_text = "♪  Müzik bekleniyor" if title == "Müzik bekleniyor" else "♪  " + " • ".join(item for item in (title, artist) if item)
        self._update_now_playing_island(island_text)

    def _update_now_playing_island(self, text: str) -> None:
        text = str(text or "♪  Müzik bekleniyor")
        if text == self._now_playing_island_text:
            return
        self._now_playing_island_text = text
        self._now_playing_island.setText(text)
        if os.environ.get("NETOPS_REDUCE_MOTION") == "1":
            return
        effect = QGraphicsOpacityEffect(self._now_playing_island)
        effect.setOpacity(0.55)
        self._now_playing_island.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(native_visual_contract()["button_feedback_ms"])
        animation.setStartValue(0.55)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._now_playing_island_animation = animation

    def _set_volume(self) -> None:
        value = self._volume_slider.value()
        result = self.backend.run("media_control", f"volume_set:{value}")
        if isinstance(result, dict) and result.get("ok") is False:
            self._volume_label.setText("Ses: ayarlanamadı")
        else:
            self._volume_label.setText(f"Ses: %{value}")

    def _refresh_volume(self) -> None:
        result = self.backend.run("media_control", "volume_get")
        if not isinstance(result, dict) or result.get("value") is None:
            self._volume_label.setText("Ses: okunamadı")
            return
        try:
            value = max(0, min(100, int(float(result["value"]))))
        except (TypeError, ValueError):
            self._volume_label.setText("Ses: okunamadı")
            return
        self._volume_slider.blockSignals(True)
        self._volume_slider.setValue(value)
        self._volume_slider.blockSignals(False)
        muted = result.get("muted") is True
        self._volume_label.setText(f"Ses: %{value}" + (" • Sessiz" if muted else ""))
        self._mute_button.setText("Sesi aç" if muted else "Sessize al")

    def _toggle_mute(self) -> None:
        result = self.backend.run("media_control", "mute_toggle")
        muted = isinstance(result, dict) and result.get("muted") is True
        self._mute_button.setText("Sesi aç" if muted else "Sessize al")

    def _open_now_playing_fullscreen(self) -> None:
        if self._now_playing_overlay is not None and self._now_playing_overlay.isVisible():
            self._now_playing_overlay.raise_()
            self._now_playing_overlay.activateWindow()
            return

        overlay = QWidget(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        overlay.setObjectName("nowPlayingOverlay")
        overlay.setStyleSheet(
            "QWidget#nowPlayingOverlay { background: #05070b; color: #f4f7fb; }"
            "QLabel#nowPlayingHeading { color: #8fb4ff; letter-spacing: 3px; }"
            "QLabel#nowPlayingOverlayTitle { color: #ffffff; }"
            "QLabel#nowPlayingOverlayMeta { color: #aeb8c8; }"
            "QLabel#nowPlayingOverlayStatus { color: #79879d; }"
            "QLabel#nowPlayingOverlayClock { color: #ffffff; }"
            "QLabel#nowPlayingOverlayDate { color: #aeb8c8; }"
            "QProgressBar#nowPlayingOverlayProgress { background: #151b27; border: 1px solid #2d405f; border-radius: 5px; height: 8px; }"
            "QProgressBar#nowPlayingOverlayProgress::chunk { background: #6f91d9; border-radius: 5px; }"
        )
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(64, 46, 64, 34)
        layout.addStretch(1)

        heading = QLabel()
        heading.setObjectName("nowPlayingHeading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(heading)

        cover = QLabel("♪")
        cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover.setMinimumSize(260, 260)
        cover.setMaximumSize(360, 360)
        cover.setStyleSheet("font-size: 90px; color: #6f91d9; background: #101521; border-radius: 24px;")
        layout.addWidget(cover, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel()
        title.setObjectName("nowPlayingOverlayTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 34px; font-weight: 700;")
        layout.addWidget(title)

        detail = QLabel()
        detail.setObjectName("nowPlayingOverlayMeta")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setStyleSheet("font-size: 17px;")
        layout.addWidget(detail)

        album = QLabel("Albüm: bekleniyor")
        album.setObjectName("nowPlayingOverlayMeta")
        album.setAlignment(Qt.AlignmentFlag.AlignCenter)
        album.setStyleSheet("font-size: 14px;")
        layout.addWidget(album)

        progress = QProgressBar()
        progress.setObjectName("nowPlayingOverlayProgress")
        progress.setRange(0, 1000)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setMaximumWidth(760)
        layout.addWidget(progress, alignment=Qt.AlignmentFlag.AlignCenter)
        timeline = QLabel("00:00 / 00:00")
        timeline.setObjectName("nowPlayingOverlayStatus")
        timeline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timeline.setStyleSheet("font-size: 13px;")
        layout.addWidget(timeline)

        status = QLabel()
        status.setObjectName("nowPlayingOverlayStatus")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet("font-size: 14px;")
        layout.addWidget(status)
        visualizer = QLabel("▂ ▄ ▆ ▃ ▅")
        visualizer.setObjectName("nowPlayingOverlayMeta")
        visualizer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        visualizer.setStyleSheet("font-size: 24px; color: #6f91d9; letter-spacing: 5px;")
        layout.addWidget(visualizer)
        layout.addStretch(1)

        footer = QHBoxLayout()
        clock = QLabel()
        clock.setObjectName("nowPlayingOverlayClock")
        clock.setStyleSheet("font-size: 26px; font-weight: 700;")
        date = QLabel()
        date.setObjectName("nowPlayingOverlayDate")
        date.setStyleSheet("font-size: 15px;")
        platform = QLabel("Platform: bekleniyor")
        platform.setObjectName("nowPlayingOverlayDate")
        platform.setStyleSheet("font-size: 15px;")
        volume_label = QLabel("Ses: okunuyor")
        volume_label.setObjectName("nowPlayingOverlayDate")
        volume_slider = QSlider(Qt.Orientation.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(50)
        volume_slider.setMinimumWidth(150)
        volume_slider.sliderReleased.connect(self._set_fullscreen_volume)
        previous = QPushButton("Önceki")
        previous.clicked.connect(lambda: self._fullscreen_media_action("previous"))
        play_pause = QPushButton("Başlat")
        play_pause.clicked.connect(lambda: self._fullscreen_media_action("play_pause"))
        mute = QPushButton("Sessize al")
        mute.clicked.connect(lambda: self._fullscreen_media_action("mute_toggle"))
        next_button = QPushButton("Sonraki")
        next_button.clicked.connect(lambda: self._fullscreen_media_action("next"))
        close = QPushButton("Now Playing'i kapat  (Esc yerine)")
        close.clicked.connect(self._close_now_playing_fullscreen)
        footer.addWidget(clock)
        footer.addWidget(date)
        footer.addWidget(platform)
        footer.addWidget(volume_label)
        footer.addWidget(volume_slider)
        footer.addWidget(previous)
        footer.addWidget(play_pause)
        footer.addWidget(mute)
        footer.addWidget(next_button)
        footer.addStretch(1)
        footer.addWidget(close)
        layout.addLayout(footer)

        self._now_playing_overlay = overlay
        self._now_playing_overlay_values = {
            "heading": heading,
            "title": title,
            "detail": detail,
            "album": album,
            "timeline": timeline,
            "status": status,
            "clock": clock,
            "date": date,
        }
        self._now_playing_overlay_cover = cover
        self._now_playing_overlay_platform = platform
        self._now_playing_overlay_album = album
        self._now_playing_overlay_timeline = timeline
        self._now_playing_overlay_progress = progress
        self._now_playing_overlay_volume_label = volume_label
        self._now_playing_overlay_volume_slider = volume_slider
        self._now_playing_overlay_play_pause = play_pause
        self._now_playing_overlay_mute = mute
        self._now_playing_overlay_visualizer = visualizer
        overlay.showFullScreen()
        self._now_playing_overlay_timer.start()
        self._now_playing_visualizer_timer.start()
        self._refresh_now_playing_fullscreen()
        self._refresh_fullscreen_volume()

    def _close_now_playing_fullscreen(self) -> None:
        overlay = self._now_playing_overlay
        self._now_playing_overlay_timer.stop()
        self._now_playing_visualizer_timer.stop()
        self._now_playing_overlay = None
        self._now_playing_overlay_values = {}
        self._now_playing_overlay_cover = None
        self._now_playing_overlay_platform = None
        self._now_playing_overlay_album = None
        self._now_playing_overlay_timeline = None
        self._now_playing_overlay_progress = None
        self._now_playing_overlay_volume_label = None
        self._now_playing_overlay_volume_slider = None
        self._now_playing_overlay_play_pause = None
        self._now_playing_overlay_mute = None
        self._now_playing_overlay_visualizer = None
        if overlay is not None:
            overlay.close()
            overlay.deleteLater()

    def _refresh_now_playing_fullscreen(self) -> None:
        overlay = self._now_playing_overlay
        if overlay is None or not overlay.isVisible():
            self._now_playing_overlay_timer.stop()
            return

        result = self.backend.run("now_playing")
        result = result if isinstance(result, dict) else {}
        title = str(result.get("title", "") or "").strip()
        has_media = bool(title) and not result.get("error") and title.lower() not in {
            "müzik bekleniyor",
            "bekleniyor",
            "unknown",
        }
        values = self._now_playing_overlay_values
        now = datetime.now()
        values["clock"].setText(now.strftime("%H:%M"))
        values["date"].setText(now.strftime("%d.%m.%Y"))

        if has_media:
            artist = str(result.get("artist", "") or "").strip()
            app = str(result.get("app", result.get("source", "")) or "").strip()
            album = str(result.get("album", "") or "").strip()
            playback = str(result.get("playback_status", "Oynatılıyor") or "Oynatılıyor")
            detail = " • ".join(item for item in (artist, app) if item) or "Kaynak bilgisi yok"
            values["heading"].setText(native_now_playing_contract()["fullscreen_title"])
            values["title"].setText(title)
            values["detail"].setText(detail)
            if self._now_playing_overlay_album is not None:
                self._now_playing_overlay_album.setText(f"Albüm: {album or 'Bilinmiyor'}")
            values["status"].setText(f"Durum: {playback}")
            if self._now_playing_overlay_platform is not None:
                self._now_playing_overlay_platform.setText(f"Platform: {app or 'Bilinmiyor'}")
            if self._now_playing_overlay_play_pause is not None:
                paused = playback.casefold() in {"paused", "pause", "duraklatıldı", "durduruldu", "stopped", "stop"}
                self._now_playing_overlay_play_pause.setText("Başlat" if paused else "Durdur")
            self._update_fullscreen_timeline(result)
        else:
            values["heading"].setText(native_now_playing_contract()["standby_title"])
            values["title"].setText("Müzik bekleniyor")
            values["detail"].setText("Şu an çalan parça olduğunda bilgiler burada görünür.")
            if self._now_playing_overlay_album is not None:
                self._now_playing_overlay_album.setText("Albüm: bekleniyor")
            values["status"].setText("Now Playing hazır")
            if self._now_playing_overlay_platform is not None:
                self._now_playing_overlay_platform.setText("Platform: bekleniyor")
            if self._now_playing_overlay_play_pause is not None:
                self._now_playing_overlay_play_pause.setText("Başlat")
            self._update_fullscreen_timeline({})

        cover_path = str(result.get("cover_path", "") or "")
        cover = self._now_playing_overlay_cover
        if cover is not None and cover_path and Path(cover_path).exists():
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                cover.setPixmap(
                    pixmap.scaled(
                        300,
                        300,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                cover.setText("")
        elif cover is not None:
            cover.setPixmap(QPixmap())
            cover.setText("♪")

    def _update_fullscreen_timeline(self, result: dict[str, Any]) -> None:
        progress = self._now_playing_overlay_progress
        timeline = self._now_playing_overlay_timeline
        if progress is None or timeline is None:
            return
        try:
            position = max(0.0, float(result.get("position_seconds", 0) or 0))
            duration = max(0.0, float(result.get("duration_seconds", 0) or 0))
        except (TypeError, ValueError):
            position, duration = 0.0, 0.0
        if duration <= 0:
            progress.setValue(0)
            timeline.setText("Süre bilgisi bekleniyor")
            return
        progress.setValue(max(0, min(1000, int((position / duration) * 1000))))
        position_i = int(position)
        duration_i = int(duration)
        timeline.setText(
            f"{position_i // 60:02d}:{position_i % 60:02d} / "
            f"{duration_i // 60:02d}:{duration_i % 60:02d}"
        )

    def _refresh_fullscreen_visualizer(self) -> None:
        visualizer = self._now_playing_overlay_visualizer
        if visualizer is None or self._now_playing_overlay is None or not self._now_playing_overlay.isVisible():
            self._now_playing_visualizer_timer.stop()
            return
        if os.environ.get("NETOPS_REDUCE_MOTION") == "1":
            visualizer.setText("—")
            return
        title = self._now_playing_overlay_values.get("title")
        title_text = title.text() if title is not None else "netops"
        seed = sum(ord(char) for char in title_text) % 17
        levels = "▁▂▃▄▅▆▇█"
        phase = self._now_playing_visualizer_phase * 0.34
        bars = []
        for index in range(10):
            wave = (math.sin(phase + index * 0.72 + seed) + 1) / 2
            wave2 = (math.sin(phase * 1.7 + index * 1.18) + 1) / 2
            level = int(max(0, min(len(levels) - 1, 1 + (wave * 3.2) + (wave2 * 2.4))))
            bars.append(levels[level])
        visualizer.setText(" ".join(bars))
        self._now_playing_visualizer_phase += 1

    def _set_fullscreen_volume(self) -> None:
        slider = self._now_playing_overlay_volume_slider
        label = self._now_playing_overlay_volume_label
        if slider is None:
            return
        value = slider.value()
        result = self.backend.run("media_control", f"volume_set:{value}")
        if label is not None:
            label.setText(f"Ses: %{value}" if not (isinstance(result, dict) and result.get("ok") is False) else "Ses: ayarlanamadı")

    def _refresh_fullscreen_volume(self) -> None:
        slider = self._now_playing_overlay_volume_slider
        label = self._now_playing_overlay_volume_label
        if slider is None:
            return
        result = self.backend.run("media_control", "volume_get")
        if not isinstance(result, dict) or result.get("value") is None:
            if label is not None:
                label.setText("Ses: okunamadı")
            return
        try:
            value = max(0, min(100, int(float(result["value"]))))
        except (TypeError, ValueError):
            return
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
        if label is not None:
            label.setText(f"Ses: %{value}")
        if self._now_playing_overlay_mute is not None:
            self._now_playing_overlay_mute.setText("Sesi aç" if result.get("muted") is True else "Sessize al")

    def _fullscreen_media_action(self, action: str) -> None:
        result = self.backend.run("media_control", action)
        if action == "mute_toggle" and self._now_playing_overlay_mute is not None and isinstance(result, dict):
            self._now_playing_overlay_mute.setText("Sesi aç" if result.get("muted") is True else "Sessize al")
        QTimer.singleShot(250, self._refresh_now_playing_fullscreen)

    def _media_action(self, action: str) -> None:
        self.backend.run("media_control", action)
        QTimer.singleShot(250, self._refresh_now_playing)

    def _refresh_automations(self) -> None:
        result = self.backend.run("automations")
        rows = result if isinstance(result, list) else []
        self._automations_table.setRowCount(len(rows))
        for row, automation in enumerate(rows):
            automation = automation if isinstance(automation, dict) else {}
            values = (
                automation.get("name", "Bilinmiyor"),
                "Evet" if automation.get("enabled") else "Hayır",
                automation.get("trigger_type", "Bilinmiyor"),
            )
            for column, value in enumerate(values):
                self._automations_table.setItem(row, column, QTableWidgetItem(str(value)))


def run_native_qt_app(backend: QtBackend | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    window = NetOpsQtWindow(backend=backend)
    if native_window_contract()["start_maximized"]:
        window.showMaximized()
    else:
        window.show()
    if os.environ.get("NETOPS_REDUCE_MOTION") == "1":
        window.setWindowOpacity(1.0)
    else:
        animation = QPropertyAnimation(window, b"windowOpacity", window)
        animation.setDuration(int(native_motion_contract()["startup_ms"]))
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        window._startup_animation = animation
    return app.exec()


__all__ = [
    "NetOpsQtWindow",
    "native_animation_contract",
    "native_brand_contract",
    "native_legacy_layout_contract",
    "native_motion_contract",
    "native_now_playing_contract",
    "native_page_keys",
    "native_sidebar_contract",
    "native_sidebar_icon_contract",
    "native_visual_contract",
    "native_window_contract",
    "run_native_qt_app",
]
