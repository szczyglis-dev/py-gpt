#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any

import anthropic
from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_IMAGE,
    MODE_RESEARCH, MODE_COMPUTER,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types.chunk import ChunkType
from pygpt_net.item.model import ModelItem

from .chat import Chat
from .tools import Tools
from .vision import Vision
from .audio import Audio
from .image import Image
from .remote_tools import RemoteTools
from .computer import Computer


class ApiAnthropic:
    def __init__(self, window=None):
        """
        Anthropic Messages API SDK wrapper

        :param window: Window instance
        """
        self.window = window
        self.chat = Chat(window)
        self.tools = Tools(window)
        self.vision = Vision(window)
        self.audio = Audio(window)   # stub helpers (no official audio out/in in SDK as of now)
        self.image = Image(window)   # stub: no image generation in Anthropic
        self.remote_tools = RemoteTools(window)
        self.computer = Computer(window)
        self.client: Optional[anthropic.Anthropic] = None
        self.locked = False
        self.last_client_args: Optional[Dict[str, Any]] = None

    def get_client(
            self,
            mode: str = MODE_CHAT,
            model: ModelItem = None,
    ) -> anthropic.Anthropic:
        """
        Get or create Anthropic client

        :param mode: Mode (chat, completion, image, etc.)
        :param model: ModelItem
        :return: anthropic.Anthropic instance
        """
        # Build minimal args from app config
        args = self.window.core.models.prepare_client_args(mode, model)
        filtered = {}
        if args.get("api_key"):
            filtered["api_key"] = args["api_key"]
        if args.get("api_proxy"):
            filtered["api_proxy"] = args["api_proxy"]

        # Optionally honor custom base_url if present in config (advanced)
        # base_url = self.window.core.config.get("api_native_anthropic.base_url", "").strip()
        # if base_url:
            # filtered["base_url"] = base_url

        # Keep a fresh client per call; Anthropic client is lightweight
        return anthropic.Anthropic(**filtered)

    def call(
            self,
            context: BridgeContext,
            extra: dict = None,
            rt_signals=None,   # unused for Anthropic
    ) -> bool:
        """
        Make an API call to Anthropic Messages API

        :param context: BridgeContext
        :param extra: Extra parameters
        :param rt_signals: Not used (no realtime Voice API)
        :return: True if successful, False otherwise
        """
        mode = context.mode
        model = context.model
        stream = context.stream
        ctx = context.ctx
        ai_name = ctx.output_name if ctx else "assistant"
        used_tokens = 0
        response = None
        ctx.chunk_type = ChunkType.ANTHROPIC

        if mode in (
                MODE_COMPLETION,
                MODE_CHAT,
                MODE_AUDIO,
                MODE_RESEARCH,
                MODE_COMPUTER
        ):
            # MODE_AUDIO fallback: treat as normal chat (no native audio API)
            response = self.chat.send(context=context, extra=extra)
            used_tokens = self.chat.get_used_tokens()
            if ctx:
                self.vision.append_images(ctx)

        elif mode == MODE_IMAGE:
            # Anthropic does not support image generation – only vision (image input in chat)
            return self.image.generate(context=context, extra=extra)  # always returns False

        elif mode == MODE_ASSISTANT:
            return False  # not implemented for Anthropic

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
            self.chat.unpack_response(mode, response, ctx)
            try:
                import json
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
        Make a quick API call to Anthropic and return the output text

        :param context: BridgeContext
        :param extra: Extra parameters
        :return: Output text
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

            client = self.get_client(MODE_CHAT, model)
            tools = self.tools.get_all_tools(model, functions)

            inputs = self.chat.build_input(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                history=history,
                attachments=context.attachments,
                multimodal_ctx=context.multimodal_ctx,
            )

            # Anthropic params
            params: Dict[str, Any] = {
                "model": model.id,
                "max_tokens": context.max_tokens if context.max_tokens else 1024,
                "messages": inputs,
            }
            if system_prompt:
                params["system"] = system_prompt
            if temperature is not None:
                params["temperature"] = temperature
            if tools:  # only include when non-empty list
                params["tools"] = tools

            resp = client.messages.create(**params)

            if ctx:
                calls = self.chat.extract_tool_calls(resp)
                if calls:
                    ctx.tool_calls = calls
            return self.chat.extract_text(resp)
        except Exception as e:
            self.window.core.debug.log(e)
            return ""
        finally:
            self.locked = False

    def stop(self):
        """On global event stop (no-op for Anthropic)"""
        pass

    def close(self):
        """Close client (no persistent resources to close)"""
        if self.locked:
            return
        self.client = None

    def safe_close(self):
        """Close client (safe)"""
        if self.locked:
            return
        self.client = None