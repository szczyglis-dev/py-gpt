#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.12 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot

from pygpt_net.core.access.events import AppEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Text:
    def __init__(self, window=None):
        """
        Text input controller

        :param window: Window instance
        """
        self.window = window

    def send(
            self,
            text: str,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: CtxItem = None,
            parent_id: str = None,
    ) -> CtxItem:
        """
        Send text message

        :param text: text to send
        :param reply: reply from plugins
        :param internal: internal call
        :param prev_ctx: previous context item (if reply)
        :param parent_id: parent context id
        :return: context item
        """
        self.window.ui.status(trans('status.sending'))

        # event: prepare username
        event = Event(Event.USER_NAME, {
            'value': self.window.core.config.get('user_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        user_name = event.data['value']

        # event: prepare ai.name
        event = Event(Event.AI_NAME, {
            'value': self.window.core.config.get('ai_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        ai_name = event.data['value']

        # prepare mode, model, etc.
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        model_data = self.window.core.models.get(model)
        stream_mode = self.window.core.config.get('stream')
        sys_prompt = self.window.core.config.get('prompt')
        sys_prompt_raw = sys_prompt  # store raw prompt (without addons)
        max_tokens = self.window.core.config.get('max_output_tokens')  # max output tokens
        base_mode = mode  # store parent mode
        functions = []  # functions to call
        tools_outputs = []  # tools outputs (assistant only)

        # o1 models: disable stream mode
        if model.startswith("o1"):
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

        # if prev ctx is not empty, then copy input name to current ctx
        if prev_ctx is not None and prev_ctx.sub_call is True:  # sub_call = sent from expert
            ctx.input_name = prev_ctx.input_name

        # if reply from expert command
        if parent_id is not None:  # parent_id = reply from expert
            ctx.meta = self.window.core.ctx.get_meta_by_id(parent_id)  # append to current ctx
            ctx.sub_reply = True  # mark as sub reply
            ctx.input_name = prev_ctx.input_name
            ctx.output_name = prev_ctx.output_name
        else:
            self.window.core.ctx.set_last_item(ctx)  # store last item

        self.window.controller.files.uploaded_ids = []  # clear uploaded files ids at the beginning

        # assistant: create thread, upload attachments
        if mode == 'assistant':
            self.window.controller.assistant.begin(ctx)

        # store in history (input only)
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "input")        

        self.log_ctx(ctx, "input")  # log

        # agent mode: before context
        if mode == 'agent':
            self.window.controller.agent.flow.on_ctx_before(ctx)

        # event: context before
        event = Event(Event.CTX_BEFORE)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # agent or expert mode
        sys_prompt = self.window.controller.agent.experts.append_prompts(mode, sys_prompt, parent_id)

        # on pre prompt event
        event = Event(Event.PRE_PROMPT, {
            'mode': mode,
            'value': sys_prompt,
        })
        self.window.core.dispatcher.dispatch(event)
        sys_prompt = event.data['value']

        # build final prompt (+plugins)
        sys_prompt = self.window.core.prompt.prepare_sys_prompt(
            mode,
            sys_prompt,
            ctx,
            reply,
            internal,
        )

        self.log("Appending input to chat window...")

        # render: begin
        self.window.controller.chat.render.begin(ctx.meta, ctx, stream=stream_mode)

        # append text from input to chat window
        self.window.controller.chat.render.append_input(ctx.meta, ctx)
        self.window.ui.nodes['output'].update()

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
        if mode == 'assistant':
            # prepare tool outputs for assistant
            tools_outputs = self.window.controller.assistant.threads.handle_tool_outputs(ctx)
            if len(tools_outputs) > 0:
                self.log("Tool outputs sending...")

        # make API call
        try:
            # get attachments
            files = self.window.core.attachments.get_all(mode)
            num_files = len(files)
            if num_files > 0:
                self.log("Attachments ({}): {}".format(mode, num_files))

            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.INPUT_CALL))  # app event
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
                assistant_id=self.window.core.config.get('assistant'),
                idx=self.window.controller.idx.current_idx,  # current idx
                idx_mode=self.window.core.config.get('llama.idx.mode'),  # llama index mode (chat or query)
                external_functions=functions,  # external functions
                tools_outputs=tools_outputs,  # if not empty then will submit outputs to assistant
                max_tokens=max_tokens,  # max output tokens
            )
            extra = {
                'mode': mode,
                'reply': reply,
                'internal': internal,
                'has_attachments': num_files > 0,
            }
            self.window.controller.chat.common.lock_input()  # lock input
            self.window.core.bridge.call(
                context=bridge_context,
                extra=extra,
            )  # async handled via handle_bridge_*

        except Exception as e:
            self.log("Bridge call ERROR: {}".format(e))  # log
            self.handle_error(e)
            print("Error when calling bridge: " + str(e))

        return ctx

    @Slot(bool, object, dict)
    def handle_bridge_success(self, status: bool, bridge_context: BridgeContext, extra: dict):
        """
        Handle Bridge success

        :param status: Result status
        :param bridge_context: BridgeContext
        :param extra: Extra data
        """
        ctx = bridge_context.ctx
        if not status:
            self.log("Context: OUTPUT: ERROR")
            self.window.ui.dialogs.alert(trans('status.error'))
            self.window.ui.status(trans('status.error'))
        else:
            self.log_ctx(ctx, "output")  # log

        ctx.current = False  # reset current state
        stream = bridge_context.stream
        mode = extra.get('mode', 'chat')
        reply = extra.get('reply', False)
        internal = extra.get('internal', False)
        has_attachments = extra.get('has_attachments', False)
        self.window.core.ctx.update_item(ctx)

        try:
            if mode != "assistant":
                ctx.from_previous()  # append previous result if exists
                self.window.controller.chat.output.handle(
                    ctx,
                    mode,
                    stream,
                )
        except Exception as e:
            self.log("Output ERROR: {}".format(e))  # log
            self.handle_error(e)
            print("Error in sending text: " + str(e))

        # post-handle, execute cmd, etc.
        self.window.controller.chat.output.post_handle(ctx, mode, stream, reply, internal)
        self.window.controller.chat.output.handle_end(ctx, mode, has_attachments)  # handle end.

    @Slot(object)
    def handle_bridge_failed(self, err: any):
        """
        Handle Bridge failed

        :param err: Exception
        """
        self.log("Output ERROR: {}".format(err))  # log
        self.handle_error(err)
        print("Error in sending text: " + str(err))

    def handle_error(self, e: any):
        """
        Handle error

        :param e: Exception
        """
        self.window.core.debug.log(e)
        self.window.ui.dialogs.alert(e)
        self.window.ui.status(trans('status.error'))
        self.window.controller.chat.common.unlock_input()  # always unlock input on error
        self.window.stateChanged.emit(self.window.STATE_ERROR)
        self.window.core.dispatcher.dispatch(AppEvent(AppEvent.INPUT_ERROR))  # app event

        # stop agent on error
        if self.window.controller.agent.enabled():
            self.window.controller.agent.flow.on_stop()

    def log_ctx(self, ctx: CtxItem, mode: str):
        """
        Log context item

        :param ctx: CtxItem
        :param mode: mode (input/output)
        """
        if self.window.core.config.get("log.ctx"):
            self.log("Context: {}: {}".format(mode.upper(), ctx.dump()))  # log
        else:
            self.log("Context: {}.".format(mode.upper()))

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
