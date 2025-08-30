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

from pygpt_net.core.realtime.options import RealtimeOptions
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.model import ModelItem

from .live import GoogleLiveClient


class Realtime:
    def __init__(self, window=None):
        """
        Google GenAI API realtime controller

        :param window: Window instance
        """
        self.window = window
        self.handler = GoogleLiveClient(window)

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
        :param rt_signals: Optional RealtimeSignals
        :return: bool - True if realtime session started, False otherwise
        """
        # Enable live if config says so or the model suggests live/native-audio
        try:
            use_live = bool(self.window.core.config.get("google_audio.live", True))
        except Exception:
            use_live = True
        mid = (model.id or "").lower() if model else ""
        if use_live or "live" in mid or "native-audio" in mid:
            # Build realtime options
            mm = context.multimodal_ctx
            audio_bytes = getattr(mm, "audio_data", None) if mm and getattr(mm, "is_audio_input",
                                                                            False) else None
            audio_format = getattr(mm, "audio_format", None) if mm else None
            audio_rate = getattr(mm, "audio_rate", None) if mm else None

            # Voice
            voice_name = "Kore"
            try:
                v = self.window.core.plugins.get_option("audio_output", "google_genai_tts_voice")
                if v:
                    mapping = {"kore": "Kore", "puck": "Puck", "charon": "Charon", "verse": "Verse",
                               "legend": "Legend"}
                    voice_name = mapping.get(str(v).strip().lower(), str(v))
            except Exception:
                pass

            opts = RealtimeOptions(
                provider="google",
                model=model.id,
                system_prompt=context.system_prompt,
                prompt=context.prompt,
                voice=voice_name,
                audio_data=audio_bytes,
                audio_format=audio_format,
                audio_rate=audio_rate,
                vad=None,
                extra=extra or {},
                rt_signals=rt_signals,
            )

            # Start realtime worker via controller
            try:
                rt = self.window.controller.realtime.manager
                rt.start(context.ctx, opts)
                return True
            except Exception as e:
                self.window.core.debug.log(e)
                return False  # fallback to non-live path

    def shutdown(self):
        """Shutdown realtime loops"""
        self.handler.stop_loop_sync()

    def reset(self):
        """Close realtime session"""
        self.handler.close_session_sync()