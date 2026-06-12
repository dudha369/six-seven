"""Application entry point — QApplication, system tray, and main window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from sixseven.config import AppConfig
from sixseven.ui.main_window import MainWindow
from sixseven.ui.styles import DARK_THEME


def _generate_icon() -> QIcon:
    """Create a simple '67' icon programmatically (no external file needed)."""
    size = 64
    pix = QPixmap(QSize(size, size))
    pix.fill(QColor("#1a1a2e"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    # Circle
    painter.setBrush(QColor("#e94560"))
    painter.setPen(QColor("#e94560"))
    painter.drawEllipse(4, 4, size - 8, size - 8)
    # Text
    painter.setPen(QColor("#ffffff"))
    font = QFont("Arial", 22, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pix.rect(), 0x0084, "67")  # AlignCenter
    painter.end()
    return QIcon(pix)


def run() -> None:
    """Launch the SixSeven application."""
    app = QApplication(sys.argv)
    app.setApplicationName("SixSeven")
    app.setOrganizationName("SixSeven")
    app.setQuitOnLastWindowClosed(False)  # keep running in tray
    app.setStyleSheet(DARK_THEME)

    icon = _generate_icon()
    app.setWindowIcon(icon)

    config = AppConfig.load()
    window = MainWindow(config)

    # --- System tray ---
    tray = QSystemTrayIcon(icon, app)
    menu = QMenu()

    action_show = QAction("Show window")
    action_show.triggered.connect(window.show)
    menu.addAction(action_show)

    action_hide = QAction("Hide to tray")
    action_hide.triggered.connect(window.hide)
    menu.addAction(action_hide)

    menu.addSeparator()

    action_quit = QAction("Quit")
    action_quit.triggered.connect(app.quit)
    menu.addAction(action_quit)

    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: _on_tray_activated(reason, window))
    tray.setToolTip("SixSeven — gesture detection")
    tray.show()

    if config.start_minimized:
        tray.showMessage("SixSeven", "Running in system tray", QSystemTrayIcon.Information, 2000)
    else:
        window.show()

    sys.exit(app.exec())


def _on_tray_activated(
    reason: QSystemTrayIcon.ActivationReason,
    window: MainWindow,
) -> None:
    if reason == QSystemTrayIcon.ActivationReason.Trigger:  # single click
        if window.isVisible():
            window.hide()
        else:
            window.showNormal()
            window.raise_()
            window.activateWindow()
