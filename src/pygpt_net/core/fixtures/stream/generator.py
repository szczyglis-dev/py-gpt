#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.12 20:00:00                  #
# ================================================== #

import asyncio
import random
import string
import time
from dataclasses import dataclass
from typing import AsyncIterator, Iterator, Literal, Optional, Union, Dict, Any

APITypes = Literal["raw", "chat", "responses", "respones"]  # with typo alias
ChunkTypes = Literal["str", "code"]

@dataclass
class StreamConfig:
    api: APITypes = "raw"
    chunk: ChunkTypes = "str"
    cps: int = 16                 # chunks per second
    min_newline: int = 30         # minimum distance to next \n
    include_chat_role: bool = True  # in chat: first delta with {"role": "assistant"}

class FakeOpenAIStream:
    """
    Fake chunk streamer:
      - api: "raw" | "chat" | "responses" (alias: "respones")
      - chunk: "str" | "code"
      - stop() stops the stream
    Returned elements:
      - raw:        str (text only)
      - chat:       dict in chat.completion.chunk style (choices[0].delta.*)
      - responses:  dict of response.output_text.delta type (with delta + indices)
    """
    def __init__(self, *, rng_seed: Optional[int] = None, model_name: str = "gpt-4o-mini-fake", code_path: Optional[str] = None):
        self._rng = random.Random(rng_seed)
        self._stopped = False
        self._model = model_name
        self._run_id = ""
        self._msg_id = ""  # for Responses API
        # State for injecting new lines
        self._chars_since_nl = 0
        self._next_nl_at = 80
        self._code_path = code_path
        self._code_src = None
        self._code_pos = 0
        self._code_mode = False
        if code_path:
            try:
                with open(code_path, "r", encoding="utf-8") as f:
                    self._code_src = f.read()
            except Exception:
                self._code_src = None

    def stop(self):
        self._stopped = True

    def _reset_state(self, cfg: StreamConfig):
        self._stopped = False
        now = int(time.time())
        self._run_id = f"chatcmpl_fake_{now}_{self._rng.randrange(10**6)}"
        self._msg_id = f"msg_{self._rng.randrange(10**9):09d}"
        self._chars_since_nl = 0
        self._next_nl_at = self._rng.randint(cfg.min_newline, cfg.min_newline * 4)
        self._code_pos = 0

    # ---------------------- public: async (push-friendly) ----------------------

    async def astream(self, api: APITypes = "raw", chunk: ChunkTypes = "str",
                     cps: int = 16, min_newline: int = 30,
                     include_chat_role: bool = True) -> AsyncIterator[Union[str, Dict[str, Any]]]:
        """
        Asynchronous, endless stream of chunks until stop().
        Usage:
            s = FakeOpenAIStream()
            async for payload in s.stream("chat","code",cps=20,min_newline=30):
                emit(payload)  # e.g., to a WebChannel
        """
        cfg = StreamConfig(api=api, chunk=chunk, cps=cps, min_newline=min_newline,
                           include_chat_role=include_chat_role)
        yield_from_prefix, sleep_dt = self._start_and_prefix(cfg)
        for p in yield_from_prefix:
            yield p
        try:
            while not self._stopped:
                piece = self._make_piece(cfg)
                piece = self._inject_newlines(piece, cfg.min_newline)
                yield self._wrap_payload(cfg, piece)
                await asyncio.sleep(sleep_dt)
        finally:
            # here we don't close "[DONE]" or finish_reason, because the stream is deliberately "endless"
            pass

    # ---------------------- public: sync (pull-friendly) ----------------------

    def stream(self, api: APITypes = "raw", chunk: ChunkTypes = "str",
                    cps: int = 16, min_newline: int = 30,
                    include_chat_role: bool = True) -> Iterator[Union[str, Dict[str, Any]]]:
        """
        Synchronous version (e.g., for tests in a thread without asyncio).
        """
        cfg = StreamConfig(api=api, chunk=chunk, cps=cps, min_newline=min_newline,
                           include_chat_role=include_chat_role)
        yield_from_prefix, sleep_dt = self._start_and_prefix(cfg)
        for p in yield_from_prefix:
            yield p
        try:
            while not self._stopped:
                piece = self._make_piece(cfg)
                piece = self._inject_newlines(piece, cfg.min_newline)
                yield self._wrap_payload(cfg, piece)
                time.sleep(sleep_dt)
        finally:
            pass

    # ---------------------- internals ----------------------

    def _start_and_prefix(self, cfg: StreamConfig):
        # sanity + alias
        api = (cfg.api or "raw").lower().strip()
        if api == "respones":  # alias for typo
            api = "responses"
        if api not in ("raw", "chat", "responses"):
            raise ValueError(f"Unknown api: {api}")
        chunk = (cfg.chunk or "str").lower().strip()
        if chunk not in ("str", "code"):
            raise ValueError(f"Unknown chunk: {chunk}")
        cps = max(1, min(int(cfg.cps or 16), 120))
        min_nl = max(1, int(cfg.min_newline or 30))
        self._reset_state(cfg)
        sleep_dt = 1.0 / cps

        prefix_payloads: list[Union[str, Dict[str, Any]]] = []
        # Chat: often the first delta with a role
        if api == "chat" and cfg.include_chat_role:
            prefix_payloads.append(self._wrap_chat_delta({"role": "assistant", "content": ""}))
        if chunk == "code":
            prefix_payloads.append(self._wrap_payload(cfg, ""))

        self._code_mode = (chunk == "code")
        return prefix_payloads, sleep_dt

    def _make_piece(self, cfg: StreamConfig) -> str:
        size = self._rng.randint(5, 28)
        if cfg.chunk == "code":
            if self._code_src:
                return self._code_take(size)
            return self._random_code_like(size)
        return self._random_text(size)

    def _random_text(self, n: int) -> str:
        letters = string.ascii_letters + "     "
        digits = string.digits
        punct = ".,;:!?-'" + '"'
        pool = letters + digits + punct
        return "".join(self._rng.choice(pool) for _ in range(n))

    def _random_code_like(self, n: int) -> str:
        pool = string.ascii_letters + string.digits + "_"
        ops = "()[]{}.,:;=+-*/%<>!&|^~"
        spaces_ratio = "   "
        full = pool + ops + spaces_ratio
        return "".join(self._rng.choice(full) for _ in range(n))

    def _inject_newlines(self, s: str, min_nl: int) -> str:
        if self._code_mode and self._code_src:
            return s
        out = []
        i = 0
        while i < len(s):
            remaining = self._next_nl_at - self._chars_since_nl
            if remaining <= 0:
                out.append("\n")
                self._chars_since_nl = 0
                self._next_nl_at = self._rng.randint(min_nl, min_nl * 4)
                # random indent for pseudocode
                if self._next_nl_at > min_nl and self._rng.random() < 0.25:
                    tabs = "    " * self._rng.randint(1, 3)
                    out.append(tabs)
                    self._chars_since_nl += len(tabs)
                continue
            take = min(remaining, len(s) - i)
            seg = s[i:i+take]
            out.append(seg)
            self._chars_since_nl += len(seg)
            i += take
        return "".join(out)

    def _code_take(self, n: int) -> str:
        if not self._code_src:
            return ""
        L = len(self._code_src)
        if L == 0:
            return ""
        idx = self._code_pos
        out = []
        for _ in range(n):
            out.append(self._code_src[idx])
            idx += 1
            if idx >= L:
                idx = 0
        self._code_pos = idx
        return "".join(out)

    # ---------------------- wrappers ----------------------

    def _wrap_payload(self, cfg: StreamConfig, text: str) -> Union[str, Dict[str, Any]]:
        api = "responses" if cfg.api == "respones" else cfg.api
        if api == "raw":
            return text
        elif api == "chat":
            return self._wrap_chat_delta({"content": text})
        else:
            # Responses API delta; also adding output_index/content_index/item_id
            return {
                "type": "response.output_text.delta",
                "delta": text,
                "output_index": 0,
                "content_index": 0,
                "item_id": self._msg_id
            }

    def _wrap_chat_delta(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        now = int(time.time())
        return {
            "id": self._run_id,
            "object": "chat.completion.chunk",
            "created": now,
            "model": self._model,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": None
                }
            ]
        }