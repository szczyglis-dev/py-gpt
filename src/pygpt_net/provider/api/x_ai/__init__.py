#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 17:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any

import os
import json

from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_IMAGE,
    MODE_RESEARCH,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types.chunk import ChunkType
from pygpt_net.item.model import ModelItem

import xai_sdk

from .chat import Chat
from .vision import Vision
from .tools import Tools
from .audio import Audio
from .image import Image
from .remote import Remote


class ApiXAI:
    def __init__(self, window=None):
        """
        xAI (Grok) Python SDK wrapper.

        :param window: Window instance
        """
        self.window = window
        self.chat = Chat(window)
        self.vision = Vision(window)
        self.tools = Tools(window)
        self.audio = Audio(window)
        self.image = Image(window)
        self.remote = Remote(window)  # Live Search builder
        self.client: Optional[xai_sdk.Client] = None
        self.locked = False
        self.last_client_args: Optional[Dict[str, Any]] = None

    def get_client(
            self,
            mode: str = MODE_CHAT,
            model: ModelItem = None
    ) -> xai_sdk.Client:
        """
        Get or create xAI client.

        - Reads api_key from config or XAI_API_KEY env.
        - Caches the client instance.

        :param mode: One of MODE_*
        :param model: ModelItem (optional, not used currently)
        :return: xai_sdk.Client
        """
        if self.client is not None:
            return self.client

        cfg = self.window.core.config
        api_key = cfg.get("api_key_xai") or os.environ.get("XAI_API_KEY") or ""
        timeout = cfg.get("api_native_xai.timeout")  # optional
        proxy = cfg.get("api_proxy") or ""
        if not cfg.get("api_proxy.enabled"):
            proxy = ""

        kwargs: Dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if timeout is not None:
            # Official SDK supports setting a global timeout on client init.
            kwargs["timeout"] = timeout
        if proxy:
            kwargs["channel_options"] = []
            kwargs["channel_options"].append(("grpc.http_proxy", proxy))

        self.client = xai_sdk.Client(**kwargs)
        return self.client

    def call(
            self,
            context: BridgeContext,
            extra: dict = None,
            rt_signals=None
    ) -> bool:
        """
        Make an API call to xAI.

        Supports chat (stream/non-stream), images (via REST),
        and function-calling. Audio is not available in public xAI SDK at this time.

        :param context: BridgeContext
        :param extra: Extra params (not used)
        :param rt_signals: Realtime signals (not used)
        :return: True on success, False on error
        """
        mode = context.mode
        stream = context.stream
        ctx = context.ctx
        ai_name = (ctx.output_name if ctx else "assistant")
        used_tokens = 0
        response = None
        ctx.chunk_type = ChunkType.XAI_SDK

        if mode in (
                MODE_COMPLETION,
                MODE_CHAT,
                MODE_AUDIO,
                MODE_RESEARCH
        ):
            # There is no public realtime audio in SDK; treat MODE_AUDIO as chat (TTS not supported).
            response = self.chat.send(context=context, extra=extra)
            used_tokens = self.chat.get_used_tokens()
            if ctx:
                self.vision.append_images(ctx)

        elif mode == MODE_IMAGE:
            # Image generation via REST /v1/images/generations (OpenAI-compatible)
            return self.image.generate(context=context, extra=extra)

        elif mode == MODE_ASSISTANT:
            return False  # not implemented for xAI

        if stream:
            if ctx:
                ctx.stream = response
                ctx.set_output("", ai_name)
                ctx.input_tokens = used_tokens
            return True

        if response is None:
            return False

        if isinstance(response, dict) and "error" in response:
            return False

        if ctx:
            ctx.ai_name = ai_name
            self.chat.unpack_response(context.mode, response, ctx)
            try:
                for tc in getattr(ctx, "tool_calls", []) or []:
                    fn = tc.get("function") or {}
                    args = fn.get("arguments")
                    if isinstance(args, str):
                        try:
                            fn["arguments"] = json.loads(args)
                        except Exception:
                            fn["arguments"] = {}
            except Exception:
                pass
        return True

    def quick_call(
            self,
            context: BridgeContext,
            extra: dict = None
    ) -> str:
        """
        Quick non-streaming xAI chat call and return output text.

        If context.request is set, makes a full call() instead (for consistency).

        :param context: BridgeContext
        :param extra: Extra params (not used)
        :return: Output text or "" on error
        """
        if context.request:
            context.stream = False
            context.mode = MODE_CHAT
            self.locked = True
            self.call(context, extra)
            self.locked = False
            return context.ctx.output

        self.locked = True
        try:
            ctx = context.ctx
            prompt = context.prompt
            system_prompt = context.system_prompt
            temperature = context.temperature
            history = context.history
            functions = context.external_functions
            model = context.model or self.window.core.models.from_defaults()

            tools = self.tools.prepare(functions)

            # If tools are present, prefer non-streaming HTTP Chat Completions path to extract tool calls reliably.
            # Otherwise use native SDK chat.sample().
            if tools:
                out, calls, citations, usage  = self.chat.call_http_nonstream(
                    model=model.id,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history=history,
                    attachments=context.attachments,
                    multimodal_ctx=context.multimodal_ctx,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=context.max_tokens,
                )
                if ctx:
                    if calls:
                        ctx.tool_calls = calls
                return out or ""

            # Native SDK path (no tools)
            client = self.get_client(MODE_CHAT, model)
            messages = self.chat.build_messages(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                history=history,
                attachments=context.attachments,
                multimodal_ctx=context.multimodal_ctx,
            )
            chat = client.chat.create(model=model.id, messages=messages)
            resp = chat.sample()
            return getattr(resp, "content", "") or ""
        except Exception as e:
            self.window.core.debug.log(e)
            return ""
        finally:
            self.locked = False

    def stop(self):
        """On global event stop."""
        pass

    def close(self):
        """Close xAI client."""
        if self.locked:
            return
        self.client = None  # xai-sdk gRPC channels close on GC; explicit close not exposed.

    def safe_close(self):
        """Close client."""
        if self.locked:
            return
        self.client = None