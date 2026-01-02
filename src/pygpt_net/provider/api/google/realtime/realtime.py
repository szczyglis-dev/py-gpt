#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 19:00:00                  #
# ================================================== #

import json
from typing import Optional, Dict, Any

from pygpt_net.core.events import RealtimeEvent
from pygpt_net.core.realtime.options import RealtimeOptions
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.realtime.shared.session import extract_last_session_id
from pygpt_net.item.model import ModelItem

from .client import GoogleLiveClient


class Realtime:

    PROVIDER = "google"

    def __init__(self, window=None):
        """
        Google GenAI API realtime controller

        :param window: Window instance
        """
        self.window = window
        self.handler = GoogleLiveClient(window)
        self.prev_auto_turn = False
        self.prev_vad_silence = 2000
        self.prev_vad_prefix = 300

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
        # Build realtime options
        mm = context.multimodal_ctx
        audio_bytes = getattr(mm, "audio_data", None) if mm and getattr(mm, "is_audio_input", False) else None
        audio_format = getattr(mm, "audio_format", None) if mm else None
        audio_rate = getattr(mm, "audio_rate", None) if mm else None
        is_debug = self.window.core.config.get("log.realtime", False)
        auto_turn = self.window.core.config.get("audio.input.auto_turn", True)
        opt_vad_silence = self.window.core.config.get("audio.input.vad.silence", 2000)
        opt_vad_prefix = self.window.core.config.get("audio.input.vad.prefix", 300)

        # setup manager
        self.window.controller.realtime.set_current_active(self.PROVIDER)
        self.window.controller.realtime.set_busy()
        self.handler.set_debug(is_debug)

        # handle sub-reply (tool results from tool calls)
        if context.ctx.internal:
            if context.ctx.prev_ctx and context.ctx.prev_ctx.extra.get("prev_tool_calls"):
                tool_calls = context.ctx.prev_ctx.extra.get("prev_tool_calls", [])
                tool_call_id = None
                if isinstance(tool_calls, list) and len(tool_calls) > 0:
                    tool_call_id = tool_calls[0].get("call_id", "")  # get first call_id
                    if not tool_call_id:
                        tool_call_id = tool_calls[0].get("id", "")  # fallback to id
                if tool_call_id:
                    tool_results = context.ctx.input
                    try:
                        tool_results = json.loads(tool_results)
                    except Exception:
                        pass
                    self.handler.send_tool_results_sync({
                        tool_call_id: tool_results
                    })
                    return True  # do not start new session, just send tool results

        # update auto-turn in active session
        if (self.handler.is_session_active()
                and (auto_turn != self.prev_auto_turn
                     or opt_vad_silence != self.prev_vad_silence
                     or opt_vad_prefix != self.prev_vad_prefix)):
            self.handler.update_session_autoturn_sync(auto_turn, opt_vad_silence, opt_vad_prefix)

        # Tools
        tools = self.window.core.api.google.tools.prepare(model, context.external_functions)
        remote_tools = self.window.core.api.google.remote_tools.build_remote_tools(model)
        if tools:
            remote_tools = []  # in Google, remote tools are not allowed if function calling is used

        # if auto-turn is enabled and prompt is empty, update session and context only
        if auto_turn and self.handler.is_session_active() and (context.prompt.strip() == "" or context.prompt == "..."):
            self.handler.update_session_tools_sync(tools, remote_tools)
            self.handler.update_ctx(context.ctx)
            return True  # do not send new request if session is active

        # Last session ID
        last_session_id = extract_last_session_id(context.history)
        if is_debug:
            print("[realtime session] Last ID", last_session_id)

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

        # Options
        opts = RealtimeOptions(
            provider=self.PROVIDER,
            model=model.id,
            system_prompt=context.system_prompt,
            prompt=context.prompt,
            voice=voice_name,
            audio_data=audio_bytes,
            audio_format=audio_format,
            audio_rate=audio_rate,
            vad=None,
            extra=extra or {},
            tools=tools,
            remote_tools=remote_tools,
            rt_signals=rt_signals,
            rt_session_id=last_session_id,
            auto_turn=auto_turn,
            vad_end_silence_ms=opt_vad_silence,
            vad_prefix_padding_ms=opt_vad_prefix,
        )

        # Start or append to realtime session via manager
        try:
            if is_debug:
                print("[realtime] Starting session with options:", opts.to_dict())
            rt = self.window.controller.realtime.manager
            rt.start(context.ctx, opts)

            self.prev_auto_turn = auto_turn
            self.prev_vad_silence = opt_vad_silence
            self.prev_vad_prefix = opt_vad_prefix
            return True
        except Exception as e:
            self.window.core.debug.log(e)
            return False  # fallback to non-live path

    def handle_audio_input(self, event: RealtimeEvent):
        """
        Handle Realtime audio input event

        :param event: RealtimeEvent
        """
        self.handler.rt_handle_audio_input_sync(event)

    def manual_commit(self):
        """Manually commit audio input to realtime session"""
        self.handler.force_response_now_sync()

    def shutdown(self):
        """Shutdown realtime loops"""
        if self.handler.is_session_active():
            self.handler.close_session_sync()
        try:
            self.handler.stop_loop_sync()
        except Exception:
            pass

    def reset(self):
        """Close realtime session"""
        if self.handler.is_session_active():
            self.handler.close_session_sync()