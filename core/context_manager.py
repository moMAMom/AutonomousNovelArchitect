"""core/context_manager.py — トークン予算管理 + プロンプトブロック組み立て"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import tiktoken

from core.config import get_config

_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


class ContextManager:
    """トークン予算を管理しながらプロンプトブロックを組み立てる。"""

    def __init__(self) -> None:
        self._cfg = get_config()

    @property
    def input_limit(self) -> int:
        return self._cfg.input_token_limit

    def build_prompt(
        self,
        system_prompt: str,
        fixed_memory: str,
        direct_injection: str,
        sliding_window: str,
        summarized_memory: str,
        chapter_plan: str,
        prev_draft: Optional[str] = None,
        editor_feedback: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """各ブロックを予算内に収めてメッセージリストを返す。

        予算超過時の対処:
          1. summarized_memory を 50% 圧縮
          2. それでも超過なら direct_injection を削減
        """
        budgets = self._cfg.token_budgets

        # prev_draft & editor_feedback はリトライ時のみ使用
        _prev = prev_draft or ""
        _feedback = editor_feedback or ""

        def _build(sm: str, di: str) -> List[Dict[str, str]]:
            user_parts = [
                f"## 固定記憶（世界観・主人公）\n{fixed_memory}",
                f"## 関連情報（Direct Injection）\n{di}" if di else "",
                f"## 直近章（Sliding Window）\n{sliding_window}" if sliding_window else "",
                f"## 過去章要約\n{sm}" if sm else "",
                f"## 章計画\n{chapter_plan}",
                f"## 前回ドラフト\n{_prev}" if _prev else "",
                f"## 編集者フィードバック\n{_feedback}" if _feedback else "",
            ]
            user_content = "\n\n".join(p for p in user_parts if p)
            return [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

        messages = _build(summarized_memory, direct_injection)
        total = sum(count_tokens(m["content"]) for m in messages)

        if total > self.input_limit:
            # summarized_memory を 50% 圧縮
            compressed_sm = summarized_memory[: len(summarized_memory) // 2]
            messages = _build(compressed_sm, direct_injection)
            total = sum(count_tokens(m["content"]) for m in messages)

        if total > self.input_limit:
            # direct_injection を削減
            messages = _build(compressed_sm, "")  # type: ignore[possibly-undefined]
            total = sum(count_tokens(m["content"]) for m in messages)

        return messages

    def remaining_tokens(self, messages: List[Dict[str, str]]) -> int:
        used = sum(count_tokens(m["content"]) for m in messages)
        return self.input_limit - used
