#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
import re
import json
from typing import Optional, Tuple, Any

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.api.openai.agents.response import StreamHandler

from openai.types.responses import (
    ResponseTextDeltaEvent,
    ResponseCreatedEvent,
    ResponseCompletedEvent,
)

from .logging import Logger, NullLogger


class DelayedRouterStreamer:
    """
    Delayed streaming for multi-output router agents:
    - Collect tokens silently (no UI flush).
    - After completion, reveal only parsed `content` to UI.
    """
    def __init__(self, window, bridge: ConnectionContext):
        self.window = window
        self.bridge = bridge
        self.handler = StreamHandler(window, bridge)
        self._last_response_id: Optional[str] = None

    def reset(self) -> None:
        self.handler.reset()
        self.handler.buffer = ""
        self._last_response_id = None

    def handle_event(self, event: Any, ctx: CtxItem) -> Tuple[str, Optional[str]]:
        text, resp_id = self.handler.handle(event, ctx, flush=False, buffer=True)
        if resp_id:
            self._last_response_id = resp_id
        return self.handler.buffer, self._last_response_id

    @property
    def buffer(self) -> str:
        return self.handler.buffer

    @property
    def last_response_id(self) -> Optional[str]:
        return self._last_response_id


class RealtimeRouterStreamer:
    """
    Realtime streaming for multi-output router agents:
    - Detect `"content": "<...>"` in streamed JSON and emit decoded content incrementally to UI.
    - After completion, caller parses the final route from full buffer.
    """
    CONTENT_PATTERN = re.compile(r'"content"\s*:\s*"')

    def __init__(
        self,
        window,
        bridge: ConnectionContext,
        handler: Optional[StreamHandler] = None,
        buffer_to_handler: bool = True,
        logger: Optional[Logger] = None,
    ):
        self.window = window
        self.bridge = bridge
        self.handler = handler
        self.buffer_to_handler = buffer_to_handler
        self.logger = logger or NullLogger()

        self._raw: str = ""
        self._last_response_id: Optional[str] = None

        self._content_started: bool = False
        self._content_closed: bool = False
        self._content_start_idx: int = -1
        self._content_raw: str = ""
        self._content_decoded: str = ""

    def reset(self) -> None:
        self._raw = ""
        self._last_response_id = None
        self._content_started = False
        self._content_closed = False
        self._content_start_idx = -1
        self._content_raw = ""
        self._content_decoded = ""

    def handle_event(self, event: Any, ctx: CtxItem) -> None:
        if event.type != "raw_response_event":
            return

        data = event.data
        if isinstance(data, ResponseCreatedEvent):
            self._last_response_id = data.response.id
            return

        if isinstance(data, ResponseTextDeltaEvent):
            delta = data.delta or ""
            if not delta:
                return
            prev_len = len(self._raw)
            self._raw += delta

            if not self._content_started:
                m = self.CONTENT_PATTERN.search(self._raw)
                if m:
                    self._content_started = True
                    self._content_start_idx = m.end()
                    self.logger.debug("[router-realtime] content field detected in stream.")
                    if len(self._raw) > self._content_start_idx:
                        self._process_new_content(ctx)
                return

            if self._content_started and not self._content_closed:
                self._process_new_content(ctx)
            return

        if isinstance(data, ResponseCompletedEvent):
            if self._content_started:
                self.logger.debug("[router-realtime] stream completed; final JSON will be parsed by runner.")
            return

    def _process_new_content(self, ctx: CtxItem) -> None:
        sub = self._raw[self._content_start_idx:]
        close_idx = self._find_unescaped_quote(sub)
        if close_idx is not None:
            content_portion = sub[:close_idx]
            self._content_closed = True
            self.logger.debug("[router-realtime] content field closed in stream.")
        else:
            content_portion = sub

        new_raw_piece = content_portion[len(self._content_raw):]
        if not new_raw_piece:
            return

        self._content_raw += new_raw_piece

        try:
            decoded_full: str = json.loads(f'"{self._content_raw}"')
            new_suffix = decoded_full[len(self._content_decoded):]
            if new_suffix:
                ctx.stream = new_suffix
                self.bridge.on_step(ctx, False)
                if self.handler is not None and self.buffer_to_handler:
                    self.handler.to_buffer(new_suffix)
                self._content_decoded = decoded_full
        except Exception:
            # wait for more tokens
            pass

    @staticmethod
    def _find_unescaped_quote(s: str) -> Optional[int]:
        i = 0
        while i < len(s):
            if s[i] == '"':
                j = i - 1
                bs = 0
                while j >= 0 and s[j] == '\\':
                    bs += 1
                    j -= 1
                if bs % 2 == 0:
                    return i
            i += 1
        return None

    @property
    def buffer(self) -> str:
        return self._raw

    @property
    def last_response_id(self) -> Optional[str]:
        return self._last_response_id