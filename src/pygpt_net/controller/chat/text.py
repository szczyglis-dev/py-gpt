#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

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

        # create ctx item
        ctx = CtxItem()
        ctx.meta_id = self.window.core.ctx.current
        ctx.internal = internal
        ctx.current = True  # mark as current context item
        ctx.mode = mode  # store current selected mode (not inline changed)
        ctx.model = model  # store model list key, not real model id
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)
        ctx.prev_ctx = prev_ctx  # store previous context item if exists

        # if prev ctx is not empty, then copy input name to current ctx
        if prev_ctx is not None and prev_ctx.sub_call is True:  # sub_call = sent from expert
            ctx.input_name = prev_ctx.input_name

        # if reply from expert command
        if parent_id is not None:  # parent_id = reply from expert
            ctx.meta_id = parent_id  # append to current ctx
            ctx.sub_reply = True  # mark as sub reply
            ctx.input_name = prev_ctx.input_name
            ctx.output_name = prev_ctx.output_name
        else:
            self.window.core.ctx.last_item = ctx  # store last item

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
        self.window.controller.chat.render.begin(stream=stream_mode)

        # append text from input to chat window
        self.window.controller.chat.render.append_input(ctx)
        self.window.ui.nodes['output'].update()

        QApplication.processEvents()

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

        try:
            # make API call
            try:
                # get attachments
                files = self.window.core.attachments.get_all(mode)
                num_files = len(files)
                if num_files > 0:
                    self.log("Attachments ({}): {}".format(mode, num_files))

                self.window.core.dispatcher.dispatch(AppEvent(AppEvent.INPUT_CALL))  # app event

                # make call
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

                self.window.controller.chat.common.lock_input()  # lock input
                result = self.window.core.bridge.call(
                    context=bridge_context,
                )

                # update context in DB
                ctx.current = False  # reset current state
                self.window.core.ctx.update_item(ctx)

                if result:
                    self.log_ctx(ctx, "output")  # log
                else:
                    self.log("Context: OUTPUT: ERROR")
                    self.window.ui.dialogs.alert(trans('status.error'))
                    self.window.ui.status(trans('status.error'))

            except Exception as e:
                self.log("Bridge call ERROR: {}".format(e))  # log
                self.handle_error(e)
                print("Error when calling bridge: " + str(e))

            # handle response (not assistant mode - assistant response is handled by assistant thread)
            if mode != "assistant":
                ctx.from_previous()  # append previous result if exists
                self.window.controller.chat.output.handle(
                    ctx,
                    mode,
                    stream_mode,
                )

        except Exception as e:
            self.log("Output ERROR: {}".format(e))  # log
            self.handle_error(e)
            print("Error in sending text: " + str(e))

        # post-handle, execute cmd, etc.
        self.window.controller.chat.output.post_handle(ctx, mode, stream_mode, reply, internal)

        return ctx

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
