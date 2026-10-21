"""
PLAYFy TV Windows 11 Fluent Dark Theme Stylesheet
"""

DARK_THEME = """
QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #121212;
    color: #F0F0F0;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #181818;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #555555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Sidebar navigation */
QFrame#sidebar {
    background-color: #1A1A1A;
    border-right: 1px solid #282828;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #B3B3B3;
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
}

QPushButton.nav-btn:hover {
    background-color: #282828;
    color: #FFFFFF;
}

QPushButton.nav-btn:checked {
    background-color: #0078D4;
    color: #FFFFFF;
    font-weight: bold;
}

/* Primary buttons */
QPushButton.primary-btn {
    background-color: #0078D4;
    color: #FFFFFF;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
}

QPushButton.primary-btn:hover {
    background-color: #106EBE;
}

QPushButton.primary-btn:pressed {
    background-color: #005A9E;
}

/* Danger buttons */
QPushButton.danger-btn {
    background-color: #E81123;
    color: #FFFFFF;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
}

QPushButton.danger-btn:hover {
    background-color: #C50F1F;
}

/* Secondary cards and panels */
QFrame.card {
    background-color: #1E1E1E;
    border: 1px solid #2E2E2E;
    border-radius: 8px;
}

QFrame.card:hover {
    border: 1px solid #0078D4;
    background-color: #252525;
}

/* Text inputs */
QLineEdit {
    background-color: #222222;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #0078D4;
    background-color: #282828;
}

/* Chips / Filter buttons */
QPushButton.chip {
    background-color: #2A2A2A;
    color: #DDDDDD;
    border: 1px solid #3E3E3E;
    border-radius: 14px;
    padding: 5px 14px;
    font-size: 12px;
}

QPushButton.chip:hover {
    background-color: #383838;
    color: #FFFFFF;
}

QPushButton.chip:checked {
    background-color: #0078D4;
    color: #FFFFFF;
    border: 1px solid #0078D4;
    font-weight: bold;
}

/* Labels */
QLabel.heading {
    font-size: 20px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel.subheading {
    font-size: 13px;
    color: #999999;
}
"""
