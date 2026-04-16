"""gui/preview_panel.py — ストリーミング原稿プレビュー + 承認ゲートUI"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PreviewPanel(QWidget):
    """原稿プレビュー（ストリーミング追記対応）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        layout.addWidget(self._text_edit)

        # 承認ゲートエリア（通常は非表示）
        self._gate_widget = QWidget()
        gate_layout = QHBoxLayout(self._gate_widget)
        gate_layout.addWidget(QLabel("章の内容を確認してください:"))
        self._approve_btn = QPushButton("✅ 承認")
        self._revise_btn = QPushButton("✏️ 修正指示")
        gate_layout.addWidget(self._approve_btn)
        gate_layout.addWidget(self._revise_btn)
        layout.addWidget(self._gate_widget)
        self._gate_widget.hide()

        self._pending_chapter_id: int = 0

    @pyqtSlot(str)
    def append_token(self, token: str) -> None:
        """ストリーミングチャンクを末尾に追記する。"""
        cursor = self._text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self._text_edit.setTextCursor(cursor)

    def set_text(self, text: str) -> None:
        self._text_edit.setPlainText(text)

    def clear(self) -> None:
        self._text_edit.clear()
        self.hide_approval_gate()

    @pyqtSlot(int)
    def show_approval_gate(self, chapter_id: int) -> None:
        self._pending_chapter_id = chapter_id
        self._gate_widget.show()

    def hide_approval_gate(self) -> None:
        self._gate_widget.hide()
        self._pending_chapter_id = 0

    def connect_approval(self, approve_callback, revise_callback) -> None:
        self._approve_btn.clicked.connect(lambda: approve_callback(self._pending_chapter_id))
        self._revise_btn.clicked.connect(lambda: revise_callback(self._pending_chapter_id))
