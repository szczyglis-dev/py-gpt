#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 19:05:00                  #
# ================================================== #

from typing import Any, Optional

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_ASSISTANT,
    MODE_IMAGE,
    MODE_AUDIO,
)
from pygpt_net.core.events import Event, AppEvent, RenderEvent, KernelEvent
from pygpt_net.item.ctx import CtxItem


class Output:

    STATE_PARAMS = {
        "id": "chat",
    }

    NOT_STREAM_MODES = (
        MODE_ASSISTANT,
        MODE_IMAGE
    )

    def __init__(self, window=None):
        """
        Output controller

        :param window: Window instance
        """
        self.window = window

    def handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool = False,
            is_response: bool = False,
            reply: bool = False,
            internal: bool = False,
            context: Optional[BridgeContext] = None,
            extra: Optional[dict] = None,
            render: bool = True,
    ):
        """
        Handle response from LLM

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream: stream enabled (local)
        :param is_response: Is response output
        :param reply: is reply
        :param internal: is internal command
        :param context: BridgeContext (optional)
        :param extra: Extra data (optional)
        """
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "meta": getattr(ctx, "meta", None),
        }))  # state: busy

        # if stream then append chunk by chunk
        end = True
        if stream:  # local, not global config
            if mode not in self.NOT_STREAM_MODES:
                end = False  # don't end if stream mode, append chunk by chunk
                self.window.controller.chat.stream.append(
                    ctx=ctx,
                    mode=mode,
                    is_response=is_response,
                    reply=reply,
                    internal=internal,
                    context=context,
                    extra=extra,
                )

        if end:
            self.handle_after(
                ctx=ctx,
                mode=mode,
                stream=stream,
                render=render,
            )

    def handle_after(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool = False,
            render: bool = True,
    ):
        """
        Handle response from LLM

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream: stream enabled (local)
        """
        core = self.window.core
        dispatch = self.window.dispatch
        log = self.window.controller.chat.log

        # Normalize both native tool calls and legacy <tool> syntax into
        # structured commands/tasks. Tool syntax is removed from visible output;
        # the request itself is rendered later from ctx_item_partial_task.
        part = ctx.get_active_part()
        multi_part = part is not None and len(ctx.parts or []) > 1
        legacy_source = part.output if multi_part else ctx.output
        legacy_cmds = core.command.extract_cmds(legacy_source)
        if legacy_cmds:
            ctx.cmds_before = legacy_cmds
            if multi_part:
                # Continuations are folded into one parent item before this
                # handler runs. Strip protocol markup from the active partial,
                # not from the already-composed parent cache.
                part.output = core.command.strip_cmds(part.output)
                core.ctx.update_part(ctx, part, sync_item=True)
            else:
                ctx.output = core.command.strip_cmds(ctx.output)

        if ctx.tool_calls:
            if not isinstance(ctx.extra, dict):
                ctx.extra = {}
            ctx.extra["tool_calls"] = list(ctx.tool_calls)
            if not ctx.cmds_before:
                ctx.cmds_before = core.command.tool_calls_to_cmds(ctx.tool_calls)
            log("Tool call received...")

        # ``goal_update`` in autonomous Agent mode is a local run-control signal,
        # not an executable plugin tool. Consume it before deciding whether this
        # response needs a tool roundtrip. This is especially important for
        # native function calls: a terminal goal_update-only response must finish
        # the current turn instead of waiting forever for a synthetic tool result.
        if mode == MODE_AGENT:
            self.window.controller.agent.legacy.consume_control_commands(ctx)

        has_tool_request = bool(ctx.tool_calls or ctx.cmds_before)
        part = ctx.get_active_part()
        if part is not None:
            # Simple/legacy responses still write directly to ctx.output. For a
            # multi-part turn (tool continuation / Agents v2), the active part
            # has already been updated by the continuation merger/streamer.
            # Copying the composed parent output back into that last part would
            # duplicate all previous partial outputs on every tool roundtrip.
            if len(ctx.parts or []) <= 1:
                part.output = ctx.output
                core.ctx.update_part(ctx, part, sync_item=True)
            else:
                ctx.sync_output_from_parts()

        # event: context after
        dispatch(Event(Event.CTX_AFTER, {
            'mode': mode,
        }, ctx=ctx))

        log("Appending output to chat window...")

        # only append output if not in stream mode. Continuation responses are
        # rebuilt in-place from the parent item, so they suppress incremental
        # node creation and use RELOAD instead.
        stream_global = core.config.get('stream', False)
        if render and not stream:
            if stream_global:
                dispatch(RenderEvent(RenderEvent.INPUT_APPEND, {
                    "meta": ctx.meta, "ctx": ctx, "flush": True, "append": True,
                }))
            if ctx.get_display_output():
                dispatch(RenderEvent(RenderEvent.OUTPUT_APPEND, {"meta": ctx.meta, "ctx": ctx}))
                dispatch(RenderEvent(RenderEvent.EXTRA_APPEND, {
                    "meta": ctx.meta, "ctx": ctx, "footer": True,
                }))

        # A tool request is an intermediate state of the same turn. Do not run
        # post-update/history/audio/unlock until a later response contains no
        # further tool calls.
        if not has_tool_request:
            self.handle_complete(ctx)
        return has_tool_request

    def handle_complete(self, ctx: CtxItem):
        """
        Handle completed context

        :param ctx: CtxItem
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        mode = getattr(ctx, 'mode', None) or core.config.get('mode')

        # post update context, store last mode, etc.
        core.ctx.post_update(mode)
        core.ctx.store()

        controller.ctx.update_ctx()
        controller.chat.audio.handle_output(ctx)  # handle audio output
        controller.chat.common.auto_unlock(ctx)  # unlock input if allowed
        if mode != MODE_AUDIO:
            controller.chat.common.show_response_tokens(ctx)  # update tokens
            state = dict(self.STATE_PARAMS)
            state["meta"] = getattr(ctx, "meta", None)
            dispatch(KernelEvent(KernelEvent.STATE_IDLE, state))  # state: idle
        else:
            if not controller.audio.is_recording():
                self.window.update_status("...")  # wait for audio

    def post_handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool = False,
            reply: bool = False,
            internal: bool = False
    ):
        """
        Post handle results

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream: stream mode
        :param reply: is reply
        :param internal: is internal
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch

        # Post-execute tools through one common lifecycle. expert_call is a regular
        # plugin tool now, so it is recorded, executed and returned exactly like
        # every other local command.
        pending = False
        if mode != MODE_ASSISTANT:
            ctx.clear_reply()  # reset results
            pending = bool(controller.chat.command.handle(ctx))

            ctx.from_previous()
            core.ctx.update_item(ctx)

        if pending:
            # TOOL_CALL is queued in kernel.stack. Safety-confirmed/internal force
            # calls may already execute inline and leave the stack empty; handle()
            # is a no-op in that case.
            controller.kernel.stack.handle()
            return False

        # Mark a durable, tool-free response as final. This marker is used only
        # when reconstructing history/reloading the WebView so completed turns do
        # not replay transient "Planning..." / "Using tool..." rows.
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        interrupted = bool(getattr(ctx, "stopped", False) or ctx.extra.get("response_interrupted"))
        if not interrupted:
            ctx.stopped = False
            ctx.extra["response_final"] = True
            ctx.extra.pop("response_interrupted", None)
            core.ctx.update_item(ctx)
        else:
            ctx.extra.pop("response_final", None)
            core.ctx.update_item(ctx)

        # render: end
        if ctx.sub_calls == 0:
            dispatch(RenderEvent(RenderEvent.END, {
                "meta": ctx.meta, "ctx": ctx, "stream": stream,
            }))

        controller.chat.common.auto_unlock(ctx)
        controller.ctx.prepare_summary(ctx)

        if self.window.state != self.window.STATE_ERROR and mode != MODE_ASSISTANT:
            state = dict(self.STATE_PARAMS)
            state["meta"] = getattr(ctx, "meta", None)
            dispatch(KernelEvent(KernelEvent.STATE_IDLE, state))
        return True

    def handle_end(
            self,
            ctx: CtxItem,
            mode: str
    ):
        """
        Handle context end (finish output)

        :param ctx: CtxItem
        :param mode: mode
        """
        controller = self.window.controller
        dispatch = self.window.dispatch
        log = controller.chat.log

        controller.attachment.cleanup(ctx)  # clear after send
        log(f"Context: END: {ctx}" if self.window.core.config.get("log.ctx") else "Context: END.")

        # event: context end
        dispatch(Event(Event.CTX_END, {
            'mode': mode,
        }, ctx=ctx))

        # RenderEvent.END may drop the render pin before the final RELOAD below.
        # Restore it while the request is still marked as generating so the
        # owning chat cannot be remapped to another focused chat tab.
        render_output = self.window.core.ctx.output
        render_output.pin_render_pid(getattr(ctx, "meta", None))

        controller.chat.input.generating = False  # unlock

        log("End.")
        dispatch(AppEvent(AppEvent.CTX_END))  # app event

        # restore state to idle if no errors
        if self.window.state != self.window.STATE_ERROR:
            state = dict(self.STATE_PARAMS)
            state["meta"] = getattr(ctx, "meta", None)
            dispatch(KernelEvent(KernelEvent.STATE_IDLE, state))

        if mode != MODE_ASSISTANT:
            controller.kernel.stack.handle()  # handle reply
            dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))  # reload owning chat

        # Keep ownership through the final reload. If stack.handle()
        # synchronously started a continuation, it is still the same top-level
        # request and ownership must survive. Otherwise release now and only then
        # synchronize core.ctx with whichever chat the user focused meanwhile.
        if not controller.chat.input.generating:
            render_output.finish_request(meta=getattr(ctx, "meta", None))
            controller.ui.tabs.sync_focused_chat_context()
