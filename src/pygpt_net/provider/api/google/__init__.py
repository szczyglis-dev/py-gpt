#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 12:22:00                  #
# ================================================== #

import os
from functools import cached_property
from typing import Optional, Dict, Any

from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_IMAGE,
    MODE_RESEARCH,
    MODE_COMPUTER,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types.chunk import ChunkType
from pygpt_net.item.model import ModelItem

class ApiGoogle:
    def __init__(self, window=None):
        """
        Google GenAI API SDK wrapper

        :param window: Window instance
        """
        self.window = window
        self.client = None
        self.locked = False
        self.last_client_args: Optional[Dict[str, Any]] = None

    @cached_property
    def chat(self):
        from .chat import Chat
        return Chat(self.window)

    @cached_property
    def vision(self):
        from .vision import Vision
        return Vision(self.window)

    @cached_property
    def tools(self):
        from .tools import Tools
        return Tools(self.window)

    @cached_property
    def audio(self):
        from .audio import Audio
        return Audio(self.window)

    @cached_property
    def image(self):
        from .image import Image
        return Image(self.window)

    @cached_property
    def realtime(self):
        from .realtime import Realtime
        return Realtime(self.window)

    @cached_property
    def video(self):
        from .video import Video
        return Video(self.window)

    @cached_property
    def music(self):
        from .music import Music
        return Music(self.window)

    @cached_property
    def computer(self):
        from .computer import Computer
        return Computer(self.window)

    @cached_property
    def remote_tools(self):
        from .remote_tools import RemoteTools
        return RemoteTools(self.window)

    @cached_property
    def store(self):
        from .store import Store
        return Store(self.window)

    def get_client(
            self,
            mode: str = MODE_CHAT,
            model: ModelItem = None
    ):
        """
        Get or create Google GenAI client

        :param mode: Mode (chat, completion, image, etc.)
        :param model: ModelItem
        :return: genai.Client instance
        """
        from google import genai
        from google.genai import types as gtypes

        if not model:
            model = ModelItem()
            model.provider = "google"
        args = self.window.core.models.prepare_client_args(mode, model)
        filtered = {}
        if args.get("api_key"):
            filtered["api_key"] = args["api_key"]
        if args.get("api_proxy"):
            http_options = gtypes.HttpOptions(
                client_args={"proxy": args["api_proxy"]},
                async_client_args={"proxy": args["api_proxy"]},
            )
            filtered["http_options"] = http_options

        # Setup Gemini Enterprise Agent Platform / Vertex backend. Keep the
        # legacy ``vertexai`` client flag here because google-genai 2.x still
        # supports it as an alias and this also preserves compatibility with
        # older SDK releases used by existing PyGPT installations.
        use_vertex = self.setup_env()
        if use_vertex:
            filtered["vertexai"] = True
            filtered["project"] = os.environ.get("GOOGLE_CLOUD_PROJECT")
            filtered["location"] = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            # filtered["http_options"] = gtypes.HttpOptions(api_version="v1")

        # use previous client if args are the same
        if self.client and self.last_client_args == filtered:
            return self.client

        self.last_client_args = filtered
        self.window.core.api.logger.log_input(
            type="client.init", provider="google", kwargs=filtered,
            model=getattr(model, "id", None), path="genai.Client",
        )
        self.client = genai.Client(**filtered)

        return self.client

    def call(
            self,
            context: BridgeContext,
            extra: dict = None,
            rt_signals = None
    ) -> bool:
        """
        Make an API call to Google GenAI

        :param context: BridgeContext
        :param extra: Extra parameters
        :param rt_signals: Realtime signals for audio streaming
        :return: True if successful, False otherwise
        """
        mode = context.mode
        model = context.model
        stream = context.stream
        ctx = context.ctx
        ai_name = ctx.output_name if ctx else "assistant"
        ctx.chunk_type = ChunkType.GOOGLE

        used_tokens = 0
        response = None

        if mode in [
            MODE_COMPLETION,
            MODE_CHAT,
            MODE_AUDIO,
            MODE_RESEARCH,
            MODE_COMPUTER
        ]:

            # Live API for audio streaming
            if mode == MODE_AUDIO and stream:
                is_realtime = self.realtime.begin(
                    context=context,
                    model=model,
                    extra=extra or {},
                    rt_signals=rt_signals
                )
                if is_realtime:
                    return True

            if mode == MODE_RESEARCH:
                ctx.chunk_type = ChunkType.GOOGLE_INTERACTIONS_API  # use interactions API for research

            response = self.chat.send(context=context, extra=extra)
            used_tokens = self.chat.get_used_tokens()
            if ctx:
                self.vision.append_images(ctx)

        elif mode == MODE_IMAGE:
            # Route to video / music / image based on selected model.
            media_mode = self.window.controller.media.get_mode()
            if media_mode == "video":
                if context.model.is_video_output():
                    return self.video.generate(context=context, extra=extra)  # veo, etc.
            elif media_mode == "music":
                # Lyria / music models
                if self.music.is_music_model(model.id if model else ""):
                    return self.music.generate(context=context, extra=extra)   # lyria, etc.
            elif media_mode == "image":
                # Default: image
                return self.image.generate(context=context, extra=extra)       # imagen, etc.

        elif mode == MODE_ASSISTANT:
            return False  # not implemented for Google

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

    def redirect_call(
            self,
            context: BridgeContext,
            extra: dict = None
    ) -> str:
        """
        Redirect quick call to standard call and return the output text

        :param context: BridgeContext
        :param extra: Extra parameters
        :return: Output text
        """
        context.stream = False
        context.mode = MODE_CHAT
        self.locked = True
        self.call(context, extra)
        self.locked = False
        return context.ctx.output

    def quick_call(
            self,
            context: BridgeContext,
            extra: dict = None
    ) -> str:
        """
        Make a quick API call to Google GenAI and return the output text

        :param context: BridgeContext
        :param extra: Extra parameters
        :return: Output text
        """
        if context.request:
            return self.redirect_call(context, extra)

        self.locked = True
        try:
            ctx = context.ctx
            prompt = context.prompt
            system_prompt = context.system_prompt
            history = context.history
            functions = context.external_functions
            model = context.model or self.window.core.models.from_defaults()

            client = self.get_client(MODE_CHAT, model)
            tools = self.tools.prepare(model, functions)

            """
            # with remote tools
            base_tools = self.tools.prepare(model, functions)
            remote_tools = self.remote_tools.build_remote_tools(model)
            tools = (base_tools or []) + (remote_tools or [])
            """

            inputs = self.chat.build_input(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                history=history,
                attachments=context.attachments,
                multimodal_ctx=context.multimodal_ctx,
            )
            from google import genai

            cfg = genai.types.GenerateContentConfig(
                max_output_tokens=context.max_tokens if context.max_tokens else None,
                system_instruction=system_prompt if system_prompt else None,
                tools=tools if tools else None,
            )
            request_kwargs = {
                "model": model.id,
                "contents": inputs,
                "config": cfg,
            }
            self.window.core.api.logger.log_input(
                type="models.generate_content", provider="google",
                kwargs=request_kwargs, input=inputs, history=history, extra=extra,
                model=model.id, path="client.models.generate_content",
            )
            resp = client.models.generate_content(**request_kwargs)
            self.window.core.api.logger.log_output(
                type="models.generate_content", provider="google", output=resp, model=model.id,
            )

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

    def setup_env(self) -> bool:
        """
        Setup environment variables for Google GenAI Enterprise/Vertex backend.

        - GOOGLE_GENAI_USE_ENTERPRISE
        - GOOGLE_GENAI_USE_VERTEXAI
        - GOOGLE_CLOUD_PROJECT
        - GOOGLE_CLOUD_LOCATION
        - GOOGLE_APPLICATION_CREDENTIALS

        :return: bool: True if VertexAI is used, False otherwise
        """
        config = self.window.core.config
        use_vertex = False
        if config.get("api_native_google.use_vertex", False):
            use_vertex = True
            # 2.x prefers the Enterprise name. Keep the legacy alias in sync
            # for google-genai 1.x and integrations which still inspect it.
            os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "1"
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
            os.environ["GOOGLE_CLOUD_PROJECT"] = config.get("api_native_google.cloud_project", "")
            os.environ["GOOGLE_CLOUD_LOCATION"] = config.get("api_native_google.cloud_location", "us-central1")
            if config.get("api_native_google.app_credentials", ""):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get("api_native_google.app_credentials", "")
        else:
            if os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE"):
                del os.environ["GOOGLE_GENAI_USE_ENTERPRISE"]
            if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
                del os.environ["GOOGLE_GENAI_USE_VERTEXAI"]
            if os.environ.get("GOOGLE_CLOUD_PROJECT"):
                del os.environ["GOOGLE_CLOUD_PROJECT"]
            if os.environ.get("GOOGLE_CLOUD_LOCATION"):
                del os.environ["GOOGLE_CLOUD_LOCATION"]
            if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        return use_vertex

    def stop(self):
        """On global event stop"""
        pass

    def close(self):
        """Close Google client"""
        if self.locked:
            return
        if self.client is not None:
            try:
                pass
                # self.client.close()
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error closing Google client:", e)

    def safe_close(self):
        """Close client"""
        if self.locked:
            return
        if self.client is not None:
            try:
                self.client.close()
                self.client = None
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error closing client:", e)