"""gui/inception_dialog.py — 新規プロジェクト作成ダイアログ（単一テキスト入力）"""
from __future__ import annotations

from typing import Dict, Any

from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

# ChatGPT などに渡す用のテンプレート文字列
_CONCEPT_TEMPLATE = """\
【ジャンル】
例: ファンタジー

【雰囲気・世界観】
（舞台設定、時代背景、全体の空気感など）

【主人公イメージ（外見・性格・動機）】
（どんな人物か、何を目指しているか）

【世界観タグ】
例: 魔法, 近未来, 孤島（カンマ区切り）

【登場人物メモ】
（主要な脇役・敵など）

【テーマ】
例: 成長と喪失

【起承転結ヒント】
（物語の大まかな流れ）
"""


class InceptionDialog(QDialog):
    """新規プロジェクト作成ダイアログ。
    
    必要事項をひとつのテキスト枠に記入する形式。
    ChatGPT 等で作成した原案テキストをそのまま貼り付けることもできる。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新規プロジェクト")
        self.setMinimumSize(560, 580)

        root = QVBoxLayout(self)

        # ── 上段: プロジェクト名 + 目標章数 ──────────────────────────
        form = QFormLayout()
        self._project_name = QLineEdit()
        self._project_name.setPlaceholderText("例: 蒼空の旅人")
        form.addRow("プロジェクト名 *:", self._project_name)

        self._target_chapters = QSpinBox()
        self._target_chapters.setRange(5, 20)
        self._target_chapters.setValue(10)
        form.addRow("目標章数:", self._target_chapters)
        root.addLayout(form)

        # ── テキスト枠ラベル + テンプレコピーボタン ───────────────────
        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("作品概要（テンプレートに沿って記入、または貼り付け）:"))
        label_row.addStretch()
        copy_btn = QPushButton("テンプレートをコピー")
        copy_btn.setToolTip("フォーマットをクリップボードにコピーします。ChatGPT 等に貼り付けて原案を作成してください。")
        copy_btn.clicked.connect(self._copy_template)
        label_row.addWidget(copy_btn)
        root.addLayout(label_row)

        # ── 大テキスト枠 ──────────────────────────────────────────────
        self._concept = QTextEdit()
        self._concept.setPlaceholderText(_CONCEPT_TEMPLATE)
        self._concept.setAcceptRichText(False)
        root.addWidget(self._concept)

        # ── OK / Cancel ───────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------ slots
    def _copy_template(self) -> None:
        """テンプレート文字列をクリップボードへコピーする。"""
        QApplication.clipboard().setText(_CONCEPT_TEMPLATE)

    def _on_accept(self) -> None:
        if not self._project_name.text().strip():
            self._project_name.setFocus()
            self._project_name.setPlaceholderText("← プロジェクト名は必須です")
            return
        self.accept()

    # ------------------------------------------------------------------ public
    def get_data(self) -> Dict[str, Any]:
        """入力値をまとめて返す。"""
        return {
            "project_name": self._project_name.text().strip(),
            "target_chapters": self._target_chapters.value(),
            "concept": self._concept.toPlainText().strip(),
        }
