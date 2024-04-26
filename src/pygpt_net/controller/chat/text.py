#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

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
            prev_ctx: CtxItem = None
    ) -> CtxItem:
        """
        Send text message

        :param text: text to send
        :param reply: reply from plugins
        :param internal: internal call
        :param prev_ctx: previous context item (if reply)
        :return: context item
        """
        self.window.ui.status(trans('status.sending'))
        is_ctx_debug = self.window.core.config.get("log.ctx")

        # event: username prepare
        event = Event(Event.USER_NAME, {
            'value': self.window.core.config.get('user_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        user_name = event.data['value']

        # event: ai.name
        event = Event(Event.AI_NAME, {
            'value': self.window.core.config.get('ai_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        ai_name = event.data['value']

        # get mode
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        model_data = self.window.core.models.get(model)

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

        self.window.core.ctx.last_item = ctx  # store last item

        # store thread id, assistant id and pass to gpt wrapper
        if mode == 'assistant':
            self.window.controller.assistant.prepare()  # create new thread if not exists
            ctx.thread = self.window.core.config.get('assistant_thread')

        # upload assistant attachments (only assistant mode here)
        attachments = self.window.controller.chat.files.upload(mode)  # current thread is already in global config
        if len(attachments) > 0:
            ctx.attachments = attachments
            self.window.ui.status(trans('status.sending'))
            self.log("Uploaded attachments (Assistant): {}".format(len(attachments)))

        # store history (input)
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "input")        

        if is_ctx_debug:
            self.log("Context: INPUT: {}".format(ctx))
        else:
            self.log("Context: INPUT.")

        # agent mode
        if mode == 'agent':
            self.window.controller.agent.flow.on_ctx_before(ctx)

        # event: context before
        event = Event(Event.CTX_BEFORE)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # event: prepare prompt (replace system prompt)
        sys_prompt = self.window.core.config.get('prompt')
        sys_prompt_raw = sys_prompt  # store raw prompt
        event = Event(Event.PRE_PROMPT, {
            'mode': mode,
            'value': sys_prompt,
        })
        self.window.core.dispatcher.dispatch(event)
        sys_prompt = event.data['value']

        # agent mode
        if mode == 'agent':
            sys_prompt = self.window.controller.agent.flow.on_system_prompt(
                sys_prompt,
                append_prompt=None,  # sys prompt from preset is used here
                auto_stop=self.window.core.config.get('agent.auto_stop'),
            )

        # event: system prompt (append to system prompt)
        event = Event(Event.SYSTEM_PROMPT, {
            'mode': mode,
            'value': sys_prompt,
        })
        self.window.core.dispatcher.dispatch(event)
        sys_prompt = event.data['value']

        # event: post prompt (post-handle system prompt)
        event = Event(Event.POST_PROMPT, {
            'mode': mode,
            'reply': reply,
            'internal': internal,
            'value': sys_prompt,
        })
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)
        sys_prompt = event.data['value']

        # event: command syntax apply (if commands enabled or inline plugin then append commands prompt)
        if self.window.core.config.get('cmd') or self.window.controller.plugins.is_type_enabled("cmd.inline"):
            data = {
                'mode': mode,
                'prompt': sys_prompt,
                'syntax': [],
                'cmd': [],
            }
            # full execute cmd syntax
            if self.window.core.config.get('cmd'):
                event = Event(Event.CMD_SYNTAX, data)
                self.window.core.dispatcher.dispatch(event)
                sys_prompt = self.window.core.command.append_syntax(event.data)

            # inline cmd syntax only
            elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
                event = Event(Event.CMD_SYNTAX_INLINE, data)
                self.window.core.dispatcher.dispatch(event)
                sys_prompt = self.window.core.command.append_syntax(event.data)

        self.log("Appending input to chat window...")

        # stream mode
        stream_mode = self.window.core.config.get('stream')

        # render: begin
        self.window.controller.chat.render.begin(stream=stream_mode)

        # append text from input to chat window
        self.window.controller.chat.render.append_input(ctx)
        self.window.ui.nodes['output'].update()
        QApplication.processEvents()

        # add ctx to DB here and only update it after response,
        # MUST BE REMOVED NEXT AS FIRST MSG (LAST ON LIST)
        self.window.core.ctx.add(ctx)

        # update ctx list, but not reload all to prevent focus out on lists
        self.window.controller.ctx.update(
            reload=True,
            all=False,
        )

        # process events to update UI
        #QApplication.processEvents()

        # get external functions (if preset is chosen and functions are defined)
        functions = self.window.controller.presets.get_current_functions()

        # assistant only
        tools_outputs = []
        if mode == 'assistant':
            if self.window.controller.assistant.threads.is_running():
                tools_outputs = self.window.controller.assistant.threads.apply_outputs(ctx)
                self.window.controller.assistant.threads.reset()  # reset outputs
                self.log("Appended Assistant tool outputs: {}".format(len(tools_outputs)))

                # clear tool calls to prevent appending cmds to output (otherwise it will call commands again)
                ctx.tool_calls = []

        try:
            # make API call
            try:
                self.window.controller.chat.common.lock_input()  # lock input
                files = self.window.core.attachments.get_all(mode)  # get attachments
                num_files = len(files)
                if num_files > 0:
                    self.log("Attachments ({}): {}".format(mode, num_files))

                # make call
                result = self.window.core.bridge.call(
                    mode=mode,
                    model=model_data,
                    ctx=ctx,
                    prompt=text,
                    system_prompt=sys_prompt,
                    system_prompt_raw=sys_prompt_raw,
                    stream=stream_mode,
                    attachments=files,
                    assistant_id=self.window.core.config.get('assistant'),
                    idx=self.window.controller.idx.current_idx,
                    idx_raw=self.window.core.config.get('llama.idx.raw'),  # query mode
                    external_functions=functions,  # external functions
                    tools_outputs=tools_outputs,  # if not empty then will submit outputs
                )

                # update context in DB
                ctx.current = False  # reset current state
                self.window.core.ctx.update_item(ctx)

                if result:
                    if is_ctx_debug:
                        self.log("Context: OUTPUT: {}".format(ctx.dump()))  # log
                    else:
                        self.log("Context: OUTPUT.")
                else:
                    self.log("Context: OUTPUT: ERROR")
                    self.window.ui.dialogs.alert(trans('status.error'))
                    self.window.ui.status(trans('status.error'))

            except Exception as e:
                self.log("GPT output error: {}".format(e))  # log
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(e)
                self.window.ui.status(trans('status.error'))
                print("Error when calling API: " + str(e))
                self.window.stateChanged.emit(self.window.STATE_ERROR)

            # handle response (if no assistant mode)
            # assistant response is handled in assistant thread
            if mode != "assistant":
                ctx.from_previous()  # append previous result if exists
                self.window.controller.chat.output.handle(
                    ctx,
                    mode,
                    stream_mode,
                )

        except Exception as e:
            self.log("Output ERROR: {}".format(e))  # log
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            self.window.ui.status(trans('status.error'))
            print("Error in sending text: " + str(e))
            self.window.stateChanged.emit(self.window.STATE_ERROR)

        # if commands enabled: post-execute commands (if no assistant mode)
        if mode != "assistant":
            ctx.clear_reply()  # reset results
            self.window.controller.chat.output.handle_cmd(ctx)
            ctx.from_previous()  # append previous result again before save
            self.window.core.ctx.update_item(ctx)  # update ctx in DB

        # render: end
        self.window.controller.chat.render.end(stream=stream_mode)

        # don't unlock input and leave stop btn if assistant mode or if agent/autonomous is enabled
        # send btn will be unlocked in agent mode on stop
        if mode != "assistant" and not self.window.controller.agent.enabled():
            self.window.controller.chat.common.unlock_input()  # unlock input if not assistant and agent mode

        # handle ctx name (generate title from summary if not initialized)
        if not reply and not internal:  # don't call if reply or internal mode
            if self.window.core.config.get('ctx.auto_summary'):
                self.log("Calling for prepare context name...")
                self.window.controller.ctx.prepare_name(ctx)  # async

        return ctx

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
