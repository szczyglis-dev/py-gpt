#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.15 16:10:00                  #
# ================================================== #

from __future__ import annotations

from typing import Any, Optional


class RuntimeUsage:
    """Aggregate provider-reported token usage for one Agents v2 user turn."""

    INPUT_KEYS = (
        "input_tokens", "prompt_tokens", "prompt_token_count", "promptTokenCount",
        "input_token_count", "inputTokenCount",
    )
    OUTPUT_KEYS = (
        "output_tokens", "completion_tokens", "candidates_token_count", "candidatesTokenCount",
        "output_token_count", "outputTokenCount",
    )
    TOTAL_KEYS = (
        "total_tokens", "total_token_count", "totalTokenCount",
    )
    USAGE_KEYS = (
        "usage", "usage_metadata", "usageMetadata",
    )
    WRAPPER_KEYS = (
        "raw", "response", "message", "additional_kwargs",
    )
    ID_KEYS = (
        "id", "response_id", "responseId",
    )

    def __init__(self, runtime):
        self.runtime = runtime
        self.input_tokens = 0
        self.output_tokens = 0
        self._seen = set()
        # Keep no-id provider response objects alive for the lifetime of the
        # turn so CPython cannot recycle an object id and accidentally suppress
        # a later, distinct request with identical usage numbers.
        self._seen_roots = []

    @staticmethod
    def _get(value: Any, key: str, default=None):
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    @classmethod
    def _first(cls, value: Any, keys) -> Any:
        for key in keys:
            item = cls._get(value, key, None)
            if item is not None:
                return item
        return None

    @staticmethod
    def _as_int(value: Any) -> Optional[int]:
        if value is None or isinstance(value, bool):
            return None
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalize(cls, usage: Any) -> Optional[tuple[int, int, int]]:
        inp = cls._as_int(cls._first(usage, cls.INPUT_KEYS))
        out = cls._as_int(cls._first(usage, cls.OUTPUT_KEYS))
        total = cls._as_int(cls._first(usage, cls.TOTAL_KEYS))

        if inp is None and out is None and total is None:
            return None

        inp = int(inp or 0)
        out = int(out or 0)
        if total is None:
            total = inp + out

        # Some providers (notably Gemini) expose reasoning/thinking usage only
        # through total_token_count. Preserve the provider-reported turn total by
        # assigning every token above prompt/input usage to output usage.
        if total >= inp and total > inp + out:
            out = total - inp
        elif total < inp + out:
            total = inp + out

        if inp <= 0 and out <= 0 and total <= 0:
            return None
        return inp, out, total

    @classmethod
    def _response_id(cls, value: Any) -> str:
        """Find a stable provider response id without recursively walking payload text."""
        queue = [value]
        visited = set()
        for _ in range(12):
            if not queue:
                break
            current = queue.pop(0)
            if current is None:
                continue
            marker = id(current)
            if marker in visited:
                continue
            visited.add(marker)
            item = cls._first(current, cls.ID_KEYS)
            if item not in (None, ""):
                return str(item)
            for key in ("response", "raw"):
                nested = cls._get(current, key, None)
                if nested is not None:
                    queue.append(nested)
        return ""

    @classmethod
    def _usage_values(cls, value: Any):
        """Yield usage objects from common SDK/LlamaIndex response wrappers."""
        queue = [(value, 0)]
        visited = set()
        while queue:
            current, depth = queue.pop(0)
            if current is None or depth > 5:
                continue
            marker = id(current)
            if marker in visited:
                continue
            visited.add(marker)

            if cls._normalize(current) is not None:
                yield current

            for key in cls.USAGE_KEYS:
                nested = cls._get(current, key, None)
                if nested is not None:
                    queue.append((nested, depth + 1))
            for key in cls.WRAPPER_KEYS:
                nested = cls._get(current, key, None)
                if nested is not None:
                    queue.append((nested, depth + 1))

    def capture(self, value: Any, actor_id: str = "orchestrator") -> bool:
        """Add one completed provider request usage to the current turn aggregate."""
        # One capture() call represents one provider request boundary. A
        # LlamaIndex ChatResponse can expose that same request through several
        # nested usage objects (for example a raw stream delta plus merged
        # message.additional_kwargs). Never sum those nested views. Prefer the
        # most complete candidate, identified by the largest provider total.
        candidates = {
            normalized
            for usage in self._usage_values(value)
            if (normalized := self._normalize(usage)) is not None
        }
        if not candidates:
            return False
        inp, out, total = max(candidates, key=lambda item: (item[2], item[0] + item[1], item[0], item[1]))

        response_id = self._response_id(value)
        root_id = id(value)
        actor = str(actor_id or "orchestrator")
        if response_id:
            key = (actor, response_id, inp, out, total)
        else:
            # Provider adapters call capture at the raw/final response boundary.
            # Keep the root alive (below) so its identity remains unique until
            # the user turn ends.
            key = (actor, root_id, inp, out, total)
        if key in self._seen:
            return False

        self._seen.add(key)
        self.input_tokens += inp
        self.output_tokens += out
        if not response_id:
            self._seen_roots.append(value)
        try:
            self.runtime.verbose.log("TOKEN USAGE", {
                "input_tokens": inp,
                "output_tokens": out,
                "total_tokens": total,
                "turn_input_tokens": self.input_tokens,
                "turn_output_tokens": self.output_tokens,
            }, actor=actor)
        except Exception:
            pass
        return True

    @property
    def total_tokens(self) -> int:
        return int(self.input_tokens) + int(self.output_tokens)

    def apply_to_context(self) -> tuple[int, int, int]:
        """Commit the completed user-turn aggregate to the main CtxItem."""
        ctx = getattr(getattr(self.runtime, "context", None), "ctx", None)
        if ctx is not None:
            setter = getattr(ctx, "set_tokens", None)
            if callable(setter):
                setter(int(self.input_tokens), int(self.output_tokens))
            else:
                ctx.input_tokens = int(self.input_tokens)
                ctx.output_tokens = int(self.output_tokens)
                ctx.total_tokens = self.total_tokens
        return int(self.input_tokens), int(self.output_tokens), self.total_tokens
