#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.01 01:00:00                  #
# ================================================== #

from typing import Optional

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AUDIO,
    MODE_ASSISTANT,
    MODE_LLAMA_INDEX,
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
        self.ctx_pid = 0

    def send(
            self,
            text: str,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: Optional[CtxItem] = None,
            parent_id: Optional[str] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
    ) -> CtxItem:
        """
        Send text message

        :param text: text to send
        :param reply: reply from plugins
        :param internal: internal call
        :param prev_ctx: previous context item (if reply)
        :param parent_id: parent context id
        :param multimodal_ctx: multimodal context
        :return: context item
        """
        self.window.update_status(trans('status.sending'))

        # event: prepare username
        event = Event(Event.USER_NAME, {
            'value': self.window.core.config.get('user_name'),
        })
        self.window.dispatch(event)
        user_name = event.data['value']

        # event: prepare ai.name
        event = Event(Event.AI_NAME, {
            'value': self.window.core.config.get('ai_name'),
        })
        self.window.dispatch(event)
        ai_name = event.data['value']

        # prepare mode, model, etc.
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        model_data = self.window.core.models.get(model)
        stream_mode = self.window.core.config.get('stream')
        agent_provider = self.window.core.config.get('agent.llama.provider')
        agent_idx = self.window.core.config.get('agent.llama.idx')
        sys_prompt = self.window.core.config.get('prompt')
        sys_prompt_raw = sys_prompt  # store raw prompt (without addons)
        max_tokens = self.window.core.config.get('max_output_tokens')  # max output tokens
        base_mode = mode  # store parent mode
        functions = []  # functions to call
        tools_outputs = []  # tools outputs (assistant only)
        idx_mode = self.window.core.config.get('llama.idx.mode')

        # o1 models: disable stream mode
        if mode in [MODE_AGENT_LLAMA, MODE_AUDIO]:
            stream_mode = False
        if mode in [MODE_LLAMA_INDEX] and idx_mode == "retrieval":
            stream_mode = False
        if mode in [MODE_LLAMA_INDEX]:
            if not self.window.core.idx.chat.is_stream_allowed():
                stream_mode = False

        # create ctx item
        ctx = CtxItem()
        ctx.meta = self.window.core.ctx.get_current_meta()  # CtxMeta (owner object)
        ctx.internal = internal
        ctx.current = True  # mark as current context item
        ctx.mode = mode  # store current selected mode (not inline changed)
        ctx.model = model  # store model list key, not real model id
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)
        ctx.prev_ctx = prev_ctx  # store previous context item if exists
        ctx.live = True
        ctx.pid = self.ctx_pid  # store PID
        self.ctx_pid += 1  # increment PID

        # if prev ctx is not empty, then copy input name to current ctx
        if prev_ctx is not None and prev_ctx.sub_call is True:  # sub_call = sent from expert
            ctx.input_name = prev_ctx.input_name

        # if reply from expert command
        if parent_id is not None:  # parent_id = reply from expert
            # At this point, ctx.meta ID = slave META ID (parent_id is given from slave, not from master)
            ctx.sub_reply = True  # mark as sub reply
            ctx.input_name = prev_ctx.input_name
            ctx.output_name = prev_ctx.output_name
        else:
            self.window.core.ctx.set_last_item(ctx)  # store last item

        self.window.controller.files.uploaded_ids = []  # clear uploaded files ids at the beginning

        # assistant: create thread, upload attachments
        if mode == MODE_ASSISTANT:
            self.window.controller.assistant.begin(ctx)

        # store in history (input only)
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "input")        

        self.window.controller.chat.log_ctx(ctx, "input")  # log

        # agent mode: before context
        if mode == MODE_AGENT:
            self.window.controller.agent.legacy.on_ctx_before(ctx)

        # event: context before
        event = Event(Event.CTX_BEFORE)
        event.ctx = ctx
        self.window.dispatch(event)

        # agent or expert mode
        sys_prompt = self.window.controller.agent.experts.append_prompts(mode, sys_prompt, parent_id)

        # on pre prompt event
        event = Event(Event.PRE_PROMPT, {
            'mode': mode,
            'value': str(sys_prompt),
        })
        self.window.dispatch(event)
        sys_prompt = event.data['value']

        # tool calls
        disable_native_func_calls = False
        if mode == MODE_LLAMA_INDEX:
            # check if index is selected
            if self.window.controller.idx.index_selected():
                disable_native_func_calls = True
                # ^^^ native func calls allowed only for LLM call, not for the query engine

        # build final prompt (+plugins)
        sys_prompt = self.window.core.prompt.prepare_sys_prompt(
            mode=mode,
            model=model_data,
            sys_prompt=sys_prompt,
            ctx=ctx,
            reply=reply,
            internal=internal,
            disable_native_tool_calls=disable_native_func_calls,
        )

        self.window.controller.chat.log("Appending input to chat window...")

        # render: begin
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
            "stream": stream_mode,
        }
        event = RenderEvent(RenderEvent.BEGIN, data)
        self.window.dispatch(event)

        # append text from input to chat window
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.INPUT_APPEND, data)
        self.window.dispatch(event)

        # add ctx to DB here and only update it after response,
        # MUST BE REMOVED AFTER AS FIRST MSG (LAST ON LIST)
        self.window.core.ctx.add(ctx, parent_id=parent_id)

        # update ctx list, but not reload all to prevent focus out on lists
        self.window.controller.ctx.update(
            reload=True,
            all=False,
        )

        # functions: prepare user and plugins functions (native mode only)
        functions += self.window.core.command.get_functions(parent_id)

        # assistant only
        if mode == MODE_ASSISTANT:
            # prepare tool outputs for assistant
            tools_outputs = self.window.controller.assistant.threads.handle_tool_outputs(ctx)
            if len(tools_outputs) > 0:
                self.window.controller.chat.log("Tool outputs sending...")

        # make API call
        try:
            # get attachments
            files = self.window.core.attachments.get_all(mode)
            num_files = len(files)
            if num_files > 0:
                self.window.controller.chat.log("Attachments ({}): {}".format(mode, num_files))

            # assistant
            assistant_id = self.window.core.config.get('assistant')
            if mode == MODE_AGENT_LLAMA:
                preset = self.window.controller.presets.get_current()
                if preset is not None:
                    assistant_id = preset.assistant_id

            self.window.dispatch(AppEvent(AppEvent.INPUT_CALL))  # app event
            bridge_context = BridgeContext(
                ctx=ctx,
                history=self.window.core.ctx.all(meta_id=parent_id),  # get all ctx items
                mode=mode,
                parent_mode=base_mode,
                model=model_data,
                system_prompt=sys_prompt,
                system_prompt_raw=sys_prompt_raw,  # for llama-index (query mode only)
                prompt=text,  # input text
                stream=stream_mode,  # is stream mode
                attachments=files,
                file_ids=self.window.controller.files.uploaded_ids,  # uploaded files IDs
                assistant_id=assistant_id,
                idx=self.window.controller.idx.current_idx,  # current idx
                idx_mode=idx_mode,  # llama index mode (chat or query)
                external_functions=functions,  # external functions
                tools_outputs=tools_outputs,  # if not empty then will submit outputs to assistant
                max_tokens=max_tokens,  # max output tokens
                multimodal_ctx=multimodal_ctx,  # multimodal context
            )
            extra = {
                'mode': mode,
                'reply': reply,
                'internal': internal,
            }
            if mode == MODE_AGENT_LLAMA:
                extra['agent_idx'] = agent_idx
                extra['agent_provider'] = agent_provider

            self.window.controller.chat.common.lock_input()  # lock input
            event = KernelEvent(KernelEvent.REQUEST, {
                'context': bridge_context,
                'extra': extra,
            })
            self.window.dispatch(event)

        except Exception as e:
            self.window.controller.chat.log("Bridge call ERROR: {}".format(e))  # log
            self.window.controller.chat.handle_error(e)
            print("Error when calling bridge: " + str(e))

        return ctx
