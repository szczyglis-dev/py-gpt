#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 14:55:00                  #
# ================================================== #

from __future__ import annotations

import base64
import io
import json
from typing import Callable, Optional, Tuple

from openai.types.responses import (
    ResponseTextDeltaEvent,
    ResponseCreatedEvent,
    ResponseCodeInterpreterCallCodeDeltaEvent,
    ResponseOutputItemAddedEvent,
    ResponseCompletedEvent,
    ResponseOutputItemDoneEvent,
)

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.api.openai.agents.response import StreamHandler

class SupervisorStreamHandler(StreamHandler):
    """
    Stream handler that filters JSON from Supervisor output during streaming.
    - Pass-through normal text.
    - Suppress raw JSON (both ```json fenced and bare {...}).
    - When JSON finishes, parse and emit only the human-friendly text via `json_to_text`.
    """
    def __init__(
        self,
        window,
        bridge: ConnectionContext = None,
        message: str = None,
        json_to_text: Optional[Callable[[dict], str]] = None,
    ):
        super().__init__(window, bridge, message)
        self.json_to_text = json_to_text or (lambda d: json.dumps(d, ensure_ascii=False))
        self._json_fenced = False
        self._json_buf = io.StringIO()
        self._json_in_braces = False
        self._brace_depth = 0
        self._in_string = False
        self._escape = False

    def _emit_text(self, ctx: CtxItem, text: str, flush: bool, buffer: bool):
        if not text:
            return
        self._emit(ctx, text, flush, buffer)

    def _flush_json(self, ctx: CtxItem, flush: bool, buffer: bool):
        """
        Parse collected JSON and emit only formatted text; reset state.
        """
        raw_json = self._json_buf.getvalue().strip()
        self._json_buf = io.StringIO()
        self._json_fenced = False
        self._json_in_braces = False
        self._brace_depth = 0
        self._in_string = False
        self._escape = False

        if not raw_json:
            return
        try:
            data = json.loads(raw_json)
            out = self.json_to_text(data) or ""
        except Exception:
            # Fallback: if parsing failed, do not leak JSON; stay silent
            out = ""
        if out:
            self._emit_text(ctx, out, flush, buffer)

    def _handle_text_delta(self, s: str, ctx: CtxItem, flush: bool, buffer: bool):
        """
        Filter JSON while streaming; emit only non-JSON text or parsed JSON text.
        """
        i = 0
        n = len(s)
        while i < n:
            # Detect fenced JSON start
            if not self._json_fenced and not self._json_in_braces and s.startswith("```json", i):
                # Emit any text before the fence
                # (there shouldn't be in this branch because we check exact start, but keep safe)
                i += len("```json")
                self._json_fenced = True
                # Skip possible newline after fence
                if i < n and s[i] == '\n':
                    i += 1
                continue

            # Detect fenced JSON end
            if self._json_fenced and s.startswith("```", i):
                # Flush JSON collected so far
                self._flush_json(ctx, flush, buffer)
                i += len("```")
                # Optional newline after closing fence
                if i < n and s[i] == '\n':
                    i += 1
                continue

            # While inside fenced JSON -> buffer and continue
            if self._json_fenced:
                self._json_buf.write(s[i])
                i += 1
                continue

            # Bare JSON detection (naive but effective for supervisor outputs)
            if not self._json_in_braces and s[i] == "{":
                self._json_in_braces = True
                self._brace_depth = 1
                self._in_string = False
                self._escape = False
                self._json_buf.write("{")
                i += 1
                continue

            if self._json_in_braces:
                ch = s[i]
                # Basic JSON string/escape handling
                if ch == '"' and not self._escape:
                    self._in_string = not self._in_string
                if ch == "\\" and not self._escape:
                    self._escape = True
                else:
                    self._escape = False
                if not self._in_string:
                    if ch == "{":
                        self._brace_depth += 1
                    elif ch == "}":
                        self._brace_depth -= 1
                self._json_buf.write(ch)
                i += 1
                if self._brace_depth == 0:
                    # JSON closed -> flush parsed text
                    self._flush_json(ctx, flush, buffer)
                continue

            # Normal text path
            # Accumulate until potential fenced start to avoid splitting too often
            next_fence = s.find("```json", i)
            next_bare = s.find("{", i)
            cut = n
            candidates = [x for x in (next_fence, next_bare) if x != -1]
            if candidates:
                cut = min(candidates)
            chunk = s[i:cut]
            if chunk:
                self._emit_text(ctx, chunk, flush, buffer)
            i = cut if cut != n else n

    def handle(
        self,
        event,
        ctx: CtxItem,
        flush: bool = True,
        buffer: bool = True
    ) -> Tuple[str, str]:
        """
        Override StreamHandler.handle to filter JSON in text deltas.
        For non-text events, fallback to parent handler.
        """
        # ReasoningItem path remains the same (parent prints to stdout), keep parent behavior.

        if getattr(event, "type", None) == "raw_response_event":
            data = event.data

            if isinstance(data, ResponseCreatedEvent):
                self.response_id = data.response.id
                return self.buffer, self.response_id

            if isinstance(data, ResponseTextDeltaEvent):
                # Filter JSON while streaming
                delta = data.delta or ""
                # If a code_interpreter block was started previously, render fence first
                if self.code_block:
                    self._emit_text(ctx, "\n```\n", flush, buffer)
                    self.code_block = False
                self._handle_text_delta(delta, ctx, flush, buffer)
                return self.buffer, self.response_id

            if isinstance(data, ResponseOutputItemAddedEvent):
                if data.item.type == "code_interpreter_call":
                    self.code_block = True
                    s = "\n\n**Code interpreter**\n```python\n"
                    self._emit_text(ctx, s, flush, buffer)
                return self.buffer, self.response_id

            if isinstance(data, ResponseOutputItemDoneEvent):
                if data.item.type == "image_generation_call":
                    img_path = self.window.core.image.gen_unique_path(ctx)
                    image_base64 = data.item.result
                    image_bytes = base64.b64decode(image_base64)
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    self.window.core.filesystem.materialize_runtime_artifact(img_path, ctx=ctx)
                    self.window.core.debug.info("[chat] Image generation call found")
                    ctx.images = [img_path]
                return self.buffer, self.response_id

            if isinstance(data, ResponseCodeInterpreterCallCodeDeltaEvent):
                self._emit_text(ctx, data.delta or "", flush, buffer)
                return self.buffer, self.response_id

            if isinstance(data, ResponseCompletedEvent):
                # If we are still buffering JSON, flush it now (emit parsed text only)
                if self._json_fenced or self._json_in_braces:
                    self._flush_json(ctx, flush, buffer)
                # Mark finished so parent downloader logic (files) may trigger if needed
                self.finished = True
                return self.buffer, self.response_id

        # Handoff / other events: fallback to parent, but it won't print JSON since we already filtered in text deltas
        return super().handle(event, ctx, flush, buffer)
