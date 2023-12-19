#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import json
import threading

from PySide6.QtCore import QObject
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from ..context import ContextItem
from ..dispatcher import Event
from ..utils import trans


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

    def setup(self):
        """Set up input"""
        # stream
        if self.window.config.get('stream'):
            self.window.ui.nodes['input.stream'].setChecked(True)
        else:
            self.window.ui.nodes['input.stream'].setChecked(False)

        # send clear
        if self.window.config.get('send_clear'):
            self.window.ui.nodes['input.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.config.get('send_mode')
        if mode == 2:
            self.window.ui.nodes['input.send_shift_enter'].setChecked(True)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 1:
            self.window.ui.nodes['input.send_enter'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 0:
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(True)

        # cmd enabled
        if self.window.config.get('cmd'):
            self.window.ui.nodes['cmd.enabled'].setChecked(True)
        else:
            self.window.ui.nodes['cmd.enabled'].setChecked(False)

        # set focus to input
        self.window.ui.nodes['input'].setFocus()

    def send_text(self, text):
        """
        Send text to GPT

        :param text: text to send
        """
        self.window.set_status(trans('status.sending'))

        # prepare names
        self.window.log("User name: {}".format(self.window.config.get('user_name')))  # log
        self.window.log("AI name: {}".format(self.window.config.get('ai_name')))  # log

        # dispatch events
        event = Event('user.name', {
            'value': self.window.config.get('user_name'),
        })
        self.window.dispatch(event)
        user_name = event.data['value']

        event = Event('ai.name', {
            'value': self.window.config.get('ai_name'),
        })
        self.window.dispatch(event)
        ai_name = event.data['value']

        self.window.log("User name [after plugin: user_name]: {}".format(self.window.config.get('user_name')))  # log
        self.window.log("AI name [after plugin: ai_name]: {}".format(self.window.config.get('ai_name')))  # log

        # store history (input)
        if self.window.config.get('store_history') and text is not None and text.strip() != "":
            self.window.app.history.save(text)

        # get mode
        mode = self.window.config.get('mode')

        # clear
        self.window.app.gpt_assistants.file_ids = []  # file ids

        # upload new attachments if assistant mode
        if mode == 'assistant':
            is_upload = False
            num_uploaded = 0
            try:
                # it uploads only new attachments (not uploaded before to remote)
                attachments = self.window.app.attachments.get_all(mode)
                c = self.window.controller.assistant_files.count_upload_attachments(attachments)
                if c > 0:
                    is_upload = True
                    self.window.set_status(trans('status.uploading'))
                    num_uploaded = self.window.controller.assistant_files.upload_attachments(mode, attachments)
                    self.window.app.gpt_assistants.file_ids = self.window.app.attachments.get_ids(mode)
                # show uploaded status
                if is_upload and num_uploaded > 0:
                    self.window.set_status(trans('status.uploaded'))
            except Exception as e:
                print(e)
                self.window.ui.dialogs.alert(str(e))

            # create or get current thread, it is required here
            if self.window.config.get('assistant_thread') is None:
                try:
                    self.window.set_status(trans('status.starting'))
                    self.window.config.set('assistant_thread',
                                           self.window.controller.assistant_thread.create_thread())
                except Exception as e:
                    print(e)
                    self.window.ui.dialogs.alert(str(e))

        # create ctx item
        ctx = ContextItem()
        ctx.mode = mode
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)

        # store thread id, assistant id and pass to gpt wrapper
        if mode == 'assistant':
            ctx.thread = self.window.config.get('assistant_thread')
            self.window.app.gpt.assistant_id = self.window.config.get('assistant')
            self.window.app.gpt.thread_id = ctx.thread

        # log
        self.window.log("Context: input: {}".format(ctx.dump()))

        # dispatch event
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.dispatch(event)

        # log
        self.window.log("Context: input [after plugin: ctx.before]: {}".format(ctx.dump()))
        self.window.log("System: {}".format(self.window.app.gpt.system_prompt))

        # apply cfg, plugins
        self.window.app.gpt.user_name = ctx.input_name
        self.window.app.gpt.ai_name = ctx.output_name
        self.window.app.chain.user_name = ctx.input_name
        self.window.app.chain.ai_name = ctx.output_name

        # prepare system prompt
        sys_prompt = self.window.config.get('prompt')

        # dispatch event
        event = Event('system.prompt', {
            'value': sys_prompt,
        })
        self.window.dispatch(event)
        sys_prompt = event.data['value']

        # if commands enabled: append commands prompt
        if self.window.config.get('cmd'):
            sys_prompt += " " + self.window.app.command.get_prompt()
            data = {
                'prompt': sys_prompt,
                'syntax': [],
            }
            # dispatch event
            event = Event('cmd.syntax', data)
            self.window.dispatch(event)
            sys_prompt = self.window.app.command.append_syntax(event.data)
            self.window.app.gpt.system_prompt = sys_prompt

        # set system prompt
        self.window.app.gpt.system_prompt = sys_prompt
        self.window.app.chain.system_prompt = sys_prompt

        # log
        self.window.log("System [after plugin: system.prompt]: {}".format(self.window.app.gpt.system_prompt))
        self.window.log("User name: {}".format(self.window.app.gpt.user_name))
        self.window.log("AI name: {}".format(self.window.app.gpt.ai_name))
        self.window.log("Appending input to chat window...")

        # append input to chat window
        self.window.controller.output.append_input(ctx)
        QApplication.processEvents()  # process events to update UI

        # async or sync mode
        stream_mode = self.window.config.get('stream')

        # disable stream mode for vision mode (tmp)
        if mode == "vision":
            stream_mode = False

        # call the model
        try:
            # set attachments (attachments are separated by mode)
            self.window.app.gpt.attachments = self.window.app.attachments.get_all(mode)

            # make API call
            try:
                # lock input
                self.lock_input()

                if mode == "langchain":
                    self.window.log("Calling LangChain...")  # log
                    ctx = self.window.app.chain.call(text, ctx, stream_mode)
                else:
                    self.window.log("Calling OpenAI API...")  # log
                    ctx = self.window.app.gpt.call(text, ctx, stream_mode)

                    if mode == 'assistant':
                        # get run ID and save it in ctx
                        self.window.app.context.append_run(ctx.run_id)

                        # handle assistant run
                        self.window.controller.assistant_thread.handle_run(ctx)

                if ctx is not None:
                    self.window.log("Context: output: {}".format(ctx.dump()))  # log
                else:
                    # error in call if ctx is None
                    self.window.log("Context: output: None")
                    self.window.ui.dialogs.alert(trans('status.error'))
                    self.window.set_status(trans('status.error'))

            except Exception as e:
                self.window.log("GPT output error: {}".format(e))  # log
                print("Error in send text (GPT call): " + str(e))
                self.window.ui.dialogs.alert(str(e))
                self.window.set_status(trans('status.error'))

            # handle response (if no assistant mode)
            if mode != "assistant":
                self.window.controller.output.handle_response(ctx, mode, stream_mode)

        except Exception as e:
            self.window.log("Output error: {}".format(e))  # log
            print("Error sending text: " + str(e))
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

        # if commands enabled: post-execute commands (if no assistant mode)
        if mode != "assistant":
            self.window.controller.output.handle_commands(ctx)
            self.unlock_input()

        # handle ctx name (generate title from summary if not initialized)
        if self.window.config.get('ctx.auto_summary'):
            self.window.controller.output.handle_ctx_name(ctx)

        return ctx

    def user_send(self, text=None):
        """
        Send real user input

        :param text: input text
        """
        # dispatch event
        event = Event('user.send', {
            'value': text,
        })
        self.window.dispatch(event)
        text = event.data['value']
        self.send(text)

    def send(self, text=None):
        """
        Send input wrapper
        :param text: input text
        """
        self.send_execute(text)

    def start_thread(self, text):
        """
        Handle thread start

        :param ctx: ContextItem
        """
        sender = SendThread(window=self.window, text=text)
        self.thread = threading.Thread(target=sender.run)
        self.thread.start()
        self.thread_started = True

    def send_execute(self, text=None):
        """
        Send input text to API

        :param text: input text
        """
        # check if input is not locked
        if self.locked:
            return

        self.generating = True  # set generating flag
        mode = self.window.config.get('mode')
        if mode == 'assistant':
            # check if assistant is selected
            if self.window.config.get('assistant') is None or self.window.config.get('assistant') == "":
                self.window.ui.dialogs.alert(trans('error.assistant_not_selected'))
                self.generating = False
                return
        elif mode == 'vision':
            # handle auto-capture mode
            if self.window.controller.camera.is_enabled():
                if self.window.controller.camera.is_auto():
                    self.window.controller.camera.capture_frame(False)

        # unlock Assistant run thread if locked
        self.window.controller.assistant_thread.force_stop = False
        self.force_stop = False
        self.window.set_status(trans('status.sending'))

        ctx = None
        if text is None:
            text = self.window.ui.nodes['input'].toPlainText().strip()

        self.window.log("Input text: {}".format(text))  # log

        # dispatch event
        event = Event('input.before', {
            'value': text,
        })
        self.window.dispatch(event)
        text = event.data['value']

        self.window.log("Input text [after plugin: input.before]: {}".format(text))  # log

        # allow empty input only for vision mode
        if len(text.strip()) > 0 \
                or (mode == 'vision' and self.window.controller.attachment.has_attachments(mode)):

            # clear input area if clear-on-send enabled
            if self.window.config.get('send_clear'):
                self.window.ui.nodes['input'].clear()

            # check API key
            if mode != 'langchain':
                if self.window.config.get('api_key') is None or self.window.config.get('api_key') == '':
                    self.window.controller.launcher.show_api_monit()
                    self.window.set_status("Missing API KEY!")
                    self.generating = False
                    return

            # init api key if defined later
            self.window.app.gpt.init()
            self.window.app.images.init()

            # prepare context, create new ctx if there is no contexts yet (first run)
            if len(self.window.app.context.contexts) == 0:
                self.window.app.context.new()
                self.window.controller.context.update()
                self.window.log("New context created...")  # log
            else:
                # check if current context is allowed for this mode, if now then create new
                self.window.controller.context.handle_allowed(mode)

            # process events to update UI
            QApplication.processEvents()

            # send input to API
            self.generating = True  # mark as generating (lock)
            if self.window.config.get('mode') == 'img':
                ctx = self.window.controller.image.send_text(text)
            else:
                ctx = self.send_text(text)
        else:
            # reset status if input is empty
            self.window.statusChanged.emit("")

        # clear attachments after send if enabled
        if self.window.config.get('attachments_send_clear'):
            self.window.controller.attachment.clear(True)
            self.window.controller.attachment.update()

        if ctx is not None:
            self.window.log("Context: output: {}".format(ctx.dump()))  # log

            # dispatch event
            event = Event('ctx.end')
            event.ctx = ctx
            self.window.dispatch(event)

            self.window.log("Context: output [after plugin: ctx.end]: {}".format(ctx.dump()))  # log
            self.window.controller.ui.update_tokens()  # update tokens counters

            # from v.2.0.41: reply from commands in now handled in async thread!
            # if ctx.reply:
            #   self.send(json.dumps(ctx.results))

            self.generating = False
            self.window.controller.ui.update()  # update UI
            return

        self.generating = False  # unlock as not generating
        self.window.controller.ui.update()  # update UI

    def toggle_stream(self, value):
        """
        Toggle stream

        :param value: value of the checkbox
        """
        self.window.config.set('stream', value)

    def toggle_cmd(self, value):
        """
        Toggle cmd enabled

        :param value: value of the checkbox
        """
        self.window.config.set('cmd', value)

        # stop commands thread if running
        if not value:
            self.window.controller.command.force_stop = True
        else:
            self.window.controller.command.force_stop = False

    def toggle_send_clear(self, value):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.config.set('send_clear', value)

    def toggle_send_shift(self, value):
        """
        Toggle send with shift

        :param value: value of the checkbox
        """
        self.window.config.set('send_mode', value)

    def lock_input(self):
        """
        Lock input
        """
        self.locked = True
        self.window.ui.nodes['input.send_btn'].setEnabled(False)
        self.window.ui.nodes['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """
        Unlock input
        """
        self.locked = False
        self.window.ui.nodes['input.send_btn'].setEnabled(True)
        self.window.ui.nodes['input.stop_btn'].setVisible(False)

    def stop(self):
        """
        Stop input
        """
        event = Event('audio.input.toggle', {"value": False})
        self.window.controller.assistant_thread.force_stop = True
        self.window.dispatch(event)  # stop audio input
        self.force_stop = True
        self.window.app.gpt.stop()
        self.unlock_input()
        self.generating = False
        self.window.set_status(trans('status.stopped'))

    def append(self, text):
        """
        Append text to input

        :param text: text to append
        """
        cur = self.window.ui.nodes['input'].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.window.ui.nodes['input'].setTextCursor(cur)  # Update visible cursor


class SendThread(QObject):
    def __init__(self, window=None, text=None):
        """
        Run summarize thread

        :param window: Window instance
        :param ctx: ContextItem
        """
        super().__init__()
        self.window = window
        self.text = text

    def run(self):
        """Run thread"""
        try:
            self.window.controller.input.send_execute(self.text)
        except Exception as e:
            print(e)
