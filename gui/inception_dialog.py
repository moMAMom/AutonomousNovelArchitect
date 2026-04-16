"""gui/inception_dialog.py — 新規プロジェクトウィザード（3ページ）"""
from __future__ import annotations

from typing import Dict, Any

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)


class _Page1(QWizardPage):
    """基本情報"""
    def __init__(self):
        super().__init__()
        self.setTitle("基本情報")
        form = QFormLayout(self)
        self.project_name = QLineEdit()
        self.registerField("project_name*", self.project_name)
        form.addRow("プロジェクト名:", self.project_name)

        self.genre = QComboBox()
        self.genre.addItems(["ファンタジー", "SF", "ミステリー", "恋愛", "歴史", "ホラー", "その他"])
        form.addRow("ジャンル:", self.genre)

        self.atmosphere = QTextEdit()
        self.atmosphere.setPlaceholderText("雰囲気・世界観のメモ（任意）")
        self.atmosphere.setMaximumHeight(80)
        form.addRow("雰囲気メモ:", self.atmosphere)


class _Page2(QWizardPage):
    """設定・キャラクター"""
    def __init__(self):
        super().__init__()
        self.setTitle("設定・キャラクター")
        form = QFormLayout(self)

        self.protagonist = QTextEdit()
        self.protagonist.setPlaceholderText("主人公のイメージ（外見・性格・動機など）")
        self.protagonist.setMaximumHeight(80)
        form.addRow("主人公イメージ:", self.protagonist)

        self.world_tags = QLineEdit()
        self.world_tags.setPlaceholderText("例: 魔法, 近未来, 孤島（カンマ区切り）")
        form.addRow("世界観タグ:", self.world_tags)

        self.characters_memo = QTextEdit()
        self.characters_memo.setPlaceholderText("主要登場人物のメモ（任意）")
        self.characters_memo.setMaximumHeight(80)
        form.addRow("登場人物メモ:", self.characters_memo)


class _Page3(QWizardPage):
    """プロット方向"""
    def __init__(self):
        super().__init__()
        self.setTitle("プロット方向")
        form = QFormLayout(self)

        self.theme = QLineEdit()
        self.theme.setPlaceholderText("例: 成長と喪失")
        form.addRow("テーマ:", self.theme)

        self.plot_hint = QTextEdit()
        self.plot_hint.setPlaceholderText("起承転結のヒント（任意）")
        self.plot_hint.setMaximumHeight(80)
        form.addRow("起承転結ヒント:", self.plot_hint)

        self.target_chapters = QSpinBox()
        self.target_chapters.setRange(5, 20)
        self.target_chapters.setValue(10)
        form.addRow("目標章数:", self.target_chapters)


class InceptionDialog(QWizard):
    """新規プロジェクトウィザード。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新規プロジェクト")
        self.setMinimumSize(520, 400)

        self._p1 = _Page1()
        self._p2 = _Page2()
        self._p3 = _Page3()
        self.addPage(self._p1)
        self.addPage(self._p2)
        self.addPage(self._p3)

    def get_data(self) -> Dict[str, Any]:
        """ウィザード入力値をまとめて返す。"""
        return {
            "project_name": self.field("project_name"),
            "genre": self._p1.genre.currentText(),
            "atmosphere": self._p1.atmosphere.toPlainText(),
            "protagonist": self._p2.protagonist.toPlainText(),
            "world_tags": [t.strip() for t in self._p2.world_tags.text().split(",") if t.strip()],
            "characters_memo": self._p2.characters_memo.toPlainText(),
            "theme": self._p3.theme.text(),
            "plot_hint": self._p3.plot_hint.toPlainText(),
            "target_chapters": self._p3.target_chapters.value(),
        }
