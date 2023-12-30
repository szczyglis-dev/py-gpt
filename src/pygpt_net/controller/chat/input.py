#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 20:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input controller

        :param window: Window instance
        """
        self.window = window
        self.locked = False
        self.force_stop = False
        self.generating = False
        self.thread = None
        self.thread_started = False

    def send_text(self, text):
        """
        Send text to GPT

        :param text: text to send
        :return: context item
        :rtype: CtxItem
        """
        self.window.set_status(trans('status.sending'))

        # prepare names
        self.log("User name: {}".format(self.window.core.config.get('user_name')))  # log
        self.log("AI name: {}".format(self.window.core.config.get('ai_name')))  # log

        # event: user.name
        event = Event('user.name', {
            'value': self.window.core.config.get('user_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        user_name = event.data['value']

        # event: ai.name
        event = Event('ai.name', {
            'value': self.window.core.config.get('ai_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        ai_name = event.data['value']

        self.log("User name [after plugin: user_name]: {}".format(user_name))  # log
        self.log("AI name [after plugin: ai_name]: {}".format(ai_name))  # log

        # get mode
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')

        # create ctx item
        ctx = CtxItem()
        ctx.current = True  # mark as current context item
        ctx.mode = mode
        ctx.model = model
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)

        # upload attachments if provided and assistant mode, TODO: extract assistant thread create
        attachments = self.window.controller.chat.files.upload(mode)
        if len(attachments) > 0:
            ctx.attachments = attachments

        # store history (input)
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "input")

        # store thread id, assistant id and pass to gpt wrapper
        if mode == 'assistant':
            ctx.thread = self.window.core.config.get('assistant_thread')

        # log
        self.log("Context: input: {}".format(self.window.core.ctx.dump(ctx)))

        # event: ctx.before
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # log
        self.log("Context: input [after plugin: ctx.before]: {}".format(self.window.core.ctx.dump(ctx)))
        self.log("System: {}".format(self.window.core.gpt.system_prompt))

        # event: system.prompt
        sys_prompt = self.window.core.config.get('prompt')
        event = Event('system.prompt', {
            'value': sys_prompt,
        })
        self.window.core.dispatcher.dispatch(event)
        sys_prompt = event.data['value']

        # event: cmd.syntax (if commands enabled then append commands prompt)
        if self.window.core.config.get('cmd'):
            sys_prompt += " " + self.window.core.command.get_prompt()
            data = {
                'prompt': sys_prompt,
                'syntax': [],
            }
            event = Event('cmd.syntax', data)
            self.window.core.dispatcher.dispatch(event)
            sys_prompt = self.window.core.command.append_syntax(event.data)

        # log
        self.log("System [after plugin: system.prompt]: {}".format(sys_prompt))
        self.log("User name: {}".format(ctx.input_name))
        self.log("AI name: {}".format(ctx.output_name))
        self.log("Appending input to chat window...")

        # append text from input to chat window
        self.window.controller.chat.render.append_input(ctx)

        # add ctx to DB here and only update it after response, MUST BE REMOVED NEXT AS FIRST MSG (LAST ON LIST)!
        self.window.core.ctx.add(ctx)

        # update ctx list, but not reload all to prevent focus out on lists
        self.window.controller.ctx.update(reload=True, all=False)

        # process events to update UI
        QApplication.processEvents()

        # async or sync mode
        stream_mode = self.window.core.config.get('stream')

        try:
            # make API call
            try:
                self.window.controller.chat.common.lock_input()  # lock input

                if mode == "langchain":
                    self.log("Calling LangChain...")  # log
                    self.window.core.chain.system_prompt = sys_prompt
                    self.window.core.chain.user_name = ctx.input_name
                    self.window.core.chain.ai_name = ctx.output_name
                    result = self.window.core.chain.call(text, ctx, stream_mode)
                else:
                    self.log("Calling OpenAI API...")  # log
                    self.window.core.gpt.system_prompt = sys_prompt
                    self.window.core.gpt.user_name = ctx.input_name
                    self.window.core.gpt.ai_name = ctx.output_name
                    self.window.core.gpt.assistant_id = self.window.core.config.get('assistant')
                    self.window.core.gpt.thread_id = ctx.thread
                    self.window.core.gpt.attachments = self.window.core.attachments.get_all(mode)
                    result = self.window.core.gpt.call(text, ctx, stream_mode)

                # update context in DB
                self.window.core.ctx.update_item(ctx)

                if mode == 'assistant':
                    self.window.core.ctx.append_run(ctx.run_id)  # get run ID and save it in ctx
                    self.window.controller.assistant.threads.handle_run(ctx)  # handle assistant run

                if result:
                    self.log("Context: output: {}".format(self.window.core.ctx.dump(ctx)))  # log
                else:
                    self.log("Context: output: None")
                    self.window.ui.dialogs.alert(trans('status.error'))
                    self.window.set_status(trans('status.error'))

            except Exception as e:
                self.log("GPT output error: {}".format(e))  # log
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))
                self.window.set_status(trans('status.error'))
                print("Error when calling API: " + str(e))

            # handle response (if no assistant mode, assistant response is handled in assistant thread)
            if mode != "assistant":
                self.window.controller.chat.output.handle(ctx, mode, stream_mode)

        except Exception as e:
            self.log("Output error: {}".format(e))  # log
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))
            print("Error in sending text: " + str(e))

        # if commands enabled: post-execute commands (if no assistant mode)
        if mode != "assistant":
            self.window.controller.chat.output.handle_cmd(ctx)
            self.window.core.ctx.update_item(ctx)  # update ctx in DB
            self.window.controller.ctx.update()  # update ctx list

        self.window.controller.chat.common.unlock_input()  # unlock

        # handle ctx name (generate title from summary if not initialized), TODO: move to ctx controller
        if self.window.core.config.get('ctx.auto_summary'):
            self.window.controller.ctx.prepare_name(ctx)

        return ctx

    def user_send(self, text=None):
        """
        Send real user input

        :param text: input text
        """
        if self.generating \
                and text is not None \
                and text.strip() == "stop":
            self.window.controller.chat.common.stop()

        # event: user.send
        event = Event('user.send', {
            'value': text,
        })
        self.window.core.dispatcher.dispatch(event)
        text = event.data['value']
        self.send(text)

    def send(self, text=None, force=False):
        """
        Send input wrapper
        :param text: input text
        :param force: force send
        """
        self.send_execute(text, force)

    def send_execute(self, text=None, force=False):
        """
        Send input text to API

        :param text: input text
        :param force: force send
        """
        # check if input is not locked
        if self.locked and not force:
            return

        self.generating = True  # set generating flag
        mode = self.window.core.config.get('mode')
        if mode == 'assistant':
            # check if assistant is selected
            if self.window.core.config.get('assistant') is None or self.window.core.config.get('assistant') == "":
                self.window.ui.dialogs.alert(trans('error.assistant_not_selected'))
                self.generating = False
                return
        elif mode == 'vision':
            # handle auto-capture mode
            if self.window.controller.camera.is_enabled():
                if self.window.controller.camera.is_auto():
                    self.window.controller.camera.capture_frame(False)

        # unlock Assistant run thread if locked
        self.window.controller.assistant.threads.force_stop = False
        self.force_stop = False
        self.window.set_status(trans('status.sending'))

        ctx = None
        if text is None:
            text = self.window.ui.nodes['input'].toPlainText().strip()

        self.log("Input text: {}".format(text))  # log

        # event: input.before
        event = Event('input.before', {
            'value': text,
        })
        self.window.core.dispatcher.dispatch(event)
        text = event.data['value']

        self.log("Input text [after plugin: input.before]: {}".format(text))  # log

        # allow empty input only for vision mode
        if len(text.strip()) > 0 \
                or (mode == 'vision' and self.window.controller.attachment.has_attachments(mode)):

            # clear input area if clear-on-send enabled
            if self.window.core.config.get('send_clear') and not force:
                self.window.ui.nodes['input'].clear()

            # check API key
            if mode != 'langchain':
                if self.window.core.config.get('api_key') is None or self.window.core.config.get('api_key') == '':
                    self.window.controller.launcher.show_api_monit()
                    self.window.set_status("Missing API KEY!")
                    self.generating = False
                    return

            # prepare context, create new ctx if there is no contexts yet (first run)
            if len(self.window.core.ctx.meta) == 0:
                self.window.core.ctx.new()
                self.window.controller.ctx.update()
                self.log("New context created...")  # log
            else:
                # check if current context is allowed for this mode, if now then create new
                self.window.controller.ctx.handle_allowed(mode)

            # process events to update UI
            QApplication.processEvents()

            # send input to API
            self.generating = True  # mark as generating (lock)
            if self.window.core.config.get('mode') == 'img':
                ctx = self.window.controller.image.send_text(text)
            else:
                ctx = self.send_text(text)
        else:
            # reset status if input is empty
            self.window.statusChanged.emit("")

        # clear attachments after send if enabled
        if self.window.core.config.get('attachments_send_clear'):
            self.window.controller.attachment.clear(True)
            self.window.controller.attachment.update()

        if ctx is not None:
            self.log("Context: output: {}".format(self.window.core.ctx.dump(ctx)))  # log

            # event: ctx.end
            event = Event('ctx.end')
            event.ctx = ctx
            self.window.core.dispatcher.dispatch(event)

            self.log("Context: output [after plugin: ctx.end]: {}".
                     format(self.window.core.ctx.dump(ctx)))  # log
            self.window.controller.ui.update_tokens()  # update tokens counters

        self.generating = False  # unlock as not generating
        self.window.controller.ui.update()  # update UI

    def log(self, data):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.controller.debug.log(data, True)
