"""gui/settings_dialog.py — 設定ダイアログ（ロック制御付き）"""
from __future__ import annotations

from pathlib import Path

import yaml
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig, get_config, load_config

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_LOCK_MSG = "執筆開始後は変更できません。新規プロジェクトを作成してください。"


class SettingsDialog(QDialog):
    """設定ダイアログ。locked=True のときロック項目は編集不可。"""

    def __init__(self, locked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(480)
        self._locked = locked
        self._cfg = get_config()

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_generation_tab(), "生成")
        tabs.addTab(self._build_quality_tab(), "品質管理")
        tabs.addTab(self._build_connection_tab(), "接続")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _lock(self, widget: QWidget, locked: bool) -> QWidget:
        if locked:
            widget.setEnabled(False)
            widget.setToolTip(_LOCK_MSG)
        return widget

    # --------------------------------------------------------- tabs
    def _build_generation_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._model_id = QLineEdit(self._cfg.model_id)
        self._lock(self._model_id, self._locked)
        form.addRow("モデル ID:", self._model_id)

        self._sliding_window = QSpinBox()
        self._sliding_window.setRange(1, 15)
        self._sliding_window.setValue(self._cfg.sliding_window_chapters)
        self._lock(self._sliding_window, self._locked)
        form.addRow("Sliding Window 章数:", self._sliding_window)

        return w

    def _build_quality_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._max_retry = QSpinBox()
        self._max_retry.setRange(1, 10)
        self._max_retry.setValue(self._cfg.max_retry_count)
        self._lock(self._max_retry, self._locked)
        form.addRow("最大リトライ回数:", self._max_retry)

        self._score_threshold = QSpinBox()
        self._score_threshold.setRange(0, 100)
        self._score_threshold.setValue(self._cfg.score_threshold)
        self._lock(self._score_threshold, self._locked)
        form.addRow("合格スコア閾値:", self._score_threshold)

        self._approval_gate = QCheckBox("章完成時に承認ゲートを表示")
        self._approval_gate.setChecked(self._cfg.chapter_approval_gate)
        form.addRow("承認ゲート:", self._approval_gate)

        return w

    def _build_connection_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._lm_url = QLineEdit(self._cfg.lm_studio_url)
        form.addRow("LM Studio URL:", self._lm_url)

        self._timeout = QSpinBox()
        self._timeout.setRange(30, 3600)
        self._timeout.setValue(self._cfg.request_timeout_sec)
        form.addRow("タイムアウト (秒):", self._timeout)

        self._conn_retry = QSpinBox()
        self._conn_retry.setRange(1, 10)
        self._conn_retry.setValue(self._cfg.connection_retry_count)
        form.addRow("接続リトライ回数:", self._conn_retry)

        return w

    # --------------------------------------------------------- save
    def _save(self) -> None:
        with _CONFIG_PATH.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not self._locked:
            raw["model_id"] = self._model_id.text().strip()
            raw["max_retry_count"] = self._max_retry.value()
            raw["score_threshold"] = self._score_threshold.value()
            raw["sliding_window_chapters"] = self._sliding_window.value()

        raw["chapter_approval_gate"] = self._approval_gate.isChecked()
        raw["lm_studio_url"] = self._lm_url.text().strip()
        raw["request_timeout_sec"] = self._timeout.value()
        raw["connection_retry_count"] = self._conn_retry.value()

        with _CONFIG_PATH.open("w", encoding="utf-8") as f:
            yaml.safe_dump(raw, f, allow_unicode=True)

        load_config()  # キャッシュ更新
        self.accept()
