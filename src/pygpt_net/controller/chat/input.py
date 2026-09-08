#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 11:15:00                  #
# ================================================== #

from typing import Optional, Any, Dict

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
from pygpt_net.utils import trans


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

        # get text from input
        text = self.window.ui.nodes['input'].toPlainText().strip()

        if not force:
            dispatch(AppEvent(AppEvent.INPUT_SENT))  # app event
            if stop:
                return

        # listen for stop command
        if self.generating \
                and text is not None \
                and text.lower().strip() in self.stop_commands:
            self.window.controller.kernel.stop()  # TODO: to chat main
            dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))
            return

        # A provider-flagged Computer Use operation is waiting for explicit user confirmation.
        # While pending, only the literal "continue" command is consumed as approval; other
        # input is kept in the editor and is not sent to the model.
        if self.window.controller.chat.command.has_pending_safety_confirmation():
            is_continue = str(text or "").strip().lower() == "continue"
            if self.window.controller.chat.command.handle_pending_safety_input(text):
                if is_continue:
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

        # if attachments, return here - send will be handled via signal after upload
        if self.handle_attachment(mode, text):
            return

        # kernel event: handle input
        context = BridgeContext()
        context.prompt = text
        dispatch(KernelEvent(KernelEvent.INPUT_USER, {
            'context': context,
            'extra': {},
        }))

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

        dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "chat",
            "meta": request_meta,
        }))

        # check if input is not locked
        if self.locked and not force and not internal:
            self._finish_request(request_meta)
            return

        log("Begin.")
        self.generating = True  # set generating flag

        # check if assistant is selected
        mode = mode_override or core.config.get('mode')
        if mode == MODE_ASSISTANT:
            if not controller.assistant.check():
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
        if core.config.get('send_clear') and not force and not internal:
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
