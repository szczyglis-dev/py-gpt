#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 02:00:00                  #
# ================================================== #

import threading

from PySide6.QtCore import QObject
from PySide6.QtGui import QTextCursor
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

    def setup(self):
        """Set up input"""
        # stream
        if self.window.core.config.get('stream'):
            self.window.ui.nodes['input.stream'].setChecked(True)
        else:
            self.window.ui.nodes['input.stream'].setChecked(False)

        # send clear
        if self.window.core.config.get('send_clear'):
            self.window.ui.nodes['input.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.core.config.get('send_mode')
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
        if self.window.core.config.get('cmd'):
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
        self.log("User name: {}".format(self.window.core.config.get('user_name')))  # log
        self.log("AI name: {}".format(self.window.core.config.get('ai_name')))  # log

        # dispatch events
        event = Event('user.name', {
            'value': self.window.core.config.get('user_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        user_name = event.data['value']

        event = Event('ai.name', {
            'value': self.window.core.config.get('ai_name'),
        })
        self.window.core.dispatcher.dispatch(event)
        ai_name = event.data['value']

        self.log("User name [after plugin: user_name]: {}".format(self.window.core.config.get('user_name')))  # log
        self.log("AI name [after plugin: ai_name]: {}".format(self.window.core.config.get('ai_name')))  # log

        # get mode
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')

        # clear
        self.window.core.gpt.assistants.file_ids = []  # file ids

        # upload new attachments if assistant mode
        attachments_list = {}

        if mode == 'assistant':
            is_upload = False
            num_uploaded = 0
            try:
                # upload only new attachments (not uploaded yet to remote)
                attachments = self.window.core.attachments.get_all(mode)
                c = self.window.controller.assistant.files.count_upload(attachments)
                if c > 0:
                    is_upload = True
                    self.window.set_status(trans('status.uploading'))
                    num_uploaded = self.window.controller.assistant.files.upload(mode, attachments)
                    self.window.core.gpt.assistants.file_ids = self.window.core.attachments.get_ids(mode)
                    attachments_list = self.window.core.gpt.attachments.make_json_list(attachments)
                # show uploaded status
                if is_upload and num_uploaded > 0:
                    self.window.set_status(trans('status.uploaded'))
            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))

            # create or get current thread, it is required here
            if self.window.core.config.get('assistant_thread') is None:
                try:
                    self.window.set_status(trans('status.starting'))
                    self.window.core.config.set('assistant_thread',
                                                self.window.controller.assistant.threads.create_thread())
                except Exception as e:
                    self.window.core.debug.log(e)
                    self.window.ui.dialogs.alert(str(e))

        # create ctx item
        ctx = CtxItem()
        ctx.current = True  # mark as current context item
        ctx.mode = mode
        ctx.model = model
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)

        # attachments
        if len(attachments_list) > 0:
            ctx.attachments = attachments_list

        # store history (input)
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "input")

        # store thread id, assistant id and pass to gpt wrapper
        if mode == 'assistant':
            ctx.thread = self.window.core.config.get('assistant_thread')
            self.window.core.gpt.assistant_id = self.window.core.config.get('assistant')
            self.window.core.gpt.thread_id = ctx.thread

        # log
        self.log("Context: input: {}".format(self.window.core.ctx.dump(ctx)))

        # dispatch event
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # log
        self.log("Context: input [after plugin: ctx.before]: {}".format(self.window.core.ctx.dump(ctx)))
        self.log("System: {}".format(self.window.core.gpt.system_prompt))

        # apply cfg, plugins
        self.window.core.gpt.user_name = ctx.input_name
        self.window.core.gpt.ai_name = ctx.output_name
        self.window.core.chain.user_name = ctx.input_name
        self.window.core.chain.ai_name = ctx.output_name

        # prepare system prompt
        sys_prompt = self.window.core.config.get('prompt')

        # dispatch event
        event = Event('system.prompt', {
            'value': sys_prompt,
        })

        self.window.core.dispatcher.dispatch(event)

        sys_prompt = event.data['value']

        # if commands enabled: append commands prompt
        if self.window.core.config.get('cmd'):
            sys_prompt += " " + self.window.core.command.get_prompt()
            data = {
                'prompt': sys_prompt,
                'syntax': [],
            }
            # dispatch cmd syntax event
            event = Event('cmd.syntax', data)
            self.window.core.dispatcher.dispatch(event)
            sys_prompt = self.window.core.command.append_syntax(event.data)
            self.window.core.gpt.system_prompt = sys_prompt

        # append system prompt
        self.window.core.gpt.system_prompt = sys_prompt
        self.window.core.chain.system_prompt = sys_prompt

        # log
        self.log("System [after plugin: system.prompt]: {}".format(self.window.core.gpt.system_prompt))
        self.log("User name: {}".format(self.window.core.gpt.user_name))
        self.log("AI name: {}".format(self.window.core.gpt.ai_name))
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

        # call the model
        try:
            # set attachments (attachments are separated by mode)
            self.window.core.gpt.attachments = self.window.core.attachments.get_all(mode)

            # make API call
            try:
                # lock input
                self.lock_input()

                if mode == "langchain":
                    self.log("Calling LangChain...")  # log
                    ctx = self.window.core.chain.call(text, ctx, stream_mode)

                    # update context in DB
                    if ctx is not None:
                        self.window.core.ctx.update_item(ctx)
                else:
                    self.log("Calling OpenAI API...")  # log
                    ctx = self.window.core.gpt.call(text, ctx, stream_mode)

                    # update context in DB
                    if ctx is not None:
                        self.window.core.ctx.update_item(ctx)

                    if mode == 'assistant':
                        # get run ID and save it in ctx
                        self.window.core.ctx.append_run(ctx.run_id)

                        # handle assistant run
                        self.window.controller.assistant.threads.handle_run(ctx)

                if ctx is not None:
                    self.log("Context: output: {}".format(self.window.core.ctx.dump(ctx)))  # log
                else:
                    # there was an error in call if ctx is None here
                    self.log("Context: output: None")
                    self.window.ui.dialogs.alert(trans('status.error'))
                    self.window.set_status(trans('status.error'))

            except Exception as e:
                self.log("GPT output error: {}".format(e))  # log
                print("Error in send text (GPT call): " + str(e))
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))
                self.window.set_status(trans('status.error'))

            # handle response (if no assistant mode, assistant response is handled in assistant thread)
            if mode != "assistant":
                self.window.controller.chat.output.handle_response(ctx, mode, stream_mode)

        except Exception as e:
            self.log("Output error: {}".format(e))  # log
            print("Error sending text: " + str(e))
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

        # if commands enabled: post-execute commands (if no assistant mode)
        if mode != "assistant":
            self.window.controller.chat.output.handle_commands(ctx)

            # update ctx in DB
            self.window.core.ctx.update_item(ctx)

            # unlock
            self.unlock_input()

            # update ctx list
            self.window.controller.ctx.update()

        # handle ctx name (generate title from summary if not initialized)
        if self.window.core.config.get('ctx.auto_summary'):
            self.window.controller.chat.output.handle_ctx_name(ctx)

        return ctx

    def user_send(self, text=None):
        """
        Send real user input

        :param text: input text
        """
        if self.generating \
                and text is not None \
                and text.strip() == "stop":
            self.stop()

        # dispatch event
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

    def start_thread(self, text):
        """
        Handle thread start

        :param text: input text
        """
        sender = SendThread(window=self.window, text=text)
        self.thread = threading.Thread(target=sender.run)
        self.thread.start()
        self.thread_started = True

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

        # dispatch event
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

            # dispatch event
            event = Event('ctx.end')
            event.ctx = ctx
            self.window.core.dispatcher.dispatch(event)

            self.log("Context: output [after plugin: ctx.end]: {}".
                     format(self.window.core.ctx.dump(ctx)))  # log
            self.window.controller.ui.update_tokens()  # update tokens counters

            # from v.2.0.41: reply from commands in now handled in async thread!
            # if ctx.reply:
            #   self.send(json.dumps(ctx.results))

        self.generating = False  # unlock as not generating
        self.window.controller.ui.update()  # update UI

    def toggle_stream(self, value):
        """
        Toggle stream

        :param value: value of the checkbox
        """
        self.window.core.config.set('stream', value)

    def toggle_cmd(self, value):
        """
        Toggle cmd enabled

        :param value: value of the checkbox
        """
        self.window.core.config.set('cmd', value)

        # stop commands thread if running
        if not value:
            self.window.controller.command.force_stop = True
        else:
            self.window.controller.command.force_stop = False

        self.window.controller.ui.update_tokens()  # update tokens counters

    def toggle_send_clear(self, value):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.core.config.set('send_clear', value)

    def toggle_send_shift(self, value):
        """
        Toggle send with shift

        :param value: value of the checkbox
        """
        self.window.core.config.set('send_mode', value)

    def lock_input(self):
        """Lock input"""
        self.locked = True
        self.window.ui.nodes['input.send_btn'].setEnabled(False)
        self.window.ui.nodes['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """Unlock input"""
        self.locked = False
        self.window.ui.nodes['input.send_btn'].setEnabled(True)
        self.window.ui.nodes['input.stop_btn'].setVisible(False)

    def stop(self):
        """Stop input"""
        event = Event('audio.input.toggle', {"value": False})
        self.window.controller.assistant.threads.force_stop = True
        self.window.core.dispatcher.dispatch(event)  # stop audio input
        self.force_stop = True
        self.window.core.gpt.stop()
        self.unlock_input()
        self.generating = False
        self.window.set_status(trans('status.stopped'))

    def append_text(self, text):
        """
        Append text to notepad

        :param text: Text to append
        :param i: Notepad index
        """
        prev_text = self.window.ui.nodes['input'].toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + text.strip()
        self.window.ui.nodes['input'].setText(new_text)
        cur = self.window.ui.nodes['input'].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)

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

    def log(self, data):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.controller.debug.log(data, True)


class SendThread(QObject):
    def __init__(self, window=None, text=None):
        """
        Run summarize thread

        :param window: Window instance
        :param ctx: CtxItem
        """
        super().__init__()
        self.window = window
        self.text = text

    def run(self):
        """Run thread"""
        try:
            self.window.controller.chat.input.send_execute(self.text)
        except Exception as e:
            self.window.core.debug.log(e)
