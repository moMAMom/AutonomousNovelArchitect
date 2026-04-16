"""core/agents.py — 4ロールエージェント（BaseAgent + Writer/Editor/Proofreader/Guard）"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from core.api_client import LMStudioClient
from core.context_manager import ContextManager

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    with path.open(encoding="utf-8") as f:
        return f.read().strip()


class BaseAgent:
    """全エージェントの基底クラス。"""

    _PROMPT_FILE: str = ""

    def __init__(self, client: LMStudioClient, context_manager: ContextManager) -> None:
        self._client = client
        self._ctx = context_manager
        self._system_prompt: str = _load_prompt(self._PROMPT_FILE)

    def build_messages(self, user_content: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]


class WriterAgent(BaseAgent):
    """Writer: ドラフト生成（ストリーミング）。"""

    _PROMPT_FILE = "writer_system.txt"

    def generate_stream(
        self,
        fixed_memory: str,
        direct_injection: str,
        sliding_window: str,
        summarized_memory: str,
        chapter_plan: str,
        prev_draft: Optional[str] = None,
        editor_feedback: Optional[str] = None,
    ) -> Generator[str, None, None]:
        messages = self._ctx.build_prompt(
            system_prompt=self._system_prompt,
            fixed_memory=fixed_memory,
            direct_injection=direct_injection,
            sliding_window=sliding_window,
            summarized_memory=summarized_memory,
            chapter_plan=chapter_plan,
            prev_draft=prev_draft,
            editor_feedback=editor_feedback,
        )
        yield from self._client.chat_stream(messages, temperature=0.8)


class EditorAgent(BaseAgent):
    """Editor: ドラフト評価 → score / issues / summary を返す。"""

    _PROMPT_FILE = "editor_system.txt"

    def evaluate(self, draft: str, chapter_plan: str) -> Dict[str, Any]:
        user_content = f"## 章計画\n{chapter_plan}\n\n## ドラフト\n{draft}"
        messages = self.build_messages(user_content)
        result = self._client.chat_json(messages, temperature=0.2)
        if result is None:
            result = {"score": 0, "issues": ["評価JSONのパース失敗"], "summary": ""}
        return result


class ProofreaderAgent(BaseAgent):
    """Proofreader: 最終校正 → 校正済み本文を返す。"""

    _PROMPT_FILE = "proofreader_system.txt"

    def proofread(self, draft: str, style_rules: str = "") -> str:
        user_content = f"## 文体ルール\n{style_rules}\n\n## 本文\n{draft}" if style_rules else f"## 本文\n{draft}"
        messages = self.build_messages(user_content)
        return self._client.chat(messages, temperature=0.1)


class GuardAgent(BaseAgent):
    """Guard: 最終稿から新事実・矛盾を抽出し ProjectBible を更新する。"""

    _PROMPT_FILE = "guard_system.txt"

    def extract_and_update(
        self,
        final_text: str,
        existing_facts: List[Dict[str, Any]],
        bible: Any,  # ProjectBible（循環 import を避けるため Any）
        chapter_number: int,
        guard_log_path: Any,  # Path
    ) -> Dict[str, Any]:
        """Guard 処理を実行し、更新結果サマリを返す。"""
        facts_json = json.dumps(existing_facts, ensure_ascii=False, indent=2)
        user_content = (
            f"## 既存 facts\n{facts_json}\n\n## 最終稿（第{chapter_number}章）\n{final_text}"
        )
        messages = self.build_messages(user_content)
        result = self._client.chat_json(messages, temperature=0.1)
        if result is None:
            result = {"new_facts": [], "conflicts": []}

        import json as _json
        from datetime import datetime, timezone
        from pathlib import Path as _Path

        guard_log_path = _Path(guard_log_path)
        guard_log_path.parent.mkdir(parents=True, exist_ok=True)

        # 新事実を Bible に追加
        added_ids = []
        for nf in result.get("new_facts", []):
            fid = bible.add_fact(
                content=nf["content"],
                tags=nf.get("tags", []),
                category=nf.get("category", "event"),
                chapter_introduced=chapter_number,
            )
            added_ids.append(fid)

        # 矛盾を解決
        resolved_ids = []
        for conflict in result.get("conflicts", []):
            if conflict.get("resolution") in ("上書き", "補足"):
                new_id = bible.resolve_conflict(
                    existing_fact_id=conflict["existing_fact_id"],
                    reason=conflict["reason"],
                )
                resolved_ids.append(new_id)

        # guard_actions.jsonl に記録
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chapter": chapter_number,
            "added_facts": added_ids,
            "resolved_conflicts": resolved_ids,
            "raw": result,
        }
        with guard_log_path.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(record, ensure_ascii=False) + "\n")

        return record
