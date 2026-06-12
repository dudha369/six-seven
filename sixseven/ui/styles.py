"""Dark-theme QSS stylesheet for the application."""

DARK_THEME = """
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #1a1a2e;
}

/* --- Top bar / Menu --- */
QMenuBar {
    background-color: #16213e;
    border-bottom: 1px solid #0f3460;
}
QMenuBar::item:selected {
    background-color: #0f3460;
}
QMenu {
    background-color: #16213e;
    border: 1px solid #0f3460;
}
QMenu::item:selected {
    background-color: #533483;
}

/* --- Group boxes --- */
QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #e94560;
}

/* --- Buttons --- */
QPushButton {
    background-color: #0f3460;
    border: 1px solid #533483;
    border-radius: 6px;
    padding: 6px 16px;
    min-height: 28px;
    color: #e0e0e0;
}
QPushButton:hover {
    background-color: #533483;
    border-color: #e94560;
}
QPushButton:pressed {
    background-color: #e94560;
}
QPushButton:disabled {
    background-color: #2a2a3e;
    color: #666;
    border-color: #333;
}
QPushButton#btnStart {
    background-color: #1b998b;
    font-weight: bold;
    font-size: 14px;
}
QPushButton#btnStart:hover {
    background-color: #25b09b;
}
QPushButton#btnStop {
    background-color: #e94560;
    font-weight: bold;
    font-size: 14px;
}
QPushButton#btnStop:hover {
    background-color: #ff5c78;
}

/* --- Sliders --- */
QSlider::groove:horizontal {
    height: 6px;
    background: #0f3460;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #e94560;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #533483;
    border-radius: 3px;
}

/* --- Combo boxes --- */
QComboBox {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 26px;
}
QComboBox:hover {
    border-color: #533483;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #0f3460;
    selection-background-color: #533483;
}

/* --- Check boxes --- */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #0f3460;
    background: #16213e;
}
QCheckBox::indicator:checked {
    background: #e94560;
    border-color: #e94560;
}

/* --- Labels --- */
QLabel#statusLabel {
    font-size: 14px;
    font-weight: bold;
    padding: 4px 8px;
    border-radius: 4px;
}

QLabel#previewLabel {
    background-color: #0d0d1a;
    border: 2px solid #0f3460;
    border-radius: 8px;
}

/* --- Spin boxes --- */
QSpinBox, QDoubleSpinBox {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 2px 6px;
    min-height: 26px;
}

/* --- Scroll area --- */
QScrollArea {
    border: none;
}

/* --- Tooltips --- */
QToolTip {
    background-color: #16213e;
    border: 1px solid #533483;
    color: #e0e0e0;
    padding: 4px;
    border-radius: 4px;
}
"""
