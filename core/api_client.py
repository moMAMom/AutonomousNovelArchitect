"""core/api_client.py — LM Studio ラッパー（同期・ストリーミング・JSON 抽出）"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Generator, List, Optional

import openai
from openai import OpenAI

from core.config import get_config


class LMStudioClient:
    """LM Studio OpenAI 互換エンドポイントへのクライアント。"""

    def __init__(self) -> None:
        cfg = get_config()
        self._client = OpenAI(
            base_url=cfg.lm_studio_url,
            api_key="lm-studio",
            timeout=cfg.request_timeout_sec,
        )
        self._model = cfg.model_id
        self._retry_count = cfg.connection_retry_count

    # ------------------------------------------------------------------ ping
    def ping(self) -> bool:
        """LM Studio の /v1/models に疎通確認する。成功で True を返す。"""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ chat (sync)
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 12000,
    ) -> str:
        """同期チャット。指数バックオフで最大 connection_retry_count 回リトライ。"""
        last_exc: Exception | None = None
        for attempt in range(self._retry_count):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                last_exc = exc
                wait = 2 ** attempt
                time.sleep(wait)
            except openai.APIStatusError as exc:
                raise RuntimeError(f"LM Studio API エラー: {exc.status_code} {exc.message}") from exc
        raise RuntimeError(f"LM Studio への接続が {self._retry_count} 回失敗しました: {last_exc}") from last_exc

    # ------------------------------------------------------------------ chat (stream)
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 12000,
    ) -> Generator[str, None, None]:
        """ストリーミングチャット。チャンク文字列をジェネレータで返す。"""
        last_exc: Exception | None = None
        for attempt in range(self._retry_count):
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
            except openai.APIStatusError as exc:
                raise RuntimeError(f"LM Studio API エラー: {exc.status_code} {exc.message}") from exc
        raise RuntimeError(f"LM Studio への接続が {self._retry_count} 回失敗しました: {last_exc}") from last_exc

    # ------------------------------------------------------------------ JSON extraction
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Optional[Dict[str, Any]]:
        """JSON を要求し、パース失敗時は正規表現フォールバックを試みる。"""
        # response_format による強制
        last_exc: Exception | None = None
        for attempt in range(self._retry_count):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content or ""
                return json.loads(raw)
            except json.JSONDecodeError:
                # フォールバック: 正規表現で最初の {...} ブロックを抽出
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        pass
                last_exc = ValueError(f"JSON パース失敗。生レスポンス: {raw[:200]}")
                time.sleep(2 ** attempt)
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
            except openai.APIStatusError as exc:
                raise RuntimeError(f"LM Studio API エラー: {exc.status_code} {exc.message}") from exc
        raise RuntimeError(f"JSON チャット失敗: {last_exc}") from last_exc
