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

from typing import Optional

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
    MODE_AUDIO,
    MODE_ASSISTANT,
    MODE_LLAMA_INDEX,
    MODE_COMPUTER,
)
from pygpt_net.core.events import Event, AppEvent, KernelEvent, RenderEvent
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Text:
    def __init__(self, window=None):
        """
        Text input controller

        :param window: Window instance
        """
        self.window = window
        self.ctx_pid = 0  # sequence number for context items

    def send(
            self,
            text: str,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: Optional[CtxItem] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
            mode_override: Optional[str] = None,
            model_override: Optional[str] = None,
    ) -> CtxItem:
        """
        Send text message

        :param text: text to send
        :param reply: reply from plugins
        :param internal: internal call
        :param prev_ctx: previous context item (if reply)
        :param multimodal_ctx: multimodal context
        :param mode_override: originating mode for an internal tool reply
        :param model_override: originating model key for an internal tool reply
        :return: CtxItem instance
        """
        self.window.update_status(trans("status.sending"))

        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        config = core.config
        log = controller.chat.log

        # event: prepare username
        event = Event(Event.USER_NAME, {
            "value": config.get("user_name"),
        })
        dispatch(event)
        user_name = event.data["value"]

        # event: prepare AI name
        event = Event(Event.AI_NAME, {
            "value": config.get("ai_name"),
        })
        dispatch(event)
        ai_name = event.data["value"]

        # Internal tool feedback is a continuation of the same durable turn.
        continuation_parent = None
        if reply and internal and prev_ctx is not None:
            continuation_parent = getattr(prev_ctx, "turn_parent", None)

        # prepare mode, model, etc.
        mode = mode_override or (getattr(continuation_parent, "mode", None) if continuation_parent else None) or config.get("mode")
        model = model_override or (getattr(continuation_parent, "model", None) if continuation_parent else None) or config.get("model")
        model_data = core.models.get(model)
        sys_prompt = config.get("prompt")
        sys_prompt_raw = sys_prompt  # store raw prompt (without addons)
        max_tokens = config.get("max_output_tokens")  # max output tokens
        idx_mode = config.get("llama.idx.mode")
        base_mode = mode  # store base parent mode
        # Tool-result continuations stay in the same durable CtxItem, but they
        # should use the mode's normal streaming policy just like the initial
        # response. The ephemeral continuation is merged into the durable parent
        # only after its stream finishes (see controller.chat.stream).
        stream = self.is_stream(mode)

        functions = []  # functions to call
        tools_outputs = []  # tools outputs (assistant only)

        # create ctx item
        meta = continuation_parent.meta if continuation_parent is not None else core.ctx.get_current_meta()
        if meta and continuation_parent is None:
            meta.preset = config.get("preset")  # current preset

        # Capture the owning chat before rendering starts.  The shared input can
        # be used while keyboard focus is inside Code Interpreter/another tool
        # in the second column; that focus must not redirect or orphan the send.
        if meta is not None:
            core.ctx.output.pin_render_pid(meta)

        ctx = CtxItem()
        ctx.meta = meta  # CtxMeta (owner object)
        ctx.internal = internal
        ctx.current = True  # mark as current context item
        ctx.mode = mode  # store current selected mode (not inline changed)
        ctx.model = model  # store model list key, not real model id
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)
        ctx.prev_ctx = prev_ctx  # provider-facing previous reply lineage
        ctx.live = True
        ctx.pid = self.ctx_pid  # store PID
        if continuation_parent is not None:
            ctx.turn_parent = continuation_parent
            ctx.turn_previous_part = getattr(prev_ctx, "turn_previous_part", None)
            ctx.turn_continuation = True
            # Do not allocate a new partial for every tool round. A partial is a
            # textual assistant fragment; tool-only continuations keep appending
            # CtxItemPartTask rows to the current partial. merge_continuation()
            # decides whether an actual new text response needs a new partial.
            ctx.turn_part = continuation_parent.get_active_part()

        self.ctx_pid += 1  # increment PID

        # if prev ctx is not empty, then copy input name to current ctx
        if prev_ctx is not None and prev_ctx.sub_call is True:  # sub_call = sent from expert
            ctx.input_name = prev_ctx.input_name

        if reply:
            ctx.extra["sub_reply"] = True  # mark as sub reply in extra data

        controller.files.reset()  # clear uploaded files IDs
        if continuation_parent is None:
            controller.ctx.store_history(ctx, "input")  # store only the user-visible turn input
        controller.chat.log_ctx(ctx, "input")  # log

        # assistant: create thread, upload attachments
        if mode == MODE_ASSISTANT:
            controller.assistant.begin(ctx)

        # event: ctx before
        dispatch(Event(Event.CTX_BEFORE, {
            "mode": mode,
        }, ctx=ctx))

        # event: on pre prompt
        event = Event(Event.PRE_PROMPT, {
            "mode": mode,
            "value": str(sys_prompt),
        })
        dispatch(event)
        sys_prompt = event.data["value"]

        # build final prompt (+plugins)
        sys_prompt = core.prompt.prepare_sys_prompt(
            mode=mode,
            model=model_data,
            sys_prompt=sys_prompt,
            ctx=ctx,
            reply=reply,
            internal=internal,
        )

        log("Appending input to chat window...")

        if continuation_parent is None:
            # One BEGIN/input pair per user-visible turn. Tool feedback never
            # creates another chat row.
            dispatch(RenderEvent(RenderEvent.BEGIN, {
                "meta": ctx.meta,
                "ctx": ctx,
                "stream": stream,
            }))
            dispatch(RenderEvent(RenderEvent.INPUT_APPEND, {
                "meta": ctx.meta,
                "ctx": ctx,
            }))
            core.ctx.add(ctx)
            core.ctx.set_last_item(ctx)
            controller.ctx.update(reload=True, all=False)
        else:
            # Keep the durable parent as the active/last turn. ctx exists only
            # long enough to preserve the provider's tool-result protocol shape.
            core.ctx.set_last_item(continuation_parent)

        # prepare user and plugin tools (native mode only)
        functions.extend(core.command.get_functions())

        # assistant only - prepare tool outputs for assistant
        if mode == MODE_ASSISTANT:
            tools_outputs = controller.assistant.threads.handle_tool_outputs(ctx)
            if len(tools_outputs) > 0:
                log("Tool outputs sending...")

        # --------------------- BRIDGE CALL ---------------------

        try:
            files = core.attachments.get_all(mode)  # get attachments
            num_files = len(files)
            if num_files > 0:
                log(f"Attachments ({mode}): {num_files}")

            context = BridgeContext(
                assistant_id=config.get("assistant"),
                attachments=files,
                ctx=ctx, # CtxItem instance
                external_functions=functions,  # external functions
                file_ids=controller.files.get_ids(),  # uploaded files IDs
                history=(core.ctx.all() + [ctx]) if continuation_parent is not None else core.ctx.all(),
                idx=controller.idx.get_current(),  # current idx
                idx_mode=idx_mode,  # llama index mode (chat or query)
                max_tokens=max_tokens,  # max output tokens
                mode=mode,
                model=model_data, # ModelItem instance
                multimodal_ctx=multimodal_ctx,  # multimodal context
                parent_mode=base_mode,
                preset=controller.presets.get_current(),  # current preset
                prompt=text,  # input text
                stream=stream,  # is stream enabled
                system_prompt=sys_prompt,
                system_prompt_raw=sys_prompt_raw,  # for llama-index (query mode only)
                tools_outputs=tools_outputs,  # if not empty then will submit outputs to assistant
            )
            extra = {
                "mode": mode,
                "reply": reply,
                "internal": internal,
            }

            # event: bridge before
            dispatch(Event(Event.BRIDGE_BEFORE, {
                "mode": mode,
                "context": context,
                "extra": extra,
            }))

            controller.chat.common.lock_input()  # lock input
            dispatch(AppEvent(AppEvent.INPUT_CALL))  # app event
            dispatch(KernelEvent(KernelEvent.REQUEST, {
                "context": context,
                "extra": extra,
            }))

        except Exception as e:
            controller.chat.handle_error(e)
            log(f"Bridge call ERROR: {e}")

        return ctx

    def is_stream(self, mode: str) -> bool:
        """
        Check if stream is enabled for given mode

        :param mode: mode
        :return: True if stream is enabled, False otherwise
        """
        core = self.window.core
        stream = core.config.get("stream")
        if mode == MODE_AGENT_V2:
            return True  # Agents v2 always renders one continuous orchestrator response
        if mode in (MODE_AGENT_LLAMA):
            return False  # TODO: check if this is correct in agent
        elif mode == MODE_LLAMA_INDEX:
            if core.config.get("llama.idx.mode") == "retrieval":
                return False
            if not core.idx.chat.is_stream_allowed():
                return False
        return stream