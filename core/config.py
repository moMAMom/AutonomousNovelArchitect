"""core/config.py — pydantic による config.yaml ローダー"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml
from pydantic import BaseModel, Field


class TokenBudgets(BaseModel):
    system_prompt: int = 500
    fixed_memory: int = 4000
    sliding_window: int = 20000
    summarized_memory: int = 3000
    direct_injection: int = 2000
    chapter_plan: int = 1000
    prev_draft: int = 8000
    editor_feedback: int = 500
    output_reserve: int = 15000
    safety_margin: int = 2536


class AppConfig(BaseModel):
    # ロック項目
    model_id: str = "qwen3-9b-instruct"
    max_retry_count: int = 3
    score_threshold: int = 80
    sliding_window_chapters: int = 3
    token_budgets: TokenBudgets = Field(default_factory=TokenBudgets)

    # 変更可項目
    chapter_approval_gate: bool = False
    lm_studio_url: str = "http://localhost:1234/v1"
    request_timeout_sec: int = 800
    connection_retry_count: int = 3

    @property
    def input_token_limit(self) -> int:
        """LLM への入力トークン上限（65536 - output_reserve - safety_margin）"""
        return 65536 - self.token_budgets.output_reserve - self.token_budgets.safety_margin


_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_cached: AppConfig | None = None


def load_config(path: Path | None = None) -> AppConfig:
    global _cached
    target = path or _CONFIG_PATH
    with target.open(encoding="utf-8") as f:
        raw: Dict = yaml.safe_load(f)
    _cached = AppConfig(**raw)
    return _cached


def get_config() -> AppConfig:
    if _cached is None:
        return load_config()
    return _cached
