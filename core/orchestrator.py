"""core/orchestrator.py — Orchestrator 状態機械 + ProgressTracker"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from core.api_client import LMStudioClient
from core.agents import EditorAgent, GuardAgent, ProofreaderAgent, WriterAgent
from core.bible import DraftLog, ProjectBible, init_project_dirs
from core.config import get_config
from core.context_manager import ContextManager


# =========================================================================== #
#  ProgressTracker
# =========================================================================== #

class ProgressTracker:
    """progress.json の読み書きと再開ポイント管理。"""

    def __init__(self, project_dir: Path) -> None:
        self._path = project_dir / "progress.json"
        self._data: Dict[str, Any] = self._default()

    @staticmethod
    def _default() -> Dict[str, Any]:
        return {
            "phase": "inception",
            "current_chapter": 1,
            "chapter_statuses": {},
            "current_attempt": 1,
            "best_score_so_far": 0,
            "best_draft_index": 0,
            "locked": False,
        }

    def load(self) -> None:
        if self._path.exists():
            with self._path.open(encoding="utf-8") as f:
                self._data = json.load(f)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def lock(self) -> None:
        self._data["locked"] = True
        self.save()

    @property
    def locked(self) -> bool:
        return self._data.get("locked", False)

    def get_resume_point(self) -> Dict[str, Any]:
        return {
            "phase": self._data["phase"],
            "current_chapter": self._data["current_chapter"],
            "chapter_statuses": self._data["chapter_statuses"],
            "current_attempt": self._data["current_attempt"],
        }

    def set_phase(self, phase: str) -> None:
        self._data["phase"] = phase
        self.save()

    def set_chapter_status(self, chapter_id: int, status: str) -> None:
        self._data["chapter_statuses"][str(chapter_id)] = status
        self.save()

    def set_attempt(self, attempt: int, score: int = 0, best_index: int = 0) -> None:
        self._data["current_attempt"] = attempt
        if score > self._data.get("best_score_so_far", 0):
            self._data["best_score_so_far"] = score
            self._data["best_draft_index"] = best_index
        self.save()

    def reset_chapter(self, chapter_id: int) -> None:
        self._data["current_chapter"] = chapter_id
        self._data["current_attempt"] = 1
        self._data["best_score_so_far"] = 0
        self._data["best_draft_index"] = 0
        self.save()

    @property
    def data(self) -> Dict[str, Any]:
        return self._data


# =========================================================================== #
#  Orchestrator
# =========================================================================== #

class Orchestrator(QObject):
    """小説生成の全フェーズを制御する状態機械。

    シグナルは GUI の OrchestratorWorker 経由で MainWindow に接続する。
    """

    # pyqtSignal 定義
    token_received = pyqtSignal(str)
    phase_changed = pyqtSignal(str)
    score_updated = pyqtSignal(int)
    needs_approval = pyqtSignal(int)          # chapter_id
    error_occurred = pyqtSignal(str)
    bible_updated = pyqtSignal()

    def __init__(self, project_dir: Path) -> None:
        super().__init__()
        self._project_dir = project_dir
        self._cfg = get_config()

        # --- コンポーネント初期化 ---
        self._client = LMStudioClient()
        self._ctx = ContextManager()
        self._bible = ProjectBible(project_dir)
        self._progress = ProgressTracker(project_dir)
        self._progress.load()

        self._writer = WriterAgent(self._client, self._ctx)
        self._editor = EditorAgent(self._client, self._ctx)
        self._proofreader = ProofreaderAgent(self._client, self._ctx)
        self._guard = GuardAgent(self._client, self._ctx)

        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    # ------------------------------------------------------------------ helpers
    def _draft_log(self, chapter_id: int) -> DraftLog:
        log_path = self._project_dir / "manuscript" / "logs" / f"ch{chapter_id:02d}_drafts.jsonl"
        return DraftLog(log_path)

    def _guard_log_path(self) -> Path:
        return self._project_dir / "manuscript" / "logs" / "guard_actions.jsonl"

    def _build_sliding_window(self, current_chapter: int) -> str:
        """直近 N 章の最終稿を結合して返す。"""
        n = self._cfg.sliding_window_chapters
        texts = []
        for i in range(max(1, current_chapter - n), current_chapter):
            p = self._project_dir / "manuscript" / f"ch{i:02d}_final.txt"
            if p.exists():
                texts.append(f"=== 第{i}章 ===\n" + p.read_text(encoding="utf-8"))
        return "\n\n".join(texts)

    def _build_fixed_memory(self) -> str:
        """Bible から core 情報を文字列化する（世界観 + 主人公 + 全章プラン）。"""
        data = self._bible.data
        lines = []
        world = data.get("world", {})
        if world.get("atmosphere"):
            lines.append(f"世界観: {world['atmosphere']}")
        for ch in data.get("characters", []):
            if "主人公" in ch.get("tags", []):
                lines.append(
                    f"主人公: {ch['name']} / {ch.get('personality', '')} / 動機: {ch.get('motivation', '')}"
                )
        for ch in data.get("plot", {}).get("chapters", []):
            lines.append(f"第{ch['id']}章「{ch.get('title','')}」: {ch.get('goal','')}")
        return "\n".join(lines)

    def _build_direct_injection(self, tags: List[str]) -> str:
        facts = self._bible.get_facts_by_tags(tags) if tags else self._bible.get_active_facts()
        return "\n".join(f"- [{f['category']}] {f['content']}" for f in facts[:20])

    def _chapter_plan_text(self, chapter_id: int) -> str:
        p = self._project_dir / "plot" / "chapter_plans" / f"ch{chapter_id:02d}_plan.txt"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    # ================================================================== Phases
    def start_inception(self, keywords: Dict[str, Any]) -> None:
        """Inception フェーズ: キーワードから ProjectBible を生成。"""
        self.phase_changed.emit("inception")
        prompt = (
            "以下のキーワードをもとに長編小説（中編）のProjectBibleをJSON形式で生成してください。\n"
            "必須フィールド: meta（title, genre）, world（atmosphere, rules）, "
            "characters（主人公1名: id, name, appearance, personality, motivation, tags=[\"主人公\"]）, "
            "plot.overall（premise, theme, ending_type）\n\n"
            f"キーワード: {json.dumps(keywords, ensure_ascii=False)}"
        )
        messages = [
            {"role": "system", "content": "あなたは創造的な小説プランナーです。"},
            {"role": "user", "content": prompt},
        ]
        try:
            result = self._client.chat_json(messages, temperature=0.8)
            if result:
                # Bible を初期化
                if result.get("meta"):
                    self._bible.update_meta(**result["meta"])
                if result.get("world"):
                    self._bible.data["world"].update(result["world"])
                    self._bible.save()
                for char in result.get("characters", []):
                    self._bible.add_character(char)
                if result.get("plot", {}).get("overall"):
                    self._bible.update_plot_overall(**result["plot"]["overall"])
                self.bible_updated.emit()
            self._progress.set_phase("structuring")
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def start_structuring(self, target_chapters: int) -> None:
        """Structuring フェーズ: 章プランを生成して Bible と chapter_plans/ に保存。"""
        self.phase_changed.emit("structuring")
        overall = self._bible.data.get("plot", {}).get("overall", {})
        prompt = (
            f"以下の小説設定で{target_chapters}章構成の章プランを生成してください。\n"
            f"設定: {json.dumps(overall, ensure_ascii=False)}\n\n"
            "各章について: id（1始まり整数）, title, goal, events（リスト）, hookを含むJSONの配列を返してください。"
            '形式: {"chapters": [...]}'
        )
        messages = [
            {"role": "system", "content": "あなたは小説の構成プランナーです。"},
            {"role": "user", "content": prompt},
        ]
        try:
            result = self._client.chat_json(messages, temperature=0.7)
            chapters = result.get("chapters", []) if result else []
            for ch in chapters:
                ch.setdefault("status", "planned")
                self._bible.add_chapter(ch)
                # chapter_plans/ に保存
                plan_path = self._project_dir / "plot" / "chapter_plans" / f"ch{ch['id']:02d}_plan.txt"
                plan_path.write_text(
                    json.dumps(ch, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            self.bible_updated.emit()
            self._progress.set_phase("drafting")
            self._progress.lock()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    # ================================================================== Drafting cycle
    def run_chapter(self, chapter_id: int) -> None:
        """1章分の Recursive Drafting サイクルを実行する。"""
        cfg = self._cfg
        draft_log = self._draft_log(chapter_id)
        self._progress.reset_chapter(chapter_id)
        self._progress.set_chapter_status(chapter_id, "drafting")

        fixed = self._build_fixed_memory()
        sliding = self._build_sliding_window(chapter_id)
        chapter_plan = self._chapter_plan_text(chapter_id)
        direct = self._build_direct_injection([])

        prev_draft: Optional[str] = None
        feedback: Optional[str] = None

        for attempt in range(1, cfg.max_retry_count + 2):
            if self._stop_requested:
                break

            # --- Drafting ---
            self._progress.set_chapter_status(chapter_id, "drafting")
            draft_text = ""
            try:
                for chunk in self._writer.generate_stream(
                    fixed_memory=fixed,
                    direct_injection=direct,
                    sliding_window=sliding,
                    summarized_memory="",
                    chapter_plan=chapter_plan,
                    prev_draft=prev_draft,
                    editor_feedback=feedback,
                ):
                    draft_text += chunk
                    self.token_received.emit(chunk)
            except Exception as exc:
                self.error_occurred.emit(f"Writer エラー: {exc}")
                return

            # --- Critiquing ---
            self._progress.set_chapter_status(chapter_id, "critiquing")
            try:
                eval_result = self._editor.evaluate(draft_text, chapter_plan)
            except Exception as exc:
                self.error_occurred.emit(f"Editor エラー: {exc}")
                return

            score = int(eval_result.get("score", 0))
            issues = eval_result.get("issues", [])
            summary = eval_result.get("summary", "")
            self.score_updated.emit(score)
            draft_log.append(attempt=attempt, draft=draft_text, score=score, issues=issues)
            self._progress.set_attempt(attempt, score=score, best_index=attempt)

            if score >= cfg.score_threshold:
                # 合格
                break

            if attempt > cfg.max_retry_count:
                # リトライ上限超過 → ベストスコア強制採用
                best = draft_log.get_best()
                if best:
                    draft_text = best["draft"]
                self.error_occurred.emit(
                    f"第{chapter_id}章: リトライ上限超過。ベストスコア({draft_log.get_best() and draft_log.get_best()['score']})で強制通過。"
                )
                break

            prev_draft = draft_text
            feedback = "\n".join(issues)

        if self._stop_requested:
            return

        # --- Refining（最終ドラフト） ---
        self._progress.set_chapter_status(chapter_id, "refining")

        # --- Polishing ---
        self._progress.set_chapter_status(chapter_id, "polishing")
        try:
            polished = self._proofreader.proofread(draft_text)
        except Exception as exc:
            self.error_occurred.emit(f"Proofreader エラー: {exc}")
            return

        # 承認ゲート
        if cfg.chapter_approval_gate:
            # final_text は承認後に確定。シグナルを emit して GUI 側で保留。
            self._pending_polished: Dict[int, str] = getattr(self, "_pending_polished", {})
            self._pending_polished[chapter_id] = polished
            self.needs_approval.emit(chapter_id)
            return

        self._finalize_chapter(chapter_id, polished)

    def approve_chapter(self, chapter_id: int, override_text: Optional[str] = None) -> None:
        """承認ゲートを通過させる（GUI から呼ぶ）。"""
        pending = getattr(self, "_pending_polished", {})
        text = override_text or pending.get(chapter_id, "")
        if text:
            self._finalize_chapter(chapter_id, text)

    def _finalize_chapter(self, chapter_id: int, final_text: str) -> None:
        """Archiving: Guard 更新 + 最終稿保存 + ステータス更新。"""
        self._progress.set_chapter_status(chapter_id, "archiving")

        # Guard
        try:
            self._guard.extract_and_update(
                final_text=final_text,
                existing_facts=self._bible.get_active_facts(),
                bible=self._bible,
                chapter_number=chapter_id,
                guard_log_path=self._guard_log_path(),
            )
            self.bible_updated.emit()
        except Exception as exc:
            self.error_occurred.emit(f"Guard エラー: {exc}")

        # 最終稿保存
        final_path = self._project_dir / "manuscript" / f"ch{chapter_id:02d}_final.txt"
        final_path.write_text(final_text, encoding="utf-8")

        self._bible.update_chapter_status(chapter_id, "final")
        self._progress.set_chapter_status(chapter_id, "final")

    def resume(self) -> Optional[Dict[str, Any]]:
        """progress.json から再開ポイントを取得する。"""
        return self._progress.get_resume_point()

    @property
    def progress(self) -> ProgressTracker:
        return self._progress

    @property
    def bible(self) -> ProjectBible:
        return self._bible
