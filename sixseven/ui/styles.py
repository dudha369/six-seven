"""Modern dark-theme QSS stylesheet for the application."""

DARK_THEME = """
/* ── Base ── */
QWidget {
    background-color: #0f0f17;
    color: #d0d0d8;
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0f0f17;
}

/* ── Scroll Area (settings panel) ── */
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: #141420;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2a2a40;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Group boxes ── */
QGroupBox {
    border: 1px solid #1e1e30;
    border-radius: 10px;
    margin-top: 14px;
    padding: 18px 12px 10px 12px;
    font-weight: 600;
    font-size: 12px;
    background-color: #14141f;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #7c5cff;
    font-size: 12px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── Buttons ── */
QPushButton {
    background-color: #1e1e30;
    border: 1px solid #2a2a44;
    border-radius: 8px;
    padding: 7px 18px;
    min-height: 30px;
    color: #c0c0cc;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #282848;
    border-color: #7c5cff;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #7c5cff;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #12121c;
    color: #444;
    border-color: #1a1a28;
}

QPushButton#btnStart {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #22c997, stop:1 #1baa80);
    border: none;
    color: #ffffff;
    font-weight: 700;
    font-size: 14px;
    border-radius: 10px;
    min-height: 36px;
}
QPushButton#btnStart:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ddba8, stop:1 #22c997);
}
QPushButton#btnStart:disabled {
    background: #1a1a28;
    color: #444;
}

QPushButton#btnStop {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #e94560, stop:1 #d63651);
    border: none;
    color: #ffffff;
    font-weight: 700;
    font-size: 14px;
    border-radius: 10px;
    min-height: 36px;
}
QPushButton#btnStop:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff5c78, stop:1 #e94560);
}
QPushButton#btnStop:disabled {
    background: #1a1a28;
    color: #444;
}

QPushButton#btnBrowse {
    padding: 4px 12px;
    min-height: 24px;
    font-size: 11px;
    border-radius: 6px;
}

/* ── Combo boxes ── */
QComboBox {
    background-color: #1a1a28;
    border: 1px solid #252540;
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 28px;
    color: #c0c0cc;
}
QComboBox:hover {
    border-color: #7c5cff;
}
QComboBox:focus {
    border-color: #7c5cff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1a1a28;
    border: 1px solid #252540;
    selection-background-color: #7c5cff;
    selection-color: #ffffff;
    border-radius: 6px;
    padding: 4px;
}

/* ── Check boxes ── */
QCheckBox {
    spacing: 8px;
    color: #b0b0bc;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #2a2a44;
    background: #1a1a28;
}
QCheckBox::indicator:hover {
    border-color: #7c5cff;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #7c5cff, stop:1 #a855f7);
    border-color: #7c5cff;
}

/* ── Labels ── */
QLabel {
    color: #888898;
    font-size: 12px;
}
QLabel#statusLabel {
    font-size: 15px;
    font-weight: 700;
    padding: 6px 10px;
    border-radius: 8px;
    letter-spacing: 0.5px;
}
QLabel#previewLabel {
    background-color: #08080e;
    border: 1px solid #1a1a2e;
    border-radius: 12px;
}
QLabel#settingsTitle {
    font-size: 11px;
    font-weight: 600;
    color: #555568;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QLabel#soundLabel {
    color: #7c5cff;
    font-weight: 500;
    font-size: 12px;
}

/* ── Spin boxes ── */
QSpinBox, QDoubleSpinBox {
    background-color: #1a1a28;
    border: 1px solid #252540;
    border-radius: 8px;
    padding: 3px 8px;
    min-height: 28px;
    color: #c0c0cc;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #7c5cff;
}
QSpinBox::up-button, QDoubleSpinBox::up-button {
    border: none;
    background: transparent;
    width: 18px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    border: none;
    background: transparent;
    width: 18px;
}

/* ── Tooltips ── */
QToolTip {
    background-color: #1e1e30;
    border: 1px solid #7c5cff;
    color: #d0d0d8;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

/* ── Separator ── */
QFrame#separator {
    background-color: #1e1e30;
    max-height: 1px;
}
"""
