#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 12:30:00
# ================================================== #

from typing import Optional, Any, Dict

from PySide6.QtCore import QObject, Slot

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.bridge.context import MultimodalContext
from pygpt_net.core.events import Event, AppEvent, KernelEvent, RenderEvent
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_V2,
    MODE_ASSISTANT,
    MODE_IMAGE,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.mentions import (
    resolve_conversation_mentions,
    to_display_text as mentions_to_display_text,
)
from pygpt_net.utils import trans

from .input_worker import InputWorker


class _InputWorkerReceiver(QObject):
    """Marshal preprocessing results back to the UI thread."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    @Slot(int, str)
    def success(self, request_id: int, text: str):
        self.owner._on_preprocess_success(request_id, text)

    @Slot(int, object)
    def error(self, request_id: int, error: Exception):
        self.owner._on_preprocess_error(request_id, error)


class Input:
    def __init__(self, window=None):
        """
        Input controller

        :param window: Window instance
        """
        self.window = window
        self.locked = False
        self.stop = False
        self.generating = False
        self._preprocess_seq = 0
        self._preprocess_id = None
        self._preprocess_worker = None
        self._preprocess_receiver = _InputWorkerReceiver(self)
        self.no_ctx_idx_modes = [
            # MODE_IMAGE,
            MODE_ASSISTANT,
            # MODE_LLAMA_INDEX,
            MODE_AGENT,
        ]  # assistant is handled in async, agent is handled in agent flow
        self.stop_commands = [
            "stop",
            "halt",
        ]

    def _finish_request(self, meta=None):
        """Release request routing and apply any chat focus chosen meanwhile."""
        output = self.window.core.ctx.output
        output.finish_request(meta)
        self.window.controller.ui.tabs.sync_focused_chat_context()

    def _pin_user_chat(self, pid: Optional[int] = None):
        """Bind a manual send to the chat tab that actually invoked it."""
        core = self.window.core
        tabs_ui = self.window.controller.ui.tabs

        # ``pid`` is normally snapshotted at the very beginning of send_input(),
        # before USER_SEND/plugins can mutate focus. Keep a local fallback for
        # direct callers/tests.
        if pid is None:
            pid = tabs_ui.get_effective_current_pid()
        request_pid = core.ctx.output.begin_request(pid)
        tab = core.tabs.get_tab_by_pid(request_pid) if request_pid is not None else None
        if tab is None or tab.type != Tab.TAB_CHAT:
            return None

        meta_id = getattr(tab, "data_id", None)
        meta = core.ctx.get_meta_by_id(meta_id) if meta_id is not None else None

        if meta is None:
            # A tab opened while another request was running can intentionally
            # have no context yet. A stale/deleted data_id is equivalent: never
            # let it leave an owner pinned to a context that cannot be resolved.
            tab.data_id = None
            meta = core.ctx.new()
            if meta is not None:
                tab.data_id = meta.id
                core.ctx.output.bind_request_meta(meta)
                self.window.controller.ctx.update(reload=True, all=True)
                self.window.controller.ctx.fresh_output(meta)
                tabs_ui.update_title_by_tab(tab, meta.name)
        else:
            # The source tab is authoritative. Synchronize shared ctx state once
            # before provider/history building, then freeze it for this request.
            if core.ctx.get_current() != meta.id:
                self.window.controller.ctx.select_on_list_only(meta.id)
            core.ctx.output.bind_request_meta(meta)

        return meta

    def _resolve_history_mentions(self, text: str) -> str:
        """Populate conversation @mentions with query-focused history context."""
        raw = str(text or "")
        if "<conversation" not in raw.lower():
            return raw
        plugin = self.window.core.plugins.get("cmd_history")
        if plugin is None or not hasattr(plugin, "get_summary"):
            return raw

        query = mentions_to_display_text(raw).strip()

        def resolve(ctx_id: int, _title: str, current_query: str) -> str:
            return plugin.get_summary(ctx_id, current_query)

        try:
            return resolve_conversation_mentions(raw, resolve, query=query)
        except Exception as e:
            self.window.core.debug.log(e)
            return raw

    def _start_preprocessing(self, mode: str, text: str, meta):
        """Run expensive manual-send preparation outside the UI thread."""
        self._preprocess_seq += 1
        request_id = self._preprocess_seq
        worker = InputWorker(
            window=self.window,
            request_id=request_id,
            mode=mode,
            text=text,
            meta=meta,
        )
        self._preprocess_id = request_id
        self._preprocess_worker = worker
        worker.signals.success.connect(self._preprocess_receiver.success)
        worker.signals.error.connect(self._preprocess_receiver.error)
        try:
            self.window.threadpool.start(worker)
        except Exception as e:
            self._on_preprocess_error(request_id, e)

    def _is_current_preprocess(self, request_id: int) -> bool:
        return request_id == self._preprocess_id

    def cancel_preprocessing(self):
        """Cancel continuation from the active preprocessing worker."""
        worker = self._preprocess_worker
        self._preprocess_id = None
        self._preprocess_worker = None
        if worker is not None:
            try:
                worker.cancel()
            except Exception:
                pass

    def _on_preprocess_success(self, request_id: int, text: str):
        """Continue the normal INPUT_USER pipeline after preprocessing."""
        if not self._is_current_preprocess(request_id):
            return
        self._preprocess_id = None
        self._preprocess_worker = None

        core = self.window.core
        # STOP may finish the request while a summarizer/native upload is still
        # completing. Never let that late callback resurrect this or a newer turn.
        if (not self.generating
                or self.window.controller.kernel.stopped()
                or not core.ctx.output.has_request()):
            return

        context = BridgeContext()
        context.prompt = text
        self.window.dispatch(KernelEvent(KernelEvent.INPUT_USER, {
            'context': context,
            'extra': {
                'send_initialized': True,
            },
        }))

    def _on_preprocess_error(self, request_id: int, error: Exception):
        """Abort a manual send whose asynchronous preparation failed."""
        if not self._is_current_preprocess(request_id):
            return
        self._preprocess_id = None
        self._preprocess_worker = None

        core = self.window.core
        request_meta = core.ctx.output.get_request_meta()
        self.generating = False
        self.window.controller.chat.common.sync_send_stop_buttons()
        self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
            "id": "chat",
            "msg": f"{trans('status.error')} {error}",
            "meta": request_meta,
        }))
        self._finish_request(request_meta)

    def _abort_initialized_send(self, request_meta, error: bool = False):
        """Release only the state introduced by SEND_INIT on an early abort."""
        self.generating = False
        self.window.controller.chat.common.sync_send_stop_buttons()
        state = KernelEvent.STATE_ERROR if error else KernelEvent.STATE_IDLE
        self.window.dispatch(KernelEvent(state, {
            "id": "chat",
            "meta": request_meta,
        }))
        self._finish_request(request_meta)

    def send_input(self, force: bool = False):
        """
        Send text from user input (called from UI)

        :param force: force send
        """
        dispatch = self.window.dispatch
        # Snapshot the invoker before any input/plugin event can move focus.
        # get_effective_current_pid() also sees the latest deferred column-focus
        # request, so a click+immediate Send is routed to the clicked chat.
        source_pid = self.window.controller.ui.tabs.get_effective_current_pid()
        mode = self.window.core.config.get('mode')
        event = Event(Event.INPUT_BEGIN, {
            'mode': mode,
            'force': force,
            'stop': False,
        })
        dispatch(event)
        stop = event.data.get('stop', False)

        # Get the visible text and the durable/model-facing variant.
        # Valid @mentions are serialized as durable attachment/file/conversation
        # tags only at the send boundary; the QTextEdit itself remains human-readable.
        input_node = self.window.ui.nodes['input']
        display_text = input_node.toPlainText().strip()
        if hasattr(input_node, "serialize_mentions"):
            text = input_node.serialize_mentions().strip()
        else:
            text = display_text
        history_text = text

        if not force:
            dispatch(AppEvent(AppEvent.INPUT_SENT))  # app event
            if stop:
                return

        # listen for stop command
        if self.generating \
                and display_text is not None \
                and display_text.lower().strip() in self.stop_commands:
            self.window.controller.kernel.stop()  # TODO: to chat main
            dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))
            return

        # A top-level request may already own a chat while attachments are still
        # being processed (generating can still be False in that phase). Never
        # let a second manual send steal/release that owner. STOP is handled above.
        if self.window.core.ctx.output.has_request():
            return

        # event: user input send (manually)
        event = Event(Event.USER_SEND, {
            'mode': mode,
            'value': text,
        })
        dispatch(event)
        text = event.data['value']

        # Capture the invoking chat before attachment processing / provider
        # dispatch can move focus or mutate the globally selected context.
        request_meta = self._pin_user_chat(source_pid)
        if request_meta is None:
            # begin_request() may have resolved a valid source PID even if its
            # context creation failed. Never leave such an owner dangling.
            self.window.core.ctx.output.finish_request()
            return
        # _pin_user_chat may have synchronized a different visible chat, so use
        # that chat's restored mode for the actual send/attachment pipeline.
        mode = self.window.core.config.get('mode')

        # SEND_INIT is deliberately before history/attachment preprocessing. It
        # makes the UI react to Send immediately without rendering the user row.
        dispatch(KernelEvent(KernelEvent.SEND_INIT, {
            "id": "chat",
            "meta": request_meta,
            "clear": bool(self.window.core.config.get('send_clear')) and not force,
        }))

        # SEND_INIT pumps the Qt event loop so the spinner/button change is
        # painted immediately. STOP can therefore be clicked re-entrantly while
        # this dispatch is still returning; do not start background work after it.
        if (not self.generating
                or self.window.controller.kernel.stopped()
                or not self.window.core.ctx.output.has_request()):
            return

        # Start a fresh per-turn attachment scope before processing files from
        # the input list. Conversation/project attachments remain active for
        # model context, but only items introduced after this reset belong to
        # the message being sent now.
        self.window.controller.chat.attachment.begin_turn(request_meta)

        # Store prompt history only once the manual send has actually claimed a
        # chat. History keeps the durable form so recalling it can restore the
        # semantic mention type instead of guessing from visible @text.
        try:
            # force=True is used by edit-submit; preserve the existing behavior
            # where replacing an old turn does not create a new history entry.
            if not force and hasattr(input_node, "on_prompt_sent"):
                input_node.on_prompt_sent(history_text)
        except Exception as e:
            self.window.core.debug.log(e)

        # Conversation-history resolution and attachment reading/indexing/upload
        # can involve database/model/file/network I/O. Keep all of it off the UI
        # thread, then re-enter the existing INPUT_USER flow from the worker signal.
        self._start_preprocessing(mode, text, request_meta)

    def send(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
    ):
        """
        Send input wrapper

        :param context: bridge context
        :param extra: extra data
        """
        is_internal_reply = bool(extra.get("reply")) and bool(extra.get("internal"))
        is_agent_continue = bool(extra.get("agent_continue")) and bool(extra.get("internal"))
        inline_message = extra.get("inline_message") if is_agent_continue else None
        if not isinstance(inline_message, dict):
            inline_message = None
        origin_ctx = context.ctx
        origin_mode = getattr(origin_ctx, "mode", None) if origin_ctx is not None else None
        origin_model = getattr(origin_ctx, "model", None) if origin_ctx is not None else None

        # Autonomous Agent iterations are explicit internal continuations of one
        # user-visible turn. The originating mode may be MODE_AGENT itself or an
        # ordinary mode with the inline autonomous plugin enabled, so the explicit
        # marker (rather than the currently focused UI mode) is authoritative.
        if is_agent_continue and origin_ctx is None:
            self.window.core.debug.info("[agent] Ignoring continuation without an originating context.")
            return

        # A stopped legacy autonomous run can still have late provider/tool
        # callbacks in Qt's queue. Never let them become input for a newer run.
        if (is_internal_reply or is_agent_continue) and origin_mode == MODE_AGENT:
            if not self.window.controller.agent.legacy.is_ctx_current_run(origin_ctx):
                self.window.core.debug.info(
                    "[agent] Ignoring stale internal input from an older autonomous run."
                )
                return

        # Agents v2 owns only replies originating from its own private tool
        # contexts. Do not use the currently focused/global UI mode here: in a
        # split view another column may become active while a Chat with Files
        # tool is still running, and its REPLY_RETURN must continue in the mode
        # that created the tool call.
        if is_internal_reply and origin_mode == MODE_AGENT_V2:
            self.window.core.debug.info(
                "[agents_v2] Ignoring legacy internal tool reply; tool feedback is handled in-runtime."
            )
            return

        self.execute(
            text=str(context.prompt),
            force=extra.get("force", False),
            reply=extra.get("reply", False),
            internal=extra.get("internal", False),
            prev_ctx=context.ctx,
            multimodal_ctx=context.multimodal_ctx,
            mode_override=origin_mode if (is_internal_reply or is_agent_continue) else None,
            model_override=origin_model if (is_internal_reply or is_agent_continue) else None,
            agent_continue=is_agent_continue,
            inline_message=inline_message,
            runtime_attachments=context.attachments if is_internal_reply else None,
            send_initialized=bool(extra.get("send_initialized", False)),
        )

    def execute(
            self,
            text: str,
            force: bool = False,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: Optional[CtxItem] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
            mode_override: Optional[str] = None,
            model_override: Optional[str] = None,
            agent_continue: bool = False,
            inline_message: Optional[Dict[str, str]] = None,
            runtime_attachments: Optional[dict] = None,
            send_initialized: bool = False,
    ):
        """
        Execute send input text to API

        :param text: input text
        :param force: force send (ignore input lock)
        :param reply: reply mode (from plugins)
        :param internal: internal call
        :param prev_ctx: previous context (if reply)
        :param multimodal_ctx: multimodal context
        :param mode_override: originating mode for an internal tool reply/agent continuation
        :param model_override: originating model key for an internal tool reply/agent continuation
        :param agent_continue: keep an autonomous Agent iteration in the same durable turn
        :param inline_message: optional UI-only message metadata attached to this continuation
        :param runtime_attachments: ephemeral files produced by a tool for the immediate next model request
        :param send_initialized: manual send already entered SEND_INIT busy/clear state
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        log = controller.chat.log

        # Programmatic/internal sends may bypass send_input(). Preserve an
        # existing top-level owner; otherwise derive one from the originating ctx.
        request_meta = getattr(prev_ctx, "meta", None) if prev_ctx is not None else core.ctx.output.get_request_meta()
        if request_meta is None:
            request_meta = core.ctx.get_current_meta()
        if request_meta is not None:
            if not core.ctx.output.has_request():
                owner_pid = core.ctx.output.get_pid(request_meta)
                core.ctx.output.begin_request(owner_pid)
            core.ctx.output.bind_request_meta(request_meta)
            core.ctx.output.pin_render_pid(request_meta)

        if not send_initialized:
            dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
                "id": "chat",
                "meta": request_meta,
            }))

        # check if input is not locked
        if self.locked and not force and not internal:
            if send_initialized:
                self._abort_initialized_send(request_meta)
            else:
                self._finish_request(request_meta)
            return

        log("Begin.")
        self.generating = True  # set generating flag

        # check if assistant is selected
        mode = mode_override or core.config.get('mode')
        if mode == MODE_ASSISTANT:
            if not controller.assistant.check():
                if send_initialized:
                    self._abort_initialized_send(request_meta)
                else:
                    self.generating = False  # unlock
                    self._finish_request(request_meta)
                return

        # handle camera capture
        controller.camera.handle_auto_capture(mode)

        # unlock if locked
        controller.assistant.resume()
        controller.kernel.resume()

        log(f"Input prompt: {text}")  # log

        # event: before input handle
        event = Event(Event.INPUT_BEFORE, {
            'mode': mode,
            'value': text,
            'multimodal_ctx': multimodal_ctx,
            'stop': False,
            'silent': False,  # silent mode (without error messages)
        })
        dispatch(event)
        text = event.data['value']
        stop = event.data.get('stop', False)
        silent = event.data.get('silent', False)

        if stop:  # abort via event
            if send_initialized:
                self._abort_initialized_send(request_meta, error=not silent)
            else:
                self.generating = False
                if not silent:
                    dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                        "id": "chat",
                        "meta": request_meta,
                    }))
                self._finish_request(request_meta)
            return

        # set state to: busy
        dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "chat",
            "msg": trans('status.sending'),
            "meta": request_meta,
        }))

        # clear input field if clear-on-send is enabled
        if core.config.get('send_clear') and not force and not internal and not send_initialized:
            dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))

        # create ctx, handle allowed, etc.
        dispatch(Event(Event.INPUT_ACCEPT, {
            'value': text,
            'multimodal_ctx': multimodal_ctx,
            'mode': mode,
        }))

        # start timer
        self.window.controller.chat.common.start_counter()

        # send input to API
        if mode == MODE_IMAGE:
            controller.chat.image.send(
                text=text,
                prev_ctx=prev_ctx,
            )  # image generation
        else:
            controller.chat.text.send(
                text=text,
                reply=reply,
                internal=internal,
                prev_ctx=prev_ctx,
                multimodal_ctx=multimodal_ctx,
                mode_override=mode_override,
                model_override=model_override,
                agent_continue=agent_continue,
                inline_message=inline_message,
                runtime_attachments=runtime_attachments,
            )  # text mode: OpenAI, LlamaIndex, etc.

    def handle_attachment(self, mode: str, text: str) -> bool:
        """
        Handle attachments with additional context (not images here)

        :param mode: Mode (e.g., MODE_ASSISTANT, MODE_CHAT)
        :param text: Input text
        :return: bool: True if attachments exists, False otherwise
        """
        controller = self.window.controller
        dispatch = self.window.dispatch
        exists = False

        # handle attachments with additional context (not images here)
        if mode != MODE_ASSISTANT and controller.chat.attachment.has(mode):
            exists = True
            status = "Reading attachments..."
            if self.window.core.attachments.native.get_provider(mode):
                status = "Processing attachments..."
            dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
                "id": "chat",
                "msg": status,
                "meta": self.window.core.ctx.output.get_request_meta(),
            }))
            try:
                controller.chat.attachment.handle(mode, text)
            except Exception as e:
                request_meta = self.window.core.ctx.output.get_request_meta()
                dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                    "id": "chat",
                    "msg": f"Error processing attachments: {e}",
                    "meta": request_meta,
                }))
                self._finish_request(request_meta)

        return exists
