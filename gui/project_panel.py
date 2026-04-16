"""gui/project_panel.py — プロジェクトツリーパネル"""
from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

_STATUS_ICONS = {
    "planned":   "📋",
    "drafting":  "✏️",
    "critiquing":"🔍",
    "refining":  "🔧",
    "polishing": "✨",
    "archiving": "📦",
    "final":     "✅",
}


class ProjectPanel(QTreeWidget):
    chapter_selected = pyqtSignal(int)  # chapter_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabel("プロジェクト")
        self.itemClicked.connect(self._on_item_clicked)

    def update_chapters(self, chapters: list, statuses: Dict[str, str]) -> None:
        self.clear()
        for ch in chapters:
            cid = ch.get("id", 0)
            status = statuses.get(str(cid), "planned")
            icon = _STATUS_ICONS.get(status, "")
            text = f"{icon} 第{cid}章 {ch.get('title', '')}"
            item = QTreeWidgetItem([text])
            item.setData(0, 32, cid)  # UserRole
            self.addTopLevelItem(item)

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        cid = item.data(0, 32)
        if cid:
            self.chapter_selected.emit(cid)
