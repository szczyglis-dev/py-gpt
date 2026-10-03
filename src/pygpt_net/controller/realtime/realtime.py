#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
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
        self._auto_loop_generation = 0
        self._auto_loop_paused = False
        self._cancelling = False
        self._creating_audio_input_block = 0
        self._response_active = False
        self._response_ctx = None
        self._shutting_down = False
        self._last_error_signature = None

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
            if not self.window.tools.get("notepad").tabs.is_active():
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
            ctx = payload.get("ctx", None) if payload else None

            # A chunk may already be queued on the Qt/main-thread signal when the
            # user interrupts the turn. Re-check the response owner here, after
            # delivery, so such a stale chunk cannot create a fresh playback
            # session after interrupt_realtime() has just hard-stopped the old one.
            if ctx is not None and getattr(ctx, "_realtime_interrupted", False):
                return

            if payload:
                self._set_response_active(True, ctx=ctx)
            if payload and not is_muted:  # do not play if muted
                self._interrupt_superseded_playback(ctx)
                if ctx is not None:
                    self._playback_ctx = ctx
                self.window.core.audio.output.handle_realtime(payload, self.signals)

        # audio playback really started: hide only the WebView request loader.
        # Keep the kernel BUSY until the realtime turn actually finishes.
        elif event.name == RealtimeEvent.RT_OUTPUT_AUDIO_PLAYBACK_START:
            ctx = event.data.get("ctx", None) or self._playback_ctx
            if (ctx is None
                    or getattr(ctx, "_realtime_interrupted", False)
                    or (self._playback_ctx is not None and ctx is not self._playback_ctx)):
                return
            self._set_response_active(True, ctx=ctx)
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
            auto = bool(event.data.get("auto", False))
            if not auto:
                self._last_error_signature = None

            # A normal typed message pauses the VAD listen -> respond -> listen
            # cycle until the user explicitly clicks the microphone again. An
            # automatic start may already have been queued when that text was sent;
            # never let such a stale auto event silently resume the loop.
            if auto and self._auto_loop_paused:
                try:
                    plugin = self.window.core.plugins.get("audio_input")
                    handler = getattr(plugin, "handler_simple", None)
                    if handler is not None and getattr(handler, "is_recording", False):
                        handler.force_stop()
                except Exception as e:
                    self.window.core.debug.log(e)
                self.window.update_status("")
                return

            # Only an explicit user microphone click resumes a paused Auto-VAD
            # cycle. Automatic starts must preserve the current pause state.
            if not auto:
                self._auto_loop_paused = False

            # A manual commit acknowledgement may be lost when a realtime socket
            # drops between turns. Never let that one-shot guard leak into the
            # next microphone round.
            self.manual_commit_sent = False
            self.set_idle()
            if self.is_auto_turn():
                self._creating_audio_input_block += 1
                try:
                    self.window.controller.chat.input.execute("...", force=True)
                finally:
                    self._creating_audio_input_block = max(0, self._creating_audio_input_block - 1)
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

                # Keep the durable CtxItem synchronized with what has already
                # reached the realtime UI. Provider clients normally assign the
                # final output only on response.done/turnComplete; a user barge-in
                # can happen before that event, so without this live snapshot the
                # interrupted text cannot be committed to the database.
                current_output = getattr(ctx, "output", None)
                ctx.output = (current_output or "") + str(chunk)

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
            event_ctx = event.data.get("ctx", None)
            playback_ctx = self._playback_ctx

            # Ignore a late device-end callback from an interrupted/superseded
            # playback generation. It must not alter STOP state or schedule VAD
            # for whatever response may already own playback now.
            if event_ctx is not None:
                if getattr(event_ctx, "_realtime_interrupted", False):
                    return
                if playback_ctx is not None and event_ctx is not playback_ctx:
                    return
                playback_ctx = event_ctx

            self._playback_ctx = None
            self.manual_commit_sent = False
            self._set_response_active(False, ctx=playback_ctx)
            self.set_idle()
            self.window.controller.chat.common.unlock_input()
            if self.is_loop():
                generation = self._auto_loop_generation
                QTimer.singleShot(500, lambda g=generation: self.next_turn(g))

        # end of turn: finalize the response
        elif event.name == RealtimeEvent.RT_OUTPUT_TURN_END:
            self.manual_commit_sent = False
            ctx = event.data.get('ctx', None)
            finished = self.end_turn(ctx)
            if finished:
                # The provider turn can finish before the device drains buffered
                # realtime audio. Keep STOP visible until RT_OUTPUT_AUDIO_END. For
                # text-only/muted turns there is no playback owner, so TURN_END is
                # the natural response-activity boundary.
                if self._playback_ctx is None:
                    self._set_response_active(False, ctx=ctx)
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
            self._handle_realtime_error(event)

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

    def _handle_realtime_error(self, event: RealtimeEvent) -> None:
        """Handle an unexpected realtime/session error on the Qt main thread.

        Transport failures can arrive from the persistent provider receiver while
        microphone chunks are still being produced. Stop local capture/playback and
        close the current CtxItem, but do not call provider.reset(): a dead socket is
        already invalidated by the client and the next explicit turn may reconnect.
        """
        data = event.data or {}
        error = data.get("error")
        ctx = data.get("ctx") or self._playback_ctx or self.manager.ctx
        provider = str(data.get("provider") or self.current_active or "realtime")
        phase = str(data.get("phase") or "transport")

        try:
            self.window.core.debug.log(error)
        except Exception:
            pass

        self.cancel_auto_loop()
        self._auto_loop_paused = True
        self.manual_commit_sent = False
        self._playback_ctx = None
        self._set_response_active(False, ctx=ctx, force=True)

        # Stop microphone capture without committing the buffer into a socket that
        # has just failed. This also prevents Auto-VAD from continuously feeding a
        # dead connection until the user explicitly starts another turn.
        try:
            plugin = self.window.core.plugins.get("audio_input")
            handler = getattr(plugin, "handler_simple", None)
            if handler is not None and getattr(handler, "is_recording", False):
                handler.force_stop()
        except Exception as e:
            self.window.core.debug.log(e)

        try:
            self.window.core.audio.output.interrupt_realtime()
        except Exception:
            pass

        if ctx is not None and getattr(ctx, "_realtime_state", "") != "finished":
            try:
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["response_error"] = self._realtime_error_text(error)
            except Exception:
                pass
            self.fail_turn(ctx)

        self.set_idle()
        self.window.update_status("")
        self.window.controller.chat.common.unlock_input()

        # Opening/starting a session must never fail only in the log. Unexpected
        # transport failures are surfaced too, but deduplicated because a failed
        # ws.send() and the receiver may observe the same socket loss concurrently.
        if not self._shutting_down and not getattr(ctx, "_realtime_interrupted", False):
            message = self._realtime_error_text(error)
            signature = (provider, phase, message)
            if message and signature != self._last_error_signature:
                self._last_error_signature = signature
                label = {
                    "openai": "OpenAI Realtime",
                    "google": "Google Realtime",
                    "x_ai": "xAI Realtime",
                }.get(provider, "Realtime")
                try:
                    self.window.ui.dialogs.alert(f"{label}:\n\n{message}")
                except Exception as e:
                    self.window.core.debug.log(e)

    @staticmethod
    def _realtime_error_text(error) -> str:
        """Return useful text from an exception chain without losing provider detail."""
        if error is None:
            return "Unknown realtime error"
        messages = []
        seen = set()
        current = error
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            try:
                text = str(current).strip()
            except Exception:
                text = ""
            if text and text not in messages:
                messages.append(text)

            # websockets InvalidStatus and similar handshake exceptions may keep
            # the provider's useful quota/auth message only on the HTTP response.
            response = getattr(current, "response", None)
            if response is not None:
                try:
                    status = getattr(response, "status_code", None)
                    reason = getattr(response, "reason_phrase", None)
                    http_text = " ".join(
                        str(part).strip() for part in (
                            f"HTTP {status}" if status is not None else "",
                            reason or "",
                        ) if str(part).strip()
                    )
                    if http_text and http_text not in messages:
                        messages.append(http_text)
                except Exception:
                    pass
                try:
                    body = getattr(response, "body", None)
                    if isinstance(body, (bytes, bytearray)):
                        body = bytes(body).decode("utf-8", errors="replace")
                    body = str(body or "").strip()
                    if body and body not in messages:
                        messages.append(body)
                except Exception:
                    pass

            current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        if messages:
            return "\n".join(messages)
        return type(error).__name__

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

    def _set_response_active(self, value: bool, ctx=None, force: bool = False) -> None:
        """Track the user-visible realtime response/playback lifetime.

        ``ctx`` guards against late TURN_END/AUDIO_END events from an interrupted
        response hiding STOP for a newer turn.
        """
        value = bool(value)
        if value:
            if ctx is not None:
                self._response_ctx = ctx
            if self._response_active:
                return
            self._response_active = True
        else:
            if (not force and ctx is not None and self._response_ctx is not None
                    and ctx is not self._response_ctx):
                return
            if not self._response_active and self._response_ctx is None:
                return
            self._response_active = False
            self._response_ctx = None
        try:
            self.window.controller.chat.common.sync_send_stop_buttons()
        except Exception:
            pass

    def is_response_active(self) -> bool:
        """Return True while STOP should remain visible for realtime output."""
        return bool(self._response_active)

    def has_pending_response(self) -> bool:
        """Return True while an Audio-mode user turn can still be interrupted."""
        if not self.is_enabled():
            return False
        if self._response_active or self.has_active_turn():
            return True
        try:
            if self.window.controller.chat.input.generating:
                return True
        except Exception:
            pass
        return False

    def can_interrupt(self) -> bool:
        """Return True when ESC/STOP should use turn-only realtime cancellation."""
        if not self.is_enabled():
            return False
        if self.has_pending_response():
            return True
        # Preserve Auto-VAD cancellation while the microphone is only listening
        # and no response has started yet.
        try:
            return bool(self.is_auto_turn() and self.window.controller.audio.is_recording())
        except Exception:
            return False

    def on_user_text_submit(self, mode: str = None, text: str = "") -> None:
        """Allow keyboard text barge-in without coupling ChatInput to realtime state.

        If ENTER is pressed while a realtime response is still pending/playing,
        finalize that turn exactly like a manual interrupt before the generic
        input controller tries to claim a new request owner.
        """
        if mode != MODE_AUDIO or not str(text or "").strip():
            return
        if not self.is_enabled() or not self.has_pending_response():
            return
        self.cancel_conversation(stop_capture=True)

    def cancel_auto_loop(self):
        """Invalidate any delayed VAD restart that has already been queued."""
        self._auto_loop_generation += 1

    def next_turn(self, generation: int = None):
        """Start the next VAD turn only if the conversation is still active."""
        if generation is not None and generation != self._auto_loop_generation:
            return
        if not self.is_enabled() or not self.is_loop():
            return
        if self.window.controller.audio.is_recording():
            return

        # Use an explicit automatic start so this callback cannot accidentally
        # toggle/stop a microphone session started by the user in the meantime.
        self.window.dispatch(Event(Event.AUDIO_INPUT_RECORD_TOGGLE, {
            "state": True,
            "auto": True,
        }))
        if self.window.controller.audio.is_recording():
            QTimer.singleShot(100, lambda g=generation: self._set_listening_status(g))

    def _set_listening_status(self, generation: int = None):
        """Apply the delayed listening status only to the still-active VAD cycle."""
        if generation is not None and generation != self._auto_loop_generation:
            return
        if self._auto_loop_paused or not self.is_enabled():
            return
        if not self.window.controller.audio.is_recording():
            return
        self.window.update_status(trans("speech.listening"))

    def on_text_send(
            self,
            mode: str = None,
            internal: bool = False,
            reply: bool = False,
            continuation: bool = False,
    ) -> None:
        """Handle a text send that may affect the realtime Auto-VAD cycle.

        Keep all realtime-specific policy here so the generic text controller only
        reports that a send is about to happen. A real user text message in Audio
        mode pauses listen -> respond -> listen until the microphone is clicked
        manually again. Internal/tool continuations and the synthetic microphone
        ``...`` input block must not affect that state. The provider session and
        conversation state remain intact.
        """
        if mode != MODE_AUDIO:
            return
        if not internal and not reply and not continuation:
            self._last_error_signature = None
        if internal or reply or continuation:
            return
        if not self.is_enabled() or not self.is_auto_turn():
            return
        if self._creating_audio_input_block > 0:
            return

        self._pause_auto_loop_for_text_input()

    def _pause_auto_loop_for_text_input(self) -> None:
        """Pause VAD looping until the user explicitly starts the microphone."""
        self.cancel_auto_loop()
        self._auto_loop_paused = True
        self.manual_commit_sent = False

        try:
            plugin = self.window.core.plugins.get("audio_input")
            handler = getattr(plugin, "handler_simple", None)
            if handler is not None and getattr(handler, "is_recording", False):
                handler.force_stop()
        except Exception as e:
            self.window.core.debug.log(e)

    def is_loop(self) -> bool:
        """
        Check if automatic VAD conversation continuation is enabled.

        Loop is no longer a separate user option: Auto VAD owns the whole
        listen -> respond -> listen cycle.
        """
        if self.window.controller.kernel.stopped() or self._auto_loop_paused:
            return False
        return self.is_auto_turn()

    def has_active_turn(self) -> bool:
        """Return True while a realtime response/request is still in flight."""
        if self._playback_ctx is not None:
            return True
        ctx = self.manager.ctx
        if ctx is not None and getattr(ctx, "_realtime_state", "") != "finished":
            try:
                if self.window.controller.chat.input.generating:
                    return True
            except Exception:
                pass
        try:
            if self.window.core.ctx.output.has_request():
                return True
        except Exception:
            pass
        return False

    def prepare_new_turn(self):
        """Barge in: finish only the active response, keeping the live session."""
        self.cancel_auto_loop()
        if self.has_active_turn():
            self.cancel_conversation(stop_capture=False)

    def _cancel_provider_response(self):
        """Cancel the active model response without closing the realtime session."""
        try:
            if self.current_active == "google":
                self.window.core.api.google.realtime.cancel_response()
            elif self.current_active == "openai":
                self.window.core.api.openai.realtime.cancel_response()
            elif self.current_active == "x_ai":
                self.window.core.api.xai.realtime.cancel_response()
        except Exception as e:
            self.window.core.debug.log(e)

    def cancel_conversation(self, stop_capture: bool = True):
        """
        Interrupt the current realtime turn without closing the provider session.

        ESC/STOP also stop microphone capture and disable the queued Auto-VAD
        restart. Microphone barge-in calls the same path with ``stop_capture=False``
        immediately before starting the next capture. In every case the partial
        assistant output is finalized and persisted as its own CtxItem while the
        live conversation/session remains available for the next turn.

        :param stop_capture: force-stop the current microphone capture
        """
        if self._cancelling:
            return
        self._cancelling = True
        ctx = self.manager.ctx
        try:
            self.cancel_auto_loop()
            self._auto_loop_paused = True
            self.manual_commit_sent = False
            self._set_response_active(False, force=True)

            # ENTER/ESC/STOP may arrive while a typed message is still in the
            # asynchronous preprocessing phase, before the realtime manager owns
            # a CtxItem. Prevent that late worker from resurrecting the cancelled
            # turn.
            try:
                self.window.controller.chat.input.cancel_preprocessing()
            except Exception:
                pass

            if stop_capture:
                # Never route this through AUDIO_INPUT_RECORD_TOGGLE: in Auto VAD
                # that path commits the current microphone buffer. ESC/STOP must
                # discard it instead.
                try:
                    plugin = self.window.core.plugins.get("audio_input")
                    handler = getattr(plugin, "handler_simple", None)
                    if handler is not None and getattr(handler, "is_recording", False):
                        handler.force_stop()
                except Exception as e:
                    self.window.core.debug.log(e)

            # Mark the old response before any asynchronous provider cancellation.
            # RealtimeWorker/provider callbacks use this marker to discard late
            # audio/text from the interrupted response instead of rebinding it to
            # the next CtxItem.
            if ctx is not None and getattr(ctx, "_realtime_state", "") != "finished":
                try:
                    ctx.stopped = True
                    ctx._realtime_interrupted = True
                    if not isinstance(ctx.extra, dict):
                        ctx.extra = {}
                    ctx.extra["response_interrupted"] = True
                    ctx.extra.pop("response_final", None)
                except Exception:
                    pass

            # Stop only local playback. The websocket/live session is deliberately
            # kept alive so provider conversation memory survives ESC/STOP/barge-in.
            try:
                self.window.core.audio.output.interrupt_realtime()
            except Exception:
                pass
            self._playback_ctx = None

            # Persist and close the old visual/durable turn *before* a new input is
            # allowed to render. This is the immediate database commit requested by
            # the user and also releases the renderer's request ownership.
            if ctx is not None and getattr(ctx, "_realtime_state", "") != "finished":
                self.fail_turn(ctx)

            # Cancel generation at provider level where supported, but do not reset
            # or close the session. Google Live relies on normal activity barge-in
            # for the next microphone turn; its client still drains the interrupted
            # response against the old response owner.
            self._cancel_provider_response()

            # A generic kernel halt must not leak from an earlier STOP path into the
            # next realtime turn. We intentionally do not call kernel.stop() here.
            self.window.controller.kernel.resume()
            self.set_idle()
            self.window.controller.chat.common.unlock_input()

            # If interruption happened before a CtxItem existed, fail_turn() had
            # nothing to close. Release the pre-send request owner explicitly; the
            # cancelled preprocessing callback is now unable to continue it.
            try:
                output = self.window.core.ctx.output
                if output.has_request() and not self.window.controller.chat.input.generating:
                    output.finish_request()
                    self.window.controller.tabs.sync_focused_chat_context()
            except Exception as e:
                self.window.core.debug.log(e)

            # ``force_stop()`` intentionally does not publish a status of its own.
            # Clear the stale "Speak now..." left by microphone capture after an
            # ESC/STOP interrupt (and any other turn-only cancellation).
            self.window.update_status("")
        finally:
            self._cancelling = False

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
        if ctx is None or getattr(ctx, "_realtime_state", "") == "finished":
            return
        self._set_response_active(True, ctx=ctx)
        if getattr(ctx, "_realtime_state", "") in ("streaming", "tools"):
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
        """Release a failed/interrupted realtime request without running tools.

        ``STREAM_END`` finalizes the live assistant DOM, but it is not the outer
        CtxItem lifecycle boundary. Barge-in must close both. Otherwise a new
        microphone APPEND_INPUT can arrive while the renderer still considers
        the superseded CtxItem open and the next turn may be folded into it.
        """
        if ctx is None or getattr(ctx, "_realtime_state", "") == "finished":
            return
        was_streaming = getattr(ctx, "_realtime_state", "") == "streaming"
        ctx._realtime_state = "finished"
        ctx.current = False
        self._realtime_text_started.discard(id(ctx))
        self._realtime_follow_checked.discard(id(ctx))
        if getattr(ctx, "turn_parent", None) is not None:
            ctx = self.window.core.ctx.merge_continuation(ctx)

        # An interrupted realtime response must be durable immediately, not only
        # after the provider eventually emits response.done/turnComplete. The text
        # delta handler keeps ctx.output current, so this writes exactly the portion
        # that was visible at the interruption point.
        try:
            if not isinstance(ctx.extra, dict):
                ctx.extra = {}
            ctx.extra["response_interrupted"] = True
            ctx.extra.pop("response_final", None)
            self.window.core.ctx.update_item(ctx)
            self.window.core.ctx.store()
        except Exception as e:
            self.window.core.debug.log(e)

        if was_streaming:
            self.window.dispatch(RenderEvent(RenderEvent.STREAM_END, {
                "meta": ctx.meta,
                "ctx": ctx,
            }))

        # Match the normal completed-turn lifecycle without calling post_handle(),
        # because an interrupted response must never execute pending tool calls.
        # END clears the renderer's per-item state before the next microphone
        # BEGIN/APPEND_INPUT is allowed to establish a fresh visual turn.
        self.window.dispatch(RenderEvent(RenderEvent.END, {
            "meta": ctx.meta,
            "ctx": ctx,
            "stream": True,
        }))
        self.window.controller.chat.output.handle_end(ctx=ctx, mode=MODE_AUDIO)

    def shutdown(self):
        """Shutdown all realtime threads and async loops"""
        self._shutting_down = True
        self.cancel_auto_loop()
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
        self._shutting_down = False
        self._last_error_signature = None
        self.cancel_auto_loop()
        self._auto_loop_paused = False
        self._realtime_text_started.clear()
        self._realtime_follow_checked.clear()
        self._playback_ctx = None
        self.manual_commit_sent = False
        self._set_response_active(False, force=True)
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
