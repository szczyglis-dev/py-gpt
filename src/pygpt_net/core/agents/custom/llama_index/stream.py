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
import io
from typing import Tuple

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem


class LIStreamHandler:
    """
    Minimal streaming helper for LlamaIndex events, API-compatible with your usage:
    - reset(), new(), to_buffer(text)
    - begin flag
    - handle_token(delta, ctx) -> returns (buffer, None)
    """
    def __init__(self, bridge: ConnectionContext):
        self.bridge = bridge
        self._buf = io.StringIO()
        self.begin = True

    @property
    def buffer(self) -> str:
        return self._buf.getvalue()

    def reset(self):
        self._buf = io.StringIO()

    def new(self):
        self.reset()
        self.begin = True

    def to_buffer(self, text: str):
        if text:
            self._buf.write(text)

    def handle_token(self, delta: str, ctx: CtxItem, flush: bool = True, buffer: bool = True) -> Tuple[str, None]:
        if not delta:
            return self.buffer, None
        ctx.stream = delta
        if flush:
            self.bridge.on_step(ctx, self.begin)
        if buffer:
            self._buf.write(delta)
        self.begin = False
        return self.buffer, None