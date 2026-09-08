#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 11:20:00                  #
# ================================================== #

from typing import Dict, Any
import time
from pygpt_net.core.agents_v2.tool_bridge import is_pending, discard

from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
    MODE_ASSISTANT,
    MODE_CHAT,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import RenderEvent, KernelEvent, AppEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Response:

    AGENT_MODES_ALLOWED = (MODE_AGENT_LLAMA, MODE_AGENT_OPENAI)

    def __init__(self, window=None):
        """
        Response controller

        :param window: Window instance
        """
        super(Response, self).__init__()
        self.window = window
        self.last_response_id = None
        self._agent_v2_last_store = {}
        self._agent_v2_parts = {}
        self._agent_v2_finalizing = set()
        # Runtime part UUID currently rendered inline inside the durable bot
        # message. This is UI-only state; the parent CtxItem remains unchanged.
        self._agent_v2_inline_parts = {}

    def handle(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            status: bool
    ):
        """
        Handle Bridge success

        :param status: Result status
        :param context: BridgeContext
        :param extra: Extra data
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        ctx = context.ctx

        if not status:
            error = extra.get("error", None)
            controller.chat.log("Bridge response: ERROR")
            if error is not None:
                self.window.ui.dialogs.alert(error)
                self.window.update_status(error)
            else:
                self.window.ui.dialogs.alert(trans('status.error'))
                self.window.update_status(trans('status.error'))
        else:
            controller.chat.log_ctx(ctx, "output")  # log
            if controller.kernel.stopped():
                return

        source_ctx = ctx
        is_continuation = bool(getattr(source_ctx, "turn_parent", None))
        is_agent_continue = bool(
            is_continuation
            and isinstance(getattr(source_ctx, "extra", None), dict)
            and source_ctx.extra.get("agent_continue")
        )
        stream = bool(context.stream)
        if is_continuation:
            # Non-stream continuations can be folded immediately. A streamed
            # continuation must keep its ephemeral CtxItem until StreamWorker has
            # consumed the provider generator; merging it here would replace
            # context.ctx with the durable parent before the stream even starts.
            if status and not stream:
                ctx = core.ctx.merge_continuation(source_ctx)
                context.ctx = ctx
            elif not status:
                ctx = source_ctx.turn_parent
                context.ctx = ctx
                dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {"meta": ctx.meta}))
            else:
                ctx = source_ctx

        ctx.current = False  # reset current state
        mode = extra.get('mode', MODE_CHAT)
        reply = extra.get('reply', False)
        internal = extra.get('internal', False)
        if not is_continuation:
            core.ctx.update_item(ctx)

        # fix frozen chat
        if not status:
            failed_meta = getattr(ctx, "meta", None)
            dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {
                "meta": failed_meta,
            }))  # hide cmd waiting
            if not controller.kernel.stopped():
                controller.chat.common.unlock_input()  # unlock input
            dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                "id": "chat",
                "meta": failed_meta,
            }))
            controller.chat.input.generating = False
            if ctx is not None and failed_meta is not None:
                dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": failed_meta, "ctx": ctx}))
            core.ctx.output.finish_request(meta=failed_meta)
            controller.ui.tabs.sync_focused_chat_context()
            return

        try:
            if mode != MODE_ASSISTANT:
                if not is_continuation:
                    ctx.from_previous()
                controller.chat.output.handle(
                    ctx, mode, stream, is_response=True, reply=reply, internal=internal,
                    context=context, extra=extra, render=not is_continuation,
                )
                if is_continuation and not (stream and is_agent_continue):
                    # Tool-result continuations need an immediate durable hand-off.
                    # A streamed autonomous iteration does not: its empty partial
                    # is already persisted and Stream.handleChunk() appends into it
                    # directly. Reloading here clears/races the live stream before
                    # the first token is painted.
                    dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))
                    dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {
                        "meta": ctx.meta,
                        "ctx": ctx,
                    }))
        except Exception as e:
            extra["error"] = e
            self.failed(context, extra)

        if stream: 
            if mode not in controller.chat.output.NOT_STREAM_MODES:
                return # handled in stream:handleEnd()

        # post-handle, execute cmd, etc.
        self.post_handle(
            ctx=ctx,
            mode=mode,
            stream=stream,
            reply=reply,
            internal=internal,
        )

    def post_handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool,
            reply: bool,
            internal: bool
    ):
        """
        Post-handle response

        :param ctx: CtxItem
        :param mode: Mode of operation
        :param stream: True if stream mode
        :param reply: True if reply mode
        :param internal: True if internal mode
        """
        output = self.window.controller.chat.output
        finished = output.post_handle(ctx, mode, stream, reply, internal)
        if finished:
            output.handle_end(ctx, mode)
        return bool(finished)

    def begin(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge begin

        :param context: BridgeContext
        :param extra: Extra data
        """
        ctx = context.ctx
        ctx.stopped = False
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra.pop("response_final", None)
        ctx.extra.pop("response_interrupted", None)
        if ctx.id is not None:
            try:
                self.window.core.ctx.update_item(ctx)
            except Exception:
                pass

        msg = extra.get("msg", "")
        self.window.controller.chat.common.lock_input()  # lock input
        if msg:
            self.window.update_status(msg)

    def append(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge append (agent mode)

        :param context: BridgeContext
        :param extra: Extra data
        """
        core = self.window.core
        controller = self.window.controller
        log = controller.chat.log
        chat_output = controller.chat.output
        dispatch = self.window.dispatch
        global_mode = core.config.get("mode", MODE_AGENT_LLAMA)
        ctx = context.ctx

        # if stopped
        if controller.kernel.stopped():
            # if ctx.output and has_unclosed_code_tag(ctx.output):
                # ctx.output += "\n```"
            ctx.msg_id = None
            ctx.stopped = True
            if not isinstance(ctx.extra, dict):
                ctx.extra = {}
            ctx.extra["response_interrupted"] = True
            ctx.extra.pop("response_final", None)
            if ctx.id is None:
                if not ctx.is_empty():
                    core.ctx.add(ctx)  # store context to prevent current output from being lost
                controller.ctx.prepare_name(ctx)  # summarize if not yet
            if ctx.id is not None:
                core.ctx.update_item(ctx)
            dispatch(AppEvent(AppEvent.CTX_END))  # finish render
            dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))  # reload owning chat
            return

        prev_ctx = ctx.prev_ctx
        if prev_ctx and prev_ctx.current:
            prev_ctx.current = False  # reset previous context
            core.ctx.update_item(prev_ctx)
            prev_ctx.from_previous()  # append previous result if exists
            controller.chat.output.handle(
                ctx=prev_ctx,
                mode=prev_ctx.mode,
                stream=False,
            )
            controller.chat.output.post_handle(ctx=prev_ctx, mode=prev_ctx.mode, stream=False, reply=False, internal=False)
            controller.chat.output.handle_end(ctx=prev_ctx, mode=prev_ctx.mode)  # end previous context

        stream = context.stream

        # if next in agent cycle
        if ctx.partial:
            dispatch(AppEvent(AppEvent.CTX_END))  # app event

        # handle current step
        ctx.current = False  # reset current state
        mode = ctx.mode
        reply = ctx.reply
        internal = ctx.internal

        core.ctx.set_last_item(ctx)
        dispatch(RenderEvent(RenderEvent.BEGIN, {
            "meta": ctx.meta,
            "ctx": ctx,
            "stream": stream,
        }))

        # append step input to chat window
        dispatch(RenderEvent(RenderEvent.INPUT_APPEND, {
            "meta": ctx.meta,
            "ctx": ctx,
        }))

        # CTX OUTPUT INFO:
        # - ctx.output may be empty here if stream in OpenAI agents
        # - ctx.live_output may be used against output in LlamaIndex agents
        if ctx.id is None:
            core.ctx.add(ctx)

        core.ctx.update_item(ctx)

        # update ctx meta
        if mode in self.AGENT_MODES_ALLOWED and ctx.meta:
            core.ctx.replace(ctx.meta)  # update meta in items
            core.ctx.save(ctx.meta.id)

            # update preset if exists
            preset = controller.presets.get_current()
            if preset is not None:
                if ctx.meta.assistant is not None:
                    preset.assistant_id = ctx.meta.assistant
                    core.presets.update_and_save(preset)

        try:
            chat_output.handle(ctx, mode, stream)
        except Exception as e:
            log(f"Output ERROR: {e}")  # log
            controller.chat.handle_error(e)
            print(f"Error in append text: {e}")

        # post-handle, execute cmd, etc.
        chat_output.post_handle(ctx, mode, stream, reply, internal)
        chat_output.handle_end(ctx, mode)  # handle end.
        dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))

        # ----------- EVALUATE AGENT RESPONSE -----------

        # if continue reasoning
        if global_mode not in self.AGENT_MODES_ALLOWED:
            return  # no agent mode, nothing to do

        # agent evaluation finish
        if ctx.extra is not None and (isinstance(ctx.extra, dict) and "agent_eval_finish" in ctx.extra):
            controller.agent.llama.on_end(ctx)
            return

        # not agent final response
        #
        # APPEND_DATA for an intermediate agent step goes through the normal chat
        # output lifecycle above. That lifecycle emits STATE_IDLE from
        # handle_complete(), post_handle() and handle_end(), because for ordinary
        # chat responses the context is complete at this point. In an agent
        # workflow this is different: the rendered partial context only means that
        # one agent/step has finished and the workflow is now waiting for the next
        # agent. Re-assert BUSY *after* rendering/reload so the loading indicator
        # stays visible until the next real stream chunk arrives. The first chunk
        # is rendered with begin=True and beginStream(true) hides the spinner.
        agent_finished = isinstance(ctx.extra, dict) and "agent_finish" in ctx.extra
        if not agent_finished:
            self.window.update_status(trans("status.agent.reasoning"))
            controller.chat.common.lock_input()  # lock input, re-enable stop button
            dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
                "id": "agent",
                "msg": trans("status.agent.reasoning"),
                "meta": getattr(ctx, "meta", None),
            }))

        # agent final response, with fix for async delayed finish (prevent multiple calls for the same response)
        if agent_finished:
            consume = False
            if self.last_response_id is None or self.last_response_id < ctx.id:
                consume = True
            self.last_response_id = ctx.id
            if consume:
                controller.agent.llama.on_finish(ctx)  # evaluate response and continue if needed

    def end(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge end

        :param context: BridgeContext
        :param extra: Extra data
        """
        status = extra.get("msg", trans("status.finished"))
        self.window.update_status(status)
        self.window.controller.agent.llama.on_end()
        self.window.controller.chat.common.unlock_input()  # unlock input
        self.window.dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "chat",
            "meta": getattr(getattr(context, "ctx", None), "meta", None),
        }))

    def failed(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge failed

        :param context: BridgeContext
        :param extra: Extra data
        """
        ctx = context.ctx
        if ctx is not None:
            if not isinstance(ctx.extra, dict):
                ctx.extra = {}
            ctx.extra["response_interrupted"] = True
            ctx.extra.pop("response_final", None)
            try:
                self.window.core.ctx.update_item(ctx)
            except Exception:
                pass

        msg = extra.get("error") if "error" in extra else None
        self.window.controller.chat.log(f"Output ERROR: {msg}")  # log
        self.window.controller.chat.handle_error(msg)
        self.window.controller.chat.common.unlock_input()  # unlock input
        print(f"Error in sending text: {msg}")
        self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
            "id": "chat",
            "meta": getattr(ctx, "meta", None),
        }))
        if not extra.get("_stream_worker_error", False):
            self.window.controller.chat.input.generating = False
            if ctx is not None and getattr(ctx, "meta", None) is not None:
                self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))
            self.window.core.ctx.output.finish_request(meta=getattr(ctx, "meta", None))
            self.window.controller.ui.tabs.sync_focused_chat_context()

    def agent_v2_begin(self, context: BridgeContext, extra: Dict[str, Any]):
        """Begin the single user-visible Agents v2 response stream."""
        ctx = context.ctx
        ctx.stopped = False
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra.pop("response_final", None)
        ctx.extra.pop("response_interrupted", None)
        if ctx.id is not None:
            try:
                self.window.core.ctx.update_item(ctx)
            except Exception:
                pass
        key = getattr(ctx, "id", None) or id(ctx)
        self._agent_v2_finalizing.discard(key)
        self._agent_v2_inline_parts.pop(key, None)
        self.window.controller.chat.common.lock_input()
        # Do not allocate a durable partial from the Qt/UI side. The runtime is
        # the sole owner of Agents v2 partial creation and supplies the exact UUID
        # with every text append. Having both threads create the initial row made
        # duplicate empty/identical partials possible under signal timing races.
        part = ctx.get_active_part()
        if part is not None:
            self._agent_v2_parts[key] = part
        if ctx.output is None:
            ctx.output = ""
        self.window.dispatch(RenderEvent(RenderEvent.STREAM_BEGIN, {"meta": ctx.meta, "ctx": ctx}))

    def agent_v2_final_begin(self, context: BridgeContext, extra: Dict[str, Any]):
        """Materialize prior workflow and begin the final timeline segment.

        FINAL_BEGIN is emitted before the first final-answer chunk. Persisted
        partials/tools are reloaded first, then only the transient stream area is
        reset. The already rendered workflow remains visible above the final text.
        """
        ctx = context.ctx
        key = getattr(ctx, "id", None) or id(ctx)
        self._agent_v2_finalizing.add(key)
        self.agent_v2_status(context, extra, "")
        # The previous inline partial is already complete in the durable model.
        # Cancel its UI micro-batch before replacing the DOM, otherwise a late
        # timer could append stale text after RELOAD.
        renderer = self.window.controller.chat.render.instance()
        if hasattr(renderer, "discard_part_streams"):
            renderer.discard_part_streams(ctx.meta)
        # Clear transient statuses, then materialize every completed partial/tool
        # inside the same durable CtxItem before the final partial starts.
        self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {"meta": ctx.meta, "ctx": ctx}))
        self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))
        try:
            renderer.agent_v2_final_begin(ctx.meta, ctx)
        except Exception as exc:
            self.window.core.debug.log(exc)

    def agent_v2_append(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            chunk: str,
            begin: bool = False,
            part_begin: bool = False,
            part_uuid: str = None,
    ):
        """Append orchestrator prose, persisting each LLM pass as a partial item."""
        if self.window.controller.kernel.stopped():
            return
        ctx = context.ctx
        core_ctx = self.window.core.ctx
        key = getattr(ctx, "id", None) or id(ctx)
        previous_part = self._agent_v2_parts.get(key)
        part = None
        if part_uuid:
            for candidate in ctx.parts or []:
                if str(getattr(candidate, "uuid", "")) == str(part_uuid):
                    part = candidate
                    break
        if part is None:
            part = self._agent_v2_parts.get(key)
        if part_uuid and part is not None and str(getattr(part, "uuid", "")) != str(part_uuid):
            part = None

        if part is None and not part_uuid:
            # Compatibility fallback for legacy emitters which did not send a
            # durable part UUID. Current Agents v2 runtime always sends one.
            part = self._agent_v2_parts.get(key) or ctx.get_active_part()
            if part is None:
                part = core_ctx.ensure_part(ctx)
                if part is not None:
                    part.agent_id = "orchestrator"
                    part.name = "Orchestrator"
        elif part is None and part_uuid:
            # Never synthesize a replacement row for a UUID created by the
            # runtime. Doing so is exactly how one logical orchestrator output
            # could become two ctx_item_partial rows. Keep rendering the chunk;
            # the final commit remains defensive, but do not duplicate storage.
            try:
                self.window.core.debug.info(
                    f"[agents_v2] Missing runtime partial for UUID: {part_uuid}"
                )
            except Exception:
                pass

        # Flush the complete previous partial when the runtime switches UUIDs.
        # Per-part throttling avoids token-level SQLite writes, but without this
        # handoff flush the tail received inside the 250 ms window could remain
        # only in memory once streaming moved to the next partial.
        part_changed = bool(
            previous_part is not None
            and part is not None
            and previous_part is not part
            and str(getattr(previous_part, "uuid", "")) != str(getattr(part, "uuid", ""))
        )
        if part_changed:
            core_ctx.update_part(ctx, previous_part, sync_item=True)

        # A real runtime part boundary means that the preceding tool/text segment
        # is complete. Materialize it in the durable parent and then stream the
        # new prose as an *inline partial* of that same msg-box. Do not begin a
        # second generic stream row: that visually behaves like a new CtxItem.
        if part_begin and part_changed and key not in self._agent_v2_finalizing:
            renderer = self.window.controller.chat.render.instance()
            if hasattr(renderer, "discard_part_streams"):
                renderer.discard_part_streams(ctx.meta)
            self.window.dispatch(RenderEvent(RenderEvent.AGENT_STATUS_CLEAR, {"meta": ctx.meta, "ctx": ctx}))
            self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {"meta": ctx.meta, "ctx": ctx}))
            self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))

        self._agent_v2_parts[key] = part

        value = str(chunk or "")
        if key in self._agent_v2_finalizing and begin:
            # Token-adjacent cleanup: a status event queued before FINAL_BEGIN may
            # be delivered later by Qt. Remove it again immediately before the
            # first authoritative final token is handed to the renderer.
            self.window.dispatch(RenderEvent(RenderEvent.AGENT_STATUS_CLEAR, {"meta": ctx.meta, "ctx": ctx}))
            self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {"meta": ctx.meta, "ctx": ctx}))
        if part is not None:
            if value and not str(part.output or "").strip():
                if not isinstance(part.extra, dict):
                    part.extra = {}
                part.extra.setdefault("output_created_at", int(time.time() * 1000))
            part.append_output(value)
        # Part boundaries are rendered as separate chronological segments. Do
        # not fake that separation by prepending newlines to one shared live draft.
        render_value = value
        ctx.stream = render_value

        # Persist live output at a modest cadence. Writing SQLite on every token
        # can saturate the Qt event loop even though WebView itself batches JS.
        now = time.monotonic()
        part_store_key = (
            key,
            str(getattr(part, "uuid", "") or id(part)) if part is not None else "ctx",
        )
        last = self._agent_v2_last_store.get(part_store_key, 0.0)
        if now - last >= 0.25:
            if part is not None:
                core_ctx.update_part(ctx, part, sync_item=True)
            else:
                core_ctx.update_item(ctx)
            self._agent_v2_last_store[part_store_key] = now
        else:
            ctx.sync_output_from_parts()
        # After the first materialized boundary, all later prose is streamed
        # inside ``msg-bot-<ctx.id>`` as a partial. Track the runtime UUID so
        # subsequent chunks of the same part stay in that nested segment.
        current_part_key = str(part_uuid or getattr(part, "uuid", "") or "")
        inline_part = False
        inline_begin = False
        tracked_part_key = self._agent_v2_inline_parts.get(key)

        if current_part_key and key in self._agent_v2_finalizing:
            inline_part = True
            if tracked_part_key != current_part_key:
                self._agent_v2_inline_parts[key] = current_part_key
                inline_begin = True
        elif current_part_key and part_changed:
            inline_part = True
            self._agent_v2_inline_parts[key] = current_part_key
            inline_begin = True
        elif current_part_key and tracked_part_key == current_part_key:
            inline_part = True

        if inline_part:
            self.window.dispatch(RenderEvent(RenderEvent.STREAM_APPEND, {
                "meta": ctx.meta,
                "ctx": ctx,
                "chunk": render_value,
                "begin": bool(inline_begin),
                "partial": True,
                "part_key": current_part_key,
            }))
        else:
            # Initial orchestrator prose still uses the normal live stream because
            # no durable bot node exists yet. It will be materialized on the first
            # real part/tool boundary.
            self.window.dispatch(RenderEvent(RenderEvent.STREAM_APPEND, {
                "meta": ctx.meta,
                "ctx": ctx,
                "chunk": render_value,
                "begin": bool(begin),
            }))

    def agent_v2_status(self, context: BridgeContext, extra: Dict[str, Any], status: str):
        """Replace the transient Agents v2 status line without creating a new message."""
        ctx = context.ctx
        value = str(status or "")
        key = getattr(ctx, "id", None) or id(ctx)
        # FINAL_BEGIN is an authoritative UI barrier. Non-empty statuses queued
        # before it must not be allowed to reappear during the final stream.
        if key in self._agent_v2_finalizing and value:
            value = ""
        # Status events can already be queued when the user presses STOP/ESC.
        # Once halted, only allow cleanup events so stale rows cannot reappear.
        if self.window.controller.kernel.stopped():
            value = ""
        name = RenderEvent.AGENT_STATUS if value else RenderEvent.AGENT_STATUS_CLEAR
        self.window.dispatch(RenderEvent(name, {"meta": ctx.meta, "ctx": ctx, "status": value}))

    def agent_v2_tool_exec(self, context: BridgeContext, extra: Dict[str, Any], request):
        """Dispatch an Agents v2 plugin command without blocking Qt.

        The plugin is allowed to start its normal QRunnable and return here
        immediately. Completion is signalled later from kernel Reply.add().
        """
        if not request:
            return
        done = request.get("done")
        ctx = request.get("ctx")
        try:
            if not self.window.controller.kernel.is_main_thread():
                request["error"] = RuntimeError("Agents v2 plugin RPC reached a non-main Qt thread.")
                if done is not None:
                    done.set()
                return
            if self.window.controller.kernel.stopped():
                request["cancelled"] = True
                request["result"] = "Execution cancelled."
                if done is not None:
                    done.set()
                return

            response = self.window.controller.plugins.apply_cmds_all(
                ctx,
                request.get("cmds") or [],
            )

            # Synchronous/lightweight plugins may already have produced a reply.
            # Async plugins mark the context as pending and will wake the agent
            # later through REPLY_ADD.
            if done is not None and not done.is_set():
                pending = is_pending(ctx)
                if response not in (None, [], {}) or not pending:
                    request["result"] = response
                    discard(ctx, request)
                    done.set()
        except Exception as exc:
            request["error"] = exc
            discard(ctx, request)
            self.window.core.debug.log(exc)
            if done is not None:
                done.set()

    def agent_v2_end(self, context: BridgeContext, extra: Dict[str, Any], final_answer: str = ""):
        """Finalize Agents v2 and commit only the authoritative final answer to UI."""
        ctx = context.ctx
        core_ctx = self.window.core.ctx
        self.agent_v2_status(context, extra, "")
        ctx.current = False
        ctx.stream = None
        key = getattr(ctx, "id", None) or id(ctx)

        # The runtime marks the final orchestrator partial before starting the
        # final stream. Keep a defensive fallback for errors/legacy emitters.
        final_part = None
        for candidate in reversed(ctx.parts or []):
            candidate_extra = candidate.extra if isinstance(candidate.extra, dict) else {}
            if candidate_extra.get("agents_v2_final") is True:
                final_part = candidate
                break
        if final_answer:
            if final_part is None:
                final_part = self._agent_v2_parts.get(key) or ctx.get_active_part() or core_ctx.ensure_part(ctx)
                if final_part is not None:
                    if not isinstance(final_part.extra, dict):
                        final_part.extra = {}
                    final_part.extra["agents_v2_orchestrator"] = True
                    final_part.extra["agents_v2_final"] = True
            if final_part is not None:
                # final_answer is authoritative. AGENT_V2_APPEND is intentionally
                # throttled/queued, so the partial may contain only a prefix when
                # AGENT_V2_END reaches the UI thread. Always replace the streamed
                # draft with the complete final value before committing it.
                final_part.set_output(str(final_answer))
                core_ctx.update_part(ctx, final_part, sync_item=False)
            # Keep ctx_item.output as the compact user-facing final response. The
            # complete orchestrator trace remains in ctx_item_partial and is
            # reconstructed only by AgentsV2Memory for orchestrator history.
            ctx.output = str(final_answer)
        else:
            part = self._agent_v2_parts.get(key)
            if part is not None:
                core_ctx.update_part(ctx, part, sync_item=True)

        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        has_final = bool(str(final_answer or "").strip())
        if not has_final:
            try:
                has_final = bool(str(ctx.get_agents_v2_final_output() or "").strip())
            except Exception:
                has_final = False
        if has_final:
            ctx.stopped = False
            ctx.extra["response_final"] = True
            ctx.extra.pop("response_interrupted", None)
        elif self.window.controller.kernel.stopped():
            ctx.stopped = True
            ctx.extra["response_interrupted"] = True
            ctx.extra.pop("response_final", None)

        core_ctx.update_item(ctx)
        for store_key in list(self._agent_v2_last_store):
            if isinstance(store_key, tuple) and store_key and store_key[0] == key:
                self._agent_v2_last_store.pop(store_key, None)
            elif store_key == key:  # compatibility with pre-change in-memory keys
                self._agent_v2_last_store.pop(store_key, None)
        self._agent_v2_parts.pop(key, None)
        self._agent_v2_inline_parts.pop(key, None)
        self.window.dispatch(RenderEvent(RenderEvent.STREAM_END, {"meta": ctx.meta, "ctx": ctx}))

        if self.window.controller.kernel.stopped():
            self.window.controller.chat.output.handle_end(ctx=ctx, mode=MODE_AGENT_V2)
            self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))
            return

        self.window.controller.chat.output.handle_after(ctx=ctx, mode=MODE_AGENT_V2, stream=True)
        self.post_handle(
            ctx=ctx,
            mode=MODE_AGENT_V2,
            stream=True,
            reply=extra.get("reply", False),
            internal=extra.get("internal", False),
        )

        # Rebuild the completed message once after streaming. get_display_output()
        # returns only the final Agents v2 partial, while structured partial tasks
        # are now rendered as the grouped Tool/Tools block when the setting is on.
        self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))

    def live_append(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge live append

        :param context: BridgeContext
        :param extra: Extra data
        """
        self.window.dispatch(RenderEvent(RenderEvent.LIVE_APPEND, {
            "meta": context.ctx.meta,
            "ctx": context.ctx,
            "chunk": extra.get("chunk", ""),
            "begin": extra.get("begin", False),
        }))

    def live_clear(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge live clear

        :param context: BridgeContext
        :param extra: Extra data
        """
        self.window.dispatch(RenderEvent(RenderEvent.LIVE_CLEAR, {
            "meta": context.ctx.meta,
            "ctx": context.ctx,
        }))