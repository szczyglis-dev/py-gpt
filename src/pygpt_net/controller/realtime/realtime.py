#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.30 13:05:00                  #
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
        self._realtime_text_started = set()
        self._realtime_follow_checked = set()
        self._playback_ctx = None

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
            if self.window.controller.tabs.get_current_type() != Tab.TAB_NOTEPAD:
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
            payload = event.data.get("payload", None)
            if payload and not is_muted:  # do not play if muted
                ctx = payload.get("ctx", None)
                self._interrupt_superseded_playback(ctx)
                if ctx is not None:
                    self._playback_ctx = ctx
                self.window.core.audio.output.handle_realtime(payload, self.signals)

        # audio playback really started: hide only the WebView request loader.
        # Keep the kernel BUSY until the realtime turn actually finishes.
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_PLAYBACK_START:
            ctx = self._playback_ctx
            if ctx is not None:
                self.window.dispatch(RenderEvent(RenderEvent.STATE_IDLE, {
                    "meta": ctx.meta,
                }))

        # audio input chunk: send to the active realtime client
        elif event.name == RealtimeEvent.RT_INPUT_AUDIO_DELTA:
            if not self.is_auto_turn():
                return  # manual capture submits the complete recording on stop
            if self.current_active == "google":
                self.window.core.api.google.realtime.handle_audio_input(event)
            elif self.current_active == "openai":
                self.window.core.api.openai.realtime.handle_audio_input(event)
            elif self.current_active == "x_ai":
                self.window.core.api.xai.realtime.handle_audio_input(event)

        # begin: first text chunk or audio chunk received, start rendering
        elif event.name == RealtimeEvent.RT_OUTPUT_READY:
            ctx = event.data.get('ctx', None)
            self.begin_turn(ctx)

        # commit: audio buffer sent, begin the response and stop audio input
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT:
            self.begin_turn(event.data.get("ctx"))
            self.set_busy()
            if self.manual_commit_sent:
                self.manual_commit_sent = False
                return # abort if manual commit was already sent
            self.window.controller.audio.execute_input_stop()

        elif event.name == RealtimeEvent.RT_INPUT_AUDIO_MANUAL_STOP:
            if not self.is_auto_turn():
                # The capture plugin submits the recorded file. No live buffer
                # exists in manual mode, and force_response_now is VAD-only.
                self.manual_commit_sent = False
                return
            self.manual_commit_sent = True
            self.begin_turn(self.manager.ctx)
            self.set_busy()
            QTimer.singleShot(0, lambda: self.manual_commit())

        elif event.name == RealtimeEvent.RT_INPUT_AUDIO_MANUAL_START:
            # A manual commit acknowledgement may be lost when a realtime socket
            # drops between turns. Never let that one-shot guard leak into the
            # next microphone round.
            self.manual_commit_sent = False
            self.set_idle()
            if self.is_auto_turn():
                self.window.controller.chat.input.execute("...", force=True)
            self.window.dispatch(KernelEvent(KernelEvent.STATUS, {
                'status': trans("speech.listening"),
            }))

        # text delta: append text chunk to the response
        elif event.name == RealtimeEvent.RT_OUTPUT_TEXT_DELTA:
            ctx = event.data.get('ctx', None)
            chunk = event.data.get('chunk', "")
            if chunk and ctx:
                if getattr(ctx, "_realtime_state", "") in ("finished", "tools"):
                    return
                self.begin_turn(ctx)
                # First visible content from a newer response is a barge-in point:
                # stop any still-audible previous response immediately.
                self._interrupt_superseded_playback(ctx)

                # Realtime starts its provider stream almost immediately after the
                # input row is queued in the WebView. The loader can still change
                # document height in that window and Chromium may transiently leave
                # ScrollManager in MANUAL although the user was at the bottom. Before
                # the first visible text delta only, recover FOLLOW if the viewport is
                # still physically near the bottom. Never force a user who scrolled up.
                follow_key = id(ctx)
                if follow_key not in self._realtime_follow_checked:
                    self._realtime_follow_checked.add(follow_key)
                    try:
                        renderer = self.window.controller.chat.render.instance()
                        restore_follow = getattr(
                            renderer,
                            "resume_auto_follow_if_near_bottom",
                            None,
                        )
                        if callable(restore_follow):
                            # Sending a new microphone turn already returns scroll
                            # ownership to FOLLOW. Reassert it on the first visible
                            # assistant token as well: loader/input DOM changes can
                            # otherwise make Chromium classify the intermediate
                            # geometry shift as a manual scroll.
                            restore_follow(ctx.meta, force=True)
                    except Exception:
                        pass

                # A tool-result response is an ephemeral continuation of the same
                # durable user turn. Reuse the normal chat stream continuation
                # renderer so the completed tool row stays in chronological order
                # and the follow-up text is appended as a new partial instead of
                # replacing the previous assistant content.
                if getattr(ctx, "turn_parent", None) is not None:
                    key = id(ctx)
                    begin = key not in self._realtime_text_started
                    # Realtime owns a different worker lifecycle than Chat, so it
                    # must not call Stream.handleChunk(): that slot intentionally
                    # rejects chunks without an active chat StreamWorker/PID. Use
                    # the shared continuation renderer directly instead.
                    self.window.controller.chat.stream.append_continuation_chunk(
                        ctx,
                        chunk,
                        begin,
                    )
                    self._realtime_text_started.add(key)
                else:
                    # Mark the first visible realtime delta as begin=True, just like
                    # the normal chat StreamWorker. STREAM_BEGIN may already have
                    # been announced by commit/output-ready, but WebRenderer treats
                    # both announcements as one idempotent response lifecycle. This
                    # lets either queued event arrive first without a second reset
                    # that could discard the first provider delta.
                    key = id(ctx)
                    begin = key not in self._realtime_text_started
                    self.window.dispatch(RenderEvent(RenderEvent.STREAM_APPEND, {
                        "meta": ctx.meta,
                        "ctx": ctx,
                        "chunk": chunk,
                        "begin": begin,
                    }))
                    self._realtime_text_started.add(key)

        # audio end: on stop audio playback
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_END:
            self._playback_ctx = None
            self.manual_commit_sent = False
            self.set_idle()
            self.window.controller.chat.common.unlock_input()
            if self.is_loop():
                QTimer.singleShot(500, lambda: self.next_turn())  # wait a bit before next turn

        # end of turn: finalize the response
        elif event.name == RealtimeEvent.RT_OUTPUT_TURN_END:
            self.manual_commit_sent = False
            ctx = event.data.get('ctx', None)
            finished = self.end_turn(ctx)
            if finished:
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
            self._playback_ctx = None
            self.manual_commit_sent = False
            self.set_idle()
            error = event.data.get("error")
            self.window.core.debug.log(error)
            ctx = event.data.get("ctx") or self.manager.ctx
            self.fail_turn(ctx)
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

    def _interrupt_superseded_playback(self, ctx) -> None:
        """
        Stop buffered audio from an older response when new response content arrives.

        The comparison is deliberately based on the CtxItem object carried by
        realtime events, so chunks belonging to the same response keep using the
        same playback session.
        """
        if ctx is None or self._playback_ctx is None or ctx is self._playback_ctx:
            return
        try:
            self.window.core.audio.output.interrupt_realtime()
        except Exception:
            pass
        self._playback_ctx = None

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
        elif self.current_active == "x_ai":
            self.window.core.api.xai.realtime.manual_commit()

    def begin_turn(self, ctx):
        """Start rendering once input is committed or model output arrives.

        Session setup and microphone capture are not response streams. Commit,
        response-ready and the first delta may all announce the same response.
        """
        if ctx is None or getattr(ctx, "_realtime_state", "") in ("streaming", "tools", "finished"):
            return
        self._interrupt_superseded_playback(ctx)
        ctx._realtime_state = "streaming"
        self.window.update_status(trans("status.sending"))
        self.window.dispatch(RenderEvent(RenderEvent.STREAM_BEGIN, {
            "meta": ctx.meta,
            "ctx": ctx,
        }))
        self.set_busy()

    def end_turn(self, ctx):
        """
        End of realtime turn - finalize the response.

        Tool calls are intermediate rounds of the same durable CtxItem. A realtime
        tool-result response therefore follows the same continuation lifecycle as
        streamed chat: merge the ephemeral response into its parent, materialize
        completed tools, and call handle_end() only when no next tool is pending.

        :param ctx: Context instance
        """
        if not ctx:
            self.set_idle()
            return True

        state = getattr(ctx, "_realtime_state", "")
        if state in ("finished", "tools"):
            return state == "finished"
        self.begin_turn(ctx)  # tool-only/empty responses still have one lifecycle
        self.set_idle()
        ctx._realtime_state = "finished"
        ctx.current = False

        source_ctx = ctx
        self._realtime_text_started.discard(id(source_ctx))
        self._realtime_follow_checked.discard(id(source_ctx))
        is_continuation = getattr(source_ctx, "turn_parent", None) is not None
        closes_tool_series = bool(
            is_continuation
            and self.window.core.ctx.continuation_closes_tool_series(source_ctx)
        )
        if is_continuation:
            ctx = self.window.core.ctx.merge_continuation(source_ctx)

        self.window.dispatch(RenderEvent(RenderEvent.STREAM_END, {
            "meta": ctx.meta,
            "ctx": ctx,
        }))

        self.window.controller.chat.output.handle_after(
            ctx=ctx,
            mode=MODE_AUDIO,
            stream=True,
        )

        if is_continuation and closes_tool_series:
            # Match normal chat semantics: consecutive tool-only realtime rounds
            # keep one animated Tool row alive. Materialize/clear it only when the
            # provider emits visible non-tool output or ends the tool series.
            self.window.dispatch(RenderEvent(RenderEvent.SYNC_OUTPUT, {
                "meta": ctx.meta,
                "ctx": ctx,
                "reason": "realtime_tool_series_boundary",
            }))
            self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {
                "meta": ctx.meta,
                "ctx": ctx,
            }))

        finished = self.window.controller.chat.output.post_handle(
            ctx=ctx,
            mode=MODE_AUDIO,
            stream=True,
        )
        if not finished:
            source_ctx._realtime_state = "tools"
            # command.handle() has started the tool and emitted TOOL_BEGIN. Keep the
            # turn/request open; handle_end() would close the lifecycle and can
            # wipe that status before the tool result arrives.
            self.set_busy()
            return False

        self.window.controller.chat.output.handle_end(
            ctx=ctx,
            mode=MODE_AUDIO,
        )
        self.window.controller.chat.common.show_response_tokens(ctx)
        return True

    def fail_turn(self, ctx):
        """Release a failed realtime request without executing pending tools."""
        if ctx is None or getattr(ctx, "_realtime_state", "") == "finished":
            return
        was_streaming = getattr(ctx, "_realtime_state", "") == "streaming"
        ctx._realtime_state = "finished"
        ctx.current = False
        self._realtime_text_started.discard(id(ctx))
        self._realtime_follow_checked.discard(id(ctx))
        if getattr(ctx, "turn_parent", None) is not None:
            ctx = self.window.core.ctx.merge_continuation(ctx)
        if was_streaming:
            self.window.dispatch(RenderEvent(RenderEvent.STREAM_END, {"meta": ctx.meta, "ctx": ctx}))
        self.window.controller.chat.output.handle_end(ctx=ctx, mode=MODE_AUDIO)

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
            self.window.core.api.xai.realtime.shutdown()
        except Exception as e:
            self.window.core.debug.log(f"[xAI] Realtime shutdown error: {e}")
        try:
            self.manager.shutdown()
        except Exception as e:
            self.window.core.debug.log(f"[manager] Realtime shutdown error: {e}")

    def reset(self):
        """Reset realtime session"""
        self._realtime_text_started.clear()
        self._realtime_follow_checked.clear()
        self._playback_ctx = None
        self.manual_commit_sent = False
        try:
            self.window.core.api.openai.realtime.reset()
        except Exception as e:
            self.window.core.debug.log(f"[openai] Realtime reset error: {e}")
        try:
            self.window.core.api.google.realtime.reset()
        except Exception as e:
            self.window.core.debug.log(f"[google] Realtime reset error: {e}")
        try:
            self.window.core.api.xai.realtime.reset()
        except Exception as e:
            self.window.core.debug.log(f"[xAI] Realtime reset error: {e}")

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
