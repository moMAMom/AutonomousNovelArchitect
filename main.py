"""main.py — エントリポイント"""
import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Autonomous Novel Architect")
    app.setFont(QFont("Meiryo", 10))

    # QSS 最小スタイル
    app.setStyleSheet(
        """
        QMainWindow { background: #1e1e1e; }
        QToolBar { background: #2d2d2d; border: none; spacing: 4px; }
        QStatusBar { background: #2d2d2d; color: #cccccc; }
        QTextEdit { background: #252526; color: #d4d4d4; font-family: 'Meiryo'; font-size: 11pt; }
        QTreeWidget { background: #252526; color: #d4d4d4; }
        QListWidget { background: #1e1e1e; color: #cccccc; }
        QSplitter::handle { background: #3c3c3c; }
        """
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
