"""gui/log_panel.py — BibleViewer + AgentLogPanel"""
from __future__ import annotations

import json
from typing import Any, Dict

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

_ROLE_COLORS = {
    "Writer":     QColor("#3399ff"),
    "Editor":     QColor("#ff9900"),
    "Proofreader":QColor("#33cc66"),
    "Guard":      QColor("#9966cc"),
    "System":     QColor("#ffcc00"),
}


class BibleViewer(QWidget):
    """project_bible.json をツリー表示するウィジェット。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["キー", "値"])
        self._tree.setColumnWidth(0, 180)
        layout.addWidget(self._tree)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setMaximumHeight(80)
        layout.addWidget(self._detail)

    def refresh(self, bible_data: Dict[str, Any]) -> None:
        self._tree.clear()
        self._populate(self._tree.invisibleRootItem(), bible_data)
        self._tree.expandToDepth(1)

    def _populate(self, parent: QTreeWidgetItem, data: Any, key: str = "") -> None:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    node = QTreeWidgetItem([str(k), ""])
                    parent.addChild(node)
                    self._populate(node, v, k)
                else:
                    node = QTreeWidgetItem([str(k), str(v)])
                    parent.addChild(node)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                label = item.get("name") or item.get("id") or item.get("content", "")[:30] if isinstance(item, dict) else str(item)
                node = QTreeWidgetItem([f"[{i}]", str(label)])
                node.setData(0, 32, item)
                parent.addChild(node)
                if isinstance(item, dict):
                    self._populate(node, item)

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, 32)
        if data:
            self._detail.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))


class AgentLogPanel(QListWidget):
    """エージェントログをロール別色分けで表示するリスト。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)

    def log(self, role: str, message: str, timestamp: str = "") -> None:
        prefix = f"[{timestamp}] " if timestamp else ""
        text = f"{prefix}[{role}] {message}"
        item = QListWidgetItem(text)
        color = _ROLE_COLORS.get(role, QColor("#cccccc"))
        item.setForeground(color)
        self.addItem(item)
        self.scrollToBottom()


class LogPanel(QSplitter):
    """BibleViewer と AgentLogPanel を縦に並べるコンテナ。"""

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self.bible_viewer = BibleViewer()
        self.agent_log = AgentLogPanel()
        self.addWidget(self.bible_viewer)
        self.addWidget(self.agent_log)
        self.setSizes([300, 200])
