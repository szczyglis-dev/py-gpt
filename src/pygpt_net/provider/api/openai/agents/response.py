#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 19:00:00                  #
# ================================================== #

import base64
import io
from typing import Tuple

from agents import HandoffOutputItem, ReasoningItem

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem

from openai.types.responses import (
    ResponseTextDeltaEvent,
    ResponseCreatedEvent,
    ResponseCodeInterpreterCallCodeDeltaEvent,
    ResponseOutputItemAddedEvent,
    ResponseCompletedEvent,
    ResponseOutputItemDoneEvent,
)

class StreamHandler:
    def __init__(
            self,
            window,
            bridge: ConnectionContext = None,
            message: str = None,
    ):
        self.window = window
        self.bridge = bridge
        self._buf = io.StringIO()
        self.begin = True
        self.response_id = None
        self.files = []
        self.finished = False
        self.files_handled = False
        self.code_block = False
        if message:
            self._buf.write(message)
            self.begin = False

    @property
    def buffer(self) -> str:
        return self._buf.getvalue()

    @buffer.setter
    def buffer(self, value: str):
        self._buf = io.StringIO()
        if value:
            self._buf.write(value)

    def reset(self):
        """Reset shared data"""
        self.response_id = None
        self.finished = False
        self.code_block = False

    def new(self):
        """Reset the stream handler for a new response in cycle"""
        self.reset()
        self.buffer = ""
        self.begin = True

    def to_buffer(self, text: str):
        """
        Append text to buffer

        :param text: str - text to append
        """
        self._buf.write(text)

    def _emit(self, ctx: CtxItem, text: str, flush: bool, buffer: bool):
        ctx.stream = text
        if flush:
            self.bridge.on_step(ctx, self.begin)
        if buffer:
            self._buf.write(text)
        self.begin = False

    def handle(
            self,
            event,
            ctx: CtxItem,
            flush: bool = True,
            buffer: bool = True
    ) -> Tuple[str, str]:
        """
        Unpack agent response and set context

        :param event: Event - event containing response data
        :param ctx: CtxItem - context item to set the response data
        :param flush: bool - whether to flush the output
        :param buffer: bool - whether to buffer the output
        :return: Final output string, response ID
        """
        if isinstance(event, ReasoningItem):
            print(
                f"\033[33m{event.summary[0].text}\033[0m", end="", flush=True
            )
        elif event.type == "raw_response_event":
            data = event.data

            if isinstance(data, ResponseCreatedEvent):
                self.response_id = data.response.id

            elif isinstance(data, ResponseTextDeltaEvent):
                s = data.delta
                if self.code_block:
                    s = "\n```\n" + s
                    self.code_block = False
                self._emit(ctx, s, flush, buffer)

            elif isinstance(data, ResponseOutputItemAddedEvent):
                if data.item.type == "code_interpreter_call":
                    self.code_block = True
                    s = "\n\n**Code interpreter**\n```python\n"
                    self._emit(ctx, s, flush, buffer)

            elif isinstance(data, ResponseOutputItemDoneEvent):
                if data.item.type == "image_generation_call":
                    img_path = self.window.core.image.gen_unique_path(ctx)
                    image_base64 = data.item.result
                    image_bytes = base64.b64decode(image_base64)
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    self.window.core.debug.info("[chat] Image generation call found")
                    ctx.images = [img_path]

            elif isinstance(data, ResponseCodeInterpreterCallCodeDeltaEvent):
                self._emit(ctx, data.delta, flush, buffer)

            elif isinstance(data, ResponseCompletedEvent):
                response = data.response
                for item in response.output:
                    if item.type == "message":
                        for content in item.content:
                            if content.annotations:
                                for annotation in content.annotations:
                                    if annotation.type == "url_citation":
                                        if ctx.urls is None:
                                            ctx.urls = []
                                        ctx.urls.append(annotation.url)
                                    elif annotation.type == "container_file_citation":
                                        self.files.append({
                                            "container_id": annotation.container_id,
                                            "file_id": annotation.file_id,
                                        })
                    elif item.type == "code_interpreter_call":
                        if self.code_block:
                            s = "\n```\n"
                            self.code_block = False
                            self._emit(ctx, s, flush, buffer)
                self.finished = True

        elif event.type == "run_item_stream_event":
            if isinstance(event.item, HandoffOutputItem):
                s = f"\n\n**Handoff to: {event.item.target_agent.name}**\n\n"
                self._emit(ctx, s, flush, buffer)

        if self.finished and not self.files_handled and self.files:
            self.files_handled = True
            self.window.core.debug.info("[chat] Container files found, downloading...")
            try:
                self.window.core.api.openai.container.download_files(ctx, self.files)
            except Exception as e:
                self.window.core.debug.error(f"[chat] Error downloading container files: {e}")

        return self.buffer, self.response_id