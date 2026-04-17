"""gui/main_window.py — QMainWindow + OrchestratorWorker"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)
from PyQt6.QtCore import Qt

from core.bible import init_project_dirs
from core.config import get_config, load_config
from core.orchestrator import Orchestrator
from gui.inception_dialog import InceptionDialog
from gui.log_panel import LogPanel
from gui.preview_panel import PreviewPanel
from gui.project_panel import ProjectPanel
from gui.settings_dialog import SettingsDialog

_OUTPUT_DIR = Path(__file__).parent.parent / "output"


# =========================================================================== #
#  OrchestratorWorker — QThread ラッパー
# =========================================================================== #

class OrchestratorWorker(QThread):
    """Orchestrator をバックグラウンドスレッドで実行するラッパー。"""

    token_received = pyqtSignal(str)
    phase_changed = pyqtSignal(str)
    score_updated = pyqtSignal(int)
    needs_approval = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    bible_updated = pyqtSignal()
    finished_chapter = pyqtSignal(int)

    def __init__(self, orchestrator: Orchestrator, chapter_id: int) -> None:
        super().__init__()
        self._orc = orchestrator
        self._chapter_id = chapter_id
        # 中継
        self._orc.token_received.connect(self.token_received)
        self._orc.phase_changed.connect(self.phase_changed)
        self._orc.score_updated.connect(self.score_updated)
        self._orc.needs_approval.connect(self.needs_approval)
        self._orc.error_occurred.connect(self.error_occurred)
        self._orc.bible_updated.connect(self.bible_updated)

    def run(self) -> None:
        self._orc.run_chapter(self._chapter_id)
        self.finished_chapter.emit(self._chapter_id)

    def stop(self) -> None:
        self._orc.request_stop()


# =========================================================================== #
#  MainWindow
# =========================================================================== #

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Autonomous Novel Architect")
        self.setMinimumSize(1200, 700)

        self._orchestrator: Optional[Orchestrator] = None
        self._worker: Optional[OrchestratorWorker] = None
        self._project_dir: Optional[Path] = None

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # ToolBar
        toolbar = QToolBar("メイン")
        self.addToolBar(toolbar)
        toolbar.addAction("📄 新規", self._new_project)
        toolbar.addAction("📂 開く", self._open_project)
        toolbar.addSeparator()
        self._run_action = toolbar.addAction("▶ 実行", self._run)
        self._stop_action = toolbar.addAction("■ 停止", self._stop)
        toolbar.addSeparator()
        toolbar.addAction("💾 書き出し", self._export)
        toolbar.addAction("⚙ 設定", self._open_settings)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        h_layout.addWidget(splitter)

        self._project_panel = ProjectPanel()
        splitter.addWidget(self._project_panel)

        self._preview = PreviewPanel()
        splitter.addWidget(self._preview)

        self._log_panel = LogPanel()
        splitter.addWidget(self._log_panel)

        splitter.setSizes([240, 600, 360])

        # StatusBar
        status = QStatusBar()
        self.setStatusBar(status)
        self._role_label = QLabel("待機中")
        self._score_bar = QProgressBar()
        self._score_bar.setRange(0, 100)
        self._score_bar.setFixedWidth(120)
        self._token_label = QLabel("トークン: -")
        status.addWidget(self._role_label)
        status.addWidget(self._score_bar)
        status.addPermanentWidget(self._token_label)

        # 承認ゲート接続
        self._preview.connect_approval(self._approve_chapter, self._revise_chapter)

    # ------------------------------------------------------------------ actions
    def _new_project(self) -> None:
        wizard = InceptionDialog(self)
        if wizard.exec() != InceptionDialog.DialogCode.Accepted:
            return
        data = wizard.get_data()
        project_name = data["project_name"]
        project_dir = init_project_dirs(_OUTPUT_DIR, project_name)
        self._project_dir = project_dir
        load_config()

        self._orchestrator = Orchestrator(project_dir)
        # シグナル接続
        self._connect_orchestrator_signals(self._orchestrator)

        self._log_panel.agent_log.log("System", f"プロジェクト [{project_name}] を開始します。")
        self._preview.clear()

        # Inception → Structuring をバックグラウンドで実行
        class _InceptionWorker(QThread):
            done = pyqtSignal()
            err = pyqtSignal(str)
            def __init__(self, orc, data):
                super().__init__()
                self._orc = orc
                self._data = data
            def run(self):
                try:
                    self._orc.start_inception(self._data)
                    self._orc.start_structuring(self._data["target_chapters"])
                    self.done.emit()
                except Exception as e:
                    self.err.emit(str(e))

        self._inception_worker = _InceptionWorker(self._orchestrator, data)
        self._inception_worker.done.connect(self._on_inception_done)
        self._inception_worker.err.connect(self._on_error)
        self._inception_worker.start()
        self._role_label.setText("Inception 実行中…")

    def _on_inception_done(self) -> None:
        self._role_label.setText("Inception 完了")
        self._refresh_project_panel()
        self._log_panel.agent_log.log("System", "Bible・章プランを生成しました。ノンストップモードで執筆を開始します。")
        # ノンストップ: Inception 完了後に自動で第1章から実行開始
        self._run()

    def _open_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "プロジェクトフォルダを選択", str(_OUTPUT_DIR))
        if not path:
            return
        self._project_dir = Path(path)
        load_config()
        self._orchestrator = Orchestrator(self._project_dir)
        self._connect_orchestrator_signals(self._orchestrator)
        self._refresh_project_panel()
        self._log_panel.agent_log.log("System", f"プロジェクト [{self._project_dir.name}] を読み込みました。")

    def _run(self) -> None:
        if self._orchestrator is None:
            QMessageBox.information(self, "情報", "先に新規プロジェクトを作成するか、既存を開いてください。")
            return
        if self._worker and self._worker.isRunning():
            return

        resume = self._orchestrator.resume()
        chapters = self._orchestrator.bible.data.get("plot", {}).get("chapters", [])
        statuses = resume.get("chapter_statuses", {})

        # 未完了の最初の章を選択
        next_ch = None
        for ch in chapters:
            cid = ch.get("id", 0)
            if statuses.get(str(cid), "planned") != "final":
                next_ch = cid
                break

        if next_ch is None:
            QMessageBox.information(self, "完了", "すべての章が完成しています。")
            return

        self._start_chapter_worker(next_ch)

    def _start_chapter_worker(self, chapter_id: int) -> None:
        assert self._orchestrator is not None
        self._preview.clear()
        self._worker = OrchestratorWorker(self._orchestrator, chapter_id)
        self._worker.token_received.connect(self._preview.append_token)
        self._worker.phase_changed.connect(self._on_phase_changed)
        self._worker.score_updated.connect(self._on_score_updated)
        self._worker.needs_approval.connect(self._preview.show_approval_gate)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.bible_updated.connect(self._on_bible_updated)
        self._worker.finished_chapter.connect(self._on_chapter_finished)
        self._worker.start()
        self._role_label.setText(f"第{chapter_id}章 執筆中…")
        self._log_panel.agent_log.log("Writer", f"第{chapter_id}章 執筆開始")

    def _stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self._role_label.setText("停止リクエスト済み")

    def _export(self) -> None:
        if self._project_dir is None:
            return
        manuscript_dir = self._project_dir / "manuscript"
        texts = []
        for p in sorted(manuscript_dir.glob("ch*_final.txt")):
            texts.append(p.read_text(encoding="utf-8"))
        if not texts:
            QMessageBox.information(self, "書き出し", "最終稿がありません。")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存先", str(self._project_dir / "manuscript.txt"), "Text Files (*.txt)"
        )
        if save_path:
            Path(save_path).write_text("\n\n".join(texts), encoding="utf-8")
            QMessageBox.information(self, "書き出し", f"保存しました: {save_path}")

    def _open_settings(self) -> None:
        locked = self._orchestrator.progress.locked if self._orchestrator else False
        dlg = SettingsDialog(locked=locked, parent=self)
        dlg.exec()

    # ------------------------------------------------------------------ slots
    @pyqtSlot(str)
    def _on_phase_changed(self, phase: str) -> None:
        self._role_label.setText(phase)
        self._log_panel.agent_log.log("System", f"フェーズ: {phase}")

    @pyqtSlot(int)
    def _on_score_updated(self, score: int) -> None:
        self._score_bar.setValue(score)
        self._log_panel.agent_log.log("Editor", f"スコア: {score}")

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        self._log_panel.agent_log.log("System", f"⚠ {msg}")
        QMessageBox.warning(self, "エラー", msg)

    @pyqtSlot()
    def _on_bible_updated(self) -> None:
        if self._orchestrator:
            self._log_panel.bible_viewer.refresh(self._orchestrator.bible.data)
            self._log_panel.agent_log.log("Guard", "Bible 更新")

    @pyqtSlot(int)
    def _on_chapter_finished(self, chapter_id: int) -> None:
        self._log_panel.agent_log.log("System", f"第{chapter_id}章 完了")
        self._refresh_project_panel()
        # ノンストップ: 次の未完了章を自動で実行
        if self._orchestrator is None:
            return
        resume = self._orchestrator.resume()
        chapters = self._orchestrator.bible.data.get("plot", {}).get("chapters", [])
        statuses = resume.get("chapter_statuses", {})
        next_ch = None
        for ch in chapters:
            cid = ch.get("id", 0)
            if statuses.get(str(cid), "planned") != "final":
                next_ch = cid
                break
        if next_ch is not None:
            self._log_panel.agent_log.log("System", f"第{next_ch}章 自動開始（ノンストップ）")
            self._start_chapter_worker(next_ch)
        else:
            self._role_label.setText("全章完成")
            self._log_panel.agent_log.log("System", "すべての章が完成しました。")

    def _approve_chapter(self, chapter_id: int) -> None:
        if self._orchestrator:
            self._orchestrator.approve_chapter(chapter_id)
        self._preview.hide_approval_gate()

    def _revise_chapter(self, chapter_id: int) -> None:
        # 修正指示 → 単純に再実行
        self._preview.hide_approval_gate()
        if chapter_id > 0:
            self._start_chapter_worker(chapter_id)

    def _refresh_project_panel(self) -> None:
        if self._orchestrator is None:
            return
        chapters = self._orchestrator.bible.data.get("plot", {}).get("chapters", [])
        statuses = self._orchestrator.progress.data.get("chapter_statuses", {})
        self._project_panel.update_chapters(chapters, statuses)

    def _connect_orchestrator_signals(self, orc: Orchestrator) -> None:
        orc.error_occurred.connect(self._on_error)
        orc.bible_updated.connect(self._on_bible_updated)
