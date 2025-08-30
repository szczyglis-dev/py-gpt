#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.realtime.options import RealtimeOptions
from pygpt_net.item.model import ModelItem

from .live import OpenAIRealtimeClient

class Realtime:
    def __init__(self, window=None):
        """
        OpenAI API realtime controller

        :param window: Window instance
        """
        self.window = window
        self.handler = OpenAIRealtimeClient(window)

    def begin(
            self,
            context: BridgeContext,
            model: Optional[ModelItem] = None,
            extra: Optional[Dict[str, Any]] = None,
            rt_signals=None
    ) -> bool:
        """
        Begin realtime session if applicable

        :param context: BridgeContext
        :param model: Optional[ModelItem]
        :param extra: Optional dict with extra parameters
        :param rt_signals: RealtimeSignals
        :return: True if realtime session started, False otherwise
        """
        use_rt = True
        try:
            use_rt = bool(self.window.core.config.get("openai_audio.realtime", True))
        except Exception:
            pass

        if use_rt:
            mm = context.multimodal_ctx
            audio_bytes = getattr(mm, "audio_data", None) if mm and getattr(mm, "is_audio_input", False) else None
            audio_format = getattr(mm, "audio_format", None) if mm else None
            audio_rate = getattr(mm, "audio_rate", None) if mm else None

            # Voice
            voice = "alloy"
            try:
                v = self.window.core.plugins.get_option("audio_output", "openai_voice")
                if v:
                    voice = str(v)
            except Exception:
                pass

            opts = RealtimeOptions(
                provider="openai",
                model=context.model.id,
                system_prompt=context.system_prompt,
                prompt=context.prompt,
                voice=voice,
                audio_data=audio_bytes,
                audio_format=audio_format,
                audio_rate=audio_rate,
                vad="server_vad",  # optional; remove if you prefer manual commit
                extra=extra or {},
                rt_signals=rt_signals,
            )

            # Start Realtime manager
            rt = self.window.controller.realtime.manager
            rt.start(context.ctx, opts)
            return True

        return False

    def shutdown(self):
        """Shutdown realtime loops"""
        self.handler.stop_loop_sync()

    def reset(self):
        """Close realtime session"""
        self.handler.close_session_sync()