"""main.py — エントリポイント"""
import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Autonomous Novel Architect")
    app.setFont(QFont("Meiryo", 10))

    # ── グローバルダークテーマ ──────────────────────────────────────
    app.setStyleSheet("""
/* ベース */
QWidget {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Meiryo';
    font-size: 10pt;
}

/* メインウィンドウ・ダイアログ・ウィザード */
QMainWindow, QDialog, QWizard { background: #1e1e1e; }
QWizardPage { background: #252526; }

/* ツールバー */
QToolBar {
    background: #2d2d2d;
    border-bottom: 1px solid #3c3c3c;
    spacing: 6px;
    padding: 2px 4px;
}
QToolBar QToolButton {
    background: transparent;
    color: #d4d4d4;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
}
QToolBar QToolButton:hover  { background: #3a3a3a; border-color: #555; }
QToolBar QToolButton:pressed { background: #264f78; }
QToolBar QToolButton:disabled { color: #666; }

/* ステータスバー */
QStatusBar {
    background: #2d2d2d;
    color: #9d9d9d;
    border-top: 1px solid #3c3c3c;
}

/* ラベル */
QLabel { background: transparent; color: #d4d4d4; }

/* 入力ウィジェット共通 */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: #264f78;
    selection-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #569cd6;
}
QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled { color: #666; border-color: #2d2d2d; }

/* SpinBox ボタン */
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #3c3c3c;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background: #4a4a4a;
}

/* コンボボックス */
QComboBox {
    background: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 3px 6px;
}
QComboBox:focus { border-color: #569cd6; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { image: none; width: 8px; height: 8px; }
QComboBox QAbstractItemView {
    background: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    selection-background-color: #264f78;
    selection-color: #ffffff;
    outline: none;
}

/* チェックボックス */
QCheckBox { color: #d4d4d4; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    background: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
}
QCheckBox::indicator:checked { background: #264f78; border-color: #569cd6; }
QCheckBox::indicator:hover   { border-color: #569cd6; }

/* ボタン */
QPushButton {
    background: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 5px 16px;
    min-width: 60px;
}
QPushButton:hover  { background: #3a3a3a; border-color: #569cd6; }
QPushButton:pressed { background: #264f78; border-color: #569cd6; }
QPushButton:default {
    background: #0e639c;
    border-color: #1177bb;
    color: #ffffff;
}
QPushButton:default:hover  { background: #1177bb; }
QPushButton:disabled { background: #2a2a2a; color: #666; border-color: #2d2d2d; }

/* タブウィジェット */
QTabWidget::pane {
    background: #252526;
    border: 1px solid #3c3c3c;
    border-top: none;
}
QTabBar::tab {
    background: #2d2d2d;
    color: #9d9d9d;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #252526; color: #d4d4d4; border-bottom: 2px solid #569cd6; }
QTabBar::tab:hover:!selected { background: #3a3a3a; color: #d4d4d4; }

/* ツリー・リスト */
QTreeWidget, QListWidget {
    background: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    outline: none;
}
QTreeWidget::item, QListWidget::item { padding: 3px 4px; border: none; }
QTreeWidget::item:selected, QListWidget::item:selected {
    background: #264f78;
    color: #ffffff;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background: #2a2d2e;
}
QHeaderView::section {
    background: #2d2d2d;
    color: #9d9d9d;
    border: none;
    border-right: 1px solid #3c3c3c;
    padding: 4px 6px;
    font-size: 9pt;
}

/* スプリッター */
QSplitter::handle { background: #3c3c3c; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }
QSplitter::handle:hover { background: #569cd6; }

/* スクロールバー */
QScrollBar:vertical {
    background: #1e1e1e;
    width: 10px;
    margin: 0;
    border: none;
}
QScrollBar::handle:vertical {
    background: #424242;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #686868; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #1e1e1e;
    height: 10px;
    margin: 0;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #424242;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #686868; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* プログレスバー */
QProgressBar {
    background: #2d2d2d;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    text-align: center;
    color: #d4d4d4;
}
QProgressBar::chunk { background: #264f78; border-radius: 3px; }

/* メッセージボックス */
QMessageBox { background: #252526; }
QMessageBox QLabel { color: #d4d4d4; }

/* ツールチップ */
QToolTip {
    background: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #569cd6;
    padding: 4px;
}
""")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
