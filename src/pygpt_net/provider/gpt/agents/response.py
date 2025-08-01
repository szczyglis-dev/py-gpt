#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 03:00:00                  #
# ================================================== #

import base64
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
        self.buffer = ""
        self.begin = True
        self.response_id = None
        self.files = []
        self.finished = False
        self.files_handled = False
        self.code_block = False
        if message:
            self.buffer = message
            self.begin = False

    def reset(self):
        # self.buffer = ""
        self.response_id = None
        self.files = []
        self.finished = False
        self.files_handled = False
        self.code_block = False

    def handle(self, event, ctx: CtxItem) -> Tuple[str, str]:
        """
        Unpack agent response and set context

        :param event: Event - event containing response data
        :param ctx: CtxItem - context item to set the response data
        :return: Final output string, response ID
        """
        img_path = self.window.core.image.gen_unique_path(ctx)
        is_image = False
        if isinstance(event, ReasoningItem):
            print(
                f"\033[33m{event.summary[0].text}\033[0m", end="", flush=True
            )  # Yellow for reasoning
            #ctx.stream = event.summary[0].text
            #self.on_step(ctx, self.begin)
            #self.begin = False
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseCreatedEvent):
            self.response_id = event.data.response.id
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            ctx.stream = event.data.delta
            if self.code_block:
                ctx.stream = "\n```\n" + ctx.stream
                self.code_block = False
            self.bridge.on_step(ctx, self.begin)
            self.buffer += ctx.stream
            self.begin = False
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseOutputItemAddedEvent):
            if event.data.item.type == "code_interpreter_call":
                self.code_block = True
                ctx.stream = "\n\n**Code interpreter**\n```python\n"
                self.bridge.on_step(ctx, self.begin)
                self.buffer += ctx.stream
                self.begin = False
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseOutputItemDoneEvent):
            if event.data.item.type == "image_generation_call":
                image_base64 = event.data.item.result
                image_bytes = base64.b64decode(image_base64)
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                is_image = True
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseCodeInterpreterCallCodeDeltaEvent):
            ctx.stream = event.data.delta
            self.bridge.on_step(ctx, self.begin)
            self.buffer += ctx.stream
            self.begin = False
        elif event.type == "raw_response_event" and isinstance(event.data, ResponseCompletedEvent):
            for item in event.data.response.output:
                if item.type == "message":
                    for content in item.content:
                        if content.annotations:
                            for annotation in content.annotations:
                                # url citation
                                if annotation.type == "url_citation":
                                    if ctx.urls is None:
                                        ctx.urls = []
                                    ctx.urls.append(annotation.url)
                                # container file citation
                                elif annotation.type == "container_file_citation":
                                    container_id = annotation.container_id
                                    file_id = annotation.file_id
                                    self.files.append({
                                        "container_id": container_id,
                                        "file_id": file_id,
                                    })
                elif item.type == "code_interpreter_call":
                    if self.code_block:
                        ctx.stream = "\n```\n"
                        self.code_block = False
                    self.bridge.on_step(ctx, self.begin)
                    self.buffer += ctx.stream
                    self.begin = False


            self.finished = True

        elif event.type == "run_item_stream_event":
            if isinstance(event.item, HandoffOutputItem):
                ctx.stream = f"\n\n**Handoff to: {event.item.target_agent.name}**\n\n"
                self.bridge.on_step(ctx, self.begin)
                self.buffer += ctx.stream
                self.begin = False

        # append images
        if is_image:
            self.window.core.debug.info("[chat] Image generation call found")
            ctx.images = [img_path]  # save image path to ctx

        # if files from container are found, download them and append to ctx
        if self.finished and not self.files_handled and self.files:
            self.files_handled = True
            self.window.core.debug.info("[chat] Container files found, downloading...")
            try:
                self.window.core.gpt.container.download_files(ctx, self.files)
            except Exception as e:
                self.window.core.debug.error(f"[chat] Error downloading container files: {e}")

        return self.buffer, self.response_id