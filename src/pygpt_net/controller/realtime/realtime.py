#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 07:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, QTimer

from pygpt_net.core.events import (
    RealtimeEvent,
    RenderEvent,
    BaseEvent,
    AppEvent,
    KernelEvent,
    Event,
)
from pygpt_net.core.realtime.worker import RealtimeSignals
from pygpt_net.core.types import MODE_AUDIO
from pygpt_net.utils import trans
from pygpt_net.core.tabs import Tab

from .manager import Manager

class Realtime:
    def __init__(self, window=None):
        """
        Realtime controller

        :param window: Window instance
        """
        self.window = window
        self.manager = Manager(window)
        self.signals = RealtimeSignals()
        self.signals.response.connect(self.handle_response)
        self.current_active = None # openai | google
        self.allowed_modes = [MODE_AUDIO]
        self.manual_commit_sent = False

    def setup(self):
        """Setup realtime core, signals, etc. in main thread"""
        self.window.core.audio.setup()  # setup RT signals in audio input/output core

    def is_enabled(self) -> bool:
        """
        Check if realtime is enabled in settings

        :return: True if enabled, False otherwise
        """
        mode = self.window.core.config.get("mode")
        if mode == MODE_AUDIO:
            if self.window.controller.ui.tabs.get_current_type() != Tab.TAB_NOTEPAD:
                return True
        return False

    @Slot(object)
    def handle(self, event: BaseEvent):
        """
        Handle realtime event (returned from dispatcher)

        :param event: RealtimeEvent instance
        """
        is_muted = self.window.controller.audio.is_muted()  # global mute state

        # check if mode is supported
        if not self.is_supported() and isinstance(event, RealtimeEvent):
            event.stop = True # stop further propagation
            return # ignore if not in realtime mode

        # ----------------------------------------------------

        # audio output chunk: send to audio output handler
        if event.name == RealtimeEvent.RT_OUTPUT_AUDIO_DELTA:
            self.set_idle()
            payload = event.data.get("payload", None)
            if payload and not is_muted:  # do not play if muted
                self.window.core.audio.output.handle_realtime(payload, self.signals)

        # audio input chunk: send to the active realtime client
        elif event.name == RealtimeEvent.RT_INPUT_AUDIO_DELTA:
            self.set_idle()
            if self.current_active == "google":
                self.window.core.api.google.realtime.handle_audio_input(event)
            elif self.current_active == "openai":
                self.window.core.api.openai.realtime.handle_audio_input(event)

        # begin: first text chunk or audio chunk received, start rendering
        elif event.name == RealtimeEvent.RT_OUTPUT_READY:
            ctx = event.data.get('ctx', None)
            if ctx:
                self.window.dispatch(RenderEvent(RenderEvent.STREAM_BEGIN, {
                    "meta": ctx.meta,
                    "ctx": ctx,
                }))
                self.set_busy()

        # commit: audio buffer sent, stop audio input and finalize the response
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT:
            self.set_busy()
            if self.manual_commit_sent:
                self.manual_commit_sent = False
                return # abort if manual commit was already sent
            self.window.controller.audio.execute_input_stop()

        elif event.name == RealtimeEvent.RT_INPUT_AUDIO_MANUAL_STOP:
            self.manual_commit_sent = True
            self.set_busy()
            QTimer.singleShot(0, lambda: self.manual_commit())

        elif event.name == RealtimeEvent.RT_INPUT_AUDIO_MANUAL_START:
            self.set_idle()
            self.window.controller.chat.input.execute("...", force=True)
            self.window.dispatch(KernelEvent(KernelEvent.STATUS, {
                'status': trans("speech.listening"),
            }))

        # text delta: append text chunk to the response
        elif event.name == RealtimeEvent.RT_OUTPUT_TEXT_DELTA:
            self.set_idle()
            ctx = event.data.get('ctx', None)
            chunk = event.data.get('chunk', "")
            if chunk and ctx:
                self.window.dispatch(RenderEvent(RenderEvent.STREAM_APPEND, {
                    "meta": ctx.meta,
                    "ctx": ctx,
                    "chunk": chunk,
                    "begin": False,
                }))

        # audio end: on stop audio playback
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_END:
            self.set_idle()
            self.window.controller.chat.common.unlock_input()
            if self.is_loop():
                QTimer.singleShot(500, lambda: self.next_turn())  # wait a bit before next turn

        # end of turn: finalize the response
        elif event.name == RealtimeEvent.RT_OUTPUT_TURN_END:
            self.set_idle()
            ctx = event.data.get('ctx', None)
            if ctx:
                self.end_turn(ctx)
            if self.window.controller.audio.is_recording():
                self.window.update_status(trans("speech.listening"))
            self.window.controller.chat.common.unlock_input()

        # volume change: update volume in audio output handler
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_VOLUME_CHANGED:
            if not is_muted:
                volume = event.data.get("volume", 1.0)
            else:
                volume = 0.0
            self.window.controller.audio.ui.on_output_volume_change(volume)

        # error: audio output error
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_ERROR:
            self.set_idle()
            error = event.data.get("error")
            self.window.core.debug.log(error)
            self.window.controller.chat.common.unlock_input()

        # -----------------------------------

        # app events, always handled
        elif event.name == AppEvent.MODE_SELECTED:
            mode = self.window.core.config.get("mode")
            if mode != MODE_AUDIO:
                QTimer.singleShot(0, lambda: self.reset())

        elif event.name == AppEvent.CTX_CREATED:
            QTimer.singleShot(0, lambda: self.reset())

        elif event.name == AppEvent.CTX_SELECTED:
            QTimer.singleShot(0, lambda: self.reset())

    def next_turn(self):
        """Start next turn in loop mode (if enabled)"""
        self.window.dispatch(Event(Event.AUDIO_INPUT_RECORD_TOGGLE))
        if self.window.controller.audio.is_recording():
            QTimer.singleShot(100, lambda: self.window.update_status(trans("speech.listening")))

    def is_loop(self) -> bool:
        """
        Check if loop recording is enabled

        :return: True if loop recording is enabled, False otherwise
        """
        if self.window.controller.kernel.stopped():
            return False
        return self.window.core.config.get("audio.input.loop", False)

    @Slot(object)
    def handle_response(self, event: RealtimeEvent):
        """
        Handle response event (send to kernel -> dispatcher)

        :param event: RealtimeEvent instance
        """
        self.window.controller.kernel.listener(event)

    def is_auto_turn(self) -> bool:
        """
        Check if auto-turn is enabled

        :return: True if auto-turn is enabled, False otherwise
        """
        return self.window.core.config.get("audio.input.auto_turn", True)

    def manual_commit(self):
        """Manually commit the response (end of turn)"""
        if self.current_active == "google":
            self.window.core.api.google.realtime.manual_commit()
        elif self.current_active == "openai":
            self.window.core.api.openai.realtime.manual_commit()

    def end_turn(self, ctx):
        """
        End of realtime turn - finalize the response

        :param ctx: Context instance
        """
        self.set_idle()
        if not ctx:
            return
        self.window.controller.chat.output.handle_after(
            ctx=ctx,
            mode=MODE_AUDIO,
            stream=True,
        )
        self.window.controller.chat.output.post_handle(
            ctx=ctx,
            mode=MODE_AUDIO,
            stream=True,
        )
        self.window.controller.chat.output.handle_end(
            ctx=ctx,
            mode=MODE_AUDIO,
        )
        self.window.controller.chat.common.show_response_tokens(ctx)

    def shutdown(self):
        """Shutdown all realtime threads and async loops"""
        try:
            self.window.core.api.openai.realtime.shutdown()
        except Exception as e:
            self.window.core.debug.log(f"[openai] Realtime shutdown error: {e}")
        try:
            self.window.core.api.google.realtime.shutdown()
        except Exception as e:
            self.window.core.debug.log(f"[google] Realtime shutdown error: {e}")
        try:
            self.manager.shutdown()
        except Exception as e:
            self.window.core.debug.log(f"[manager] Realtime shutdown error: {e}")

    def reset(self):
        """Reset realtime session"""
        try:
            self.window.core.api.openai.realtime.reset()
        except Exception as e:
            self.window.core.debug.log(f"[openai] Realtime reset error: {e}")
        try:
            self.window.core.api.google.realtime.reset()
        except Exception as e:
            self.window.core.debug.log(f"[google] Realtime reset error: {e}")

    def is_supported(self) -> bool:
        """
        Check if current mode supports realtime

        :return: True if mode supports realtime, False otherwise
        """
        mode = self.window.core.config.get("mode")
        return mode in self.allowed_modes

    def set_current_active(self, provider: str):
        """
        Set the current active realtime provider

        :param provider: Provider name (openai, google)
        """
        self.current_active = provider.lower() if provider else None

    def set_idle(self):
        """Set kernel state to IDLE"""
        QTimer.singleShot(0, lambda: self.window.dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "realtime",
        })))

    def set_busy(self):
        """Set kernel state to BUSY"""
        QTimer.singleShot(0, lambda: self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "realtime",
        })))