"""core/bible.py — ProjectBible CRUD + ドラフトログ管理 + output/ 初期化"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str, existing: List[str]) -> str:
    """prefix_NNN 形式で既存と重複しない ID を生成する"""
    n = len(existing) + 1
    while True:
        candidate = f"{prefix}_{n:03d}"
        if candidate not in existing:
            return candidate
        n += 1


class ProjectBible:
    """project_bible.json の CRUD ラッパー。

    すべての書き込みは add_fact() / resolve_conflict() 経由で行う。
    直接 JSON を書き換えないこと。
    """

    _EMPTY: Dict[str, Any] = {
        "meta": {"title": "", "genre": "", "created_at": "", "version": 1},
        "world": {"geography": [], "history": [], "rules": [], "atmosphere": ""},
        "characters": [],
        "plot": {
            "overall": {"premise": "", "theme": "", "ending_type": ""},
            "beat_sheet": [],
            "chapters": [],
        },
        "facts": [],
        "foreshadowing": [],
    }

    def __init__(self, project_dir: Path) -> None:
        self._path = project_dir / "project_bible.json"
        self._data: Dict[str, Any] = {}
        if self._path.exists():
            self._load()
        else:
            self._data = json.loads(json.dumps(self._EMPTY))

    # ------------------------------------------------------------------ I/O
    def _load(self) -> None:
        with self._path.open(encoding="utf-8") as f:
            self._data = json.load(f)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ Facts
    def add_fact(
        self,
        content: str,
        tags: List[str],
        category: str,
        chapter_introduced: int = 0,
    ) -> str:
        """Fact を追加し、新しい fact_id を返す。"""
        existing_ids = [f["id"] for f in self._data["facts"]]
        fid = _new_id("fact", existing_ids)
        self._data["facts"].append(
            {
                "id": fid,
                "content": content,
                "chapter_introduced": chapter_introduced,
                "tags": tags,
                "category": category,
                "superseded_by": None,
            }
        )
        self.save()
        return fid

    def resolve_conflict(self, existing_fact_id: str, reason: str) -> str:
        """既存 fact を superseded にし、理由を記録した新 fact を返す。"""
        # 上書き前の fact を superseded_by でマーク
        new_id = self.add_fact(
            content=f"[conflict resolved] {reason}",
            tags=["conflict"],
            category="event",
        )
        for fact in self._data["facts"]:
            if fact["id"] == existing_fact_id:
                fact["superseded_by"] = new_id
                break
        self.save()
        return new_id

    def get_facts_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """アクティブ（superseded_by=None）な facts をタグでフィルタリング。"""
        return [
            f
            for f in self._data["facts"]
            if f["superseded_by"] is None and any(t in f["tags"] for t in tags)
        ]

    def get_active_facts(self) -> List[Dict[str, Any]]:
        return [f for f in self._data["facts"] if f["superseded_by"] is None]

    # ------------------------------------------------------------------ Meta helpers
    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def update_meta(self, **kwargs: Any) -> None:
        self._data["meta"].update(kwargs)
        self.save()

    def update_plot_overall(self, **kwargs: Any) -> None:
        self._data["plot"]["overall"].update(kwargs)
        self.save()

    def add_chapter(self, chapter: Dict[str, Any]) -> None:
        self._data["plot"]["chapters"].append(chapter)
        self.save()

    def update_chapter_status(self, chapter_id: int, status: str) -> None:
        for ch in self._data["plot"]["chapters"]:
            if ch["id"] == chapter_id:
                ch["status"] = status
                break
        self.save()

    def add_character(self, character: Dict[str, Any]) -> None:
        self._data["characters"].append(character)
        self.save()


# --------------------------------------------------------------------------- #
# ドラフトログ管理
# --------------------------------------------------------------------------- #

class DraftLog:
    """ch{N:02d}_drafts.jsonl への追記と最良スコア取得。"""

    def __init__(self, log_path: Path) -> None:
        self._path = log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, attempt: int, draft: str, score: int, issues: List[str]) -> None:
        record = {
            "attempt": attempt,
            "timestamp": _now_iso(),
            "draft": draft,
            "score": score,
            "issues": issues,
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_best(self) -> Optional[Dict[str, Any]]:
        """スコア最大のドラフトレコードを返す。"""
        if not self._path.exists():
            return None
        best = None
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if best is None or record["score"] > best["score"]:
                    best = record
        return best

    def get_latest(self) -> Optional[Dict[str, Any]]:
        if not self._path.exists():
            return None
        last = None
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = json.loads(line)
        return last


# --------------------------------------------------------------------------- #
# output/ ディレクトリ初期化
# --------------------------------------------------------------------------- #

def init_project_dirs(base_output: Path, project_name: str) -> Path:
    """output/{project_name}/ 以下のサブフォルダを作成し、プロジェクトディレクトリを返す。"""
    project_dir = base_output / project_name
    for sub in [
        project_dir,
        project_dir / "plot" / "chapter_plans",
        project_dir / "manuscript" / "logs",
    ]:
        sub.mkdir(parents=True, exist_ok=True)
    return project_dir
