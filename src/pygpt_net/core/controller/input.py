#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from ..context import ContextItem
from ..utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input controller

        :param window: main window
        """
        self.window = window

    def setup(self):
        """Sets up input"""
        if self.window.config.data['send_clear']:
            self.window.data['input.send_clear'].setChecked(True)
        else:
            self.window.data['input.send_clear'].setChecked(False)

        if self.window.config.data['send_shift_enter']:
            self.window.data['input.send_shift_enter'].setChecked(True)
            self.window.data['input.send_enter'].setChecked(False)
        else:
            self.window.data['input.send_enter'].setChecked(True)
            self.window.data['input.send_shift_enter'].setChecked(False)

        self.window.data['input'].setFocus()

    def toggle_send_clear(self, value):
        """
        Toggles send clear

        :param value: value of the checkbox
        """
        self.window.config.data['send_clear'] = value

    def toggle_send_shift(self, value):
        """
        Toggles send with shift

        :param value: value of the checkbox
        """
        self.window.config.data['send_shift_enter'] = value

    def send_text(self, text):
        """
        Sends text to GPT

        :param text: text to send
        """
        self.window.statusChanged.emit(trans('status.sending'))

        # prepare names
        self.window.log("User name: {}".format(self.window.config.data['user_name']))  # log
        self.window.log("AI name: {}".format(self.window.config.data['ai_name']))  # log

        user_name = self.window.controller.plugins.apply('user.name', self.window.config.data['user_name'])
        ai_name = self.window.controller.plugins.apply('ai.name', self.window.config.data['ai_name'])

        self.window.log("User name [after plugin: user_name]: {}".format(self.window.config.data['user_name']))  # log
        self.window.log("AI name [after plugin: ai_name]: {}".format(self.window.config.data['ai_name']))  # log

        # create ctx item
        ctx = ContextItem()
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)

        self.window.log("Context: input: {}".format(ctx.dump()))  # log

        # apply plugins
        ctx = self.window.controller.plugins.apply('ctx.before', ctx)

        # logger
        self.window.log("Context: input [after plugin: ctx.before]: {}".format(ctx.dump()))  # log
        self.window.log("System: {}".format(self.window.gpt.system_prompt))  # log

        # apply cfg
        self.window.gpt.user_name = ctx.input_name
        self.window.gpt.ai_name = ctx.output_name
        self.window.gpt.system_prompt = self.window.controller.plugins.apply('system.prompt',
                                                                             self.window.config.data['prompt'])

        self.window.log("System [after plugin: system.prompt]: {}".format(self.window.gpt.system_prompt))  # log
        self.window.log("User name: {}".format(self.window.gpt.user_name))  # log
        self.window.log("AI name: {}".format(self.window.gpt.ai_name))  # log
        self.window.log("Appending input to chat window...")  # log

        self.window.controller.output.append_input(ctx)

        # call GPT
        try:
            try:
                self.window.log("Calling OpenAI API...")  # log
                ctx = self.window.gpt.call(text, ctx)
                self.window.log("Context: output: {}".format(ctx.dump()))  # log
            except Exception as e:
                self.window.log("GPT output error: {}".format(e))  # log
                print("Error in send text (GPT call): " + str(e))
                self.window.ui.dialogs.alert(str(e))
                self.window.set_status(trans('status.error'))

            ctx = self.window.controller.plugins.apply('ctx.after', ctx)  # apply plugins
            self.window.log("Context: output [after plugin: ctx.after]: {}".format(ctx.dump()))  # log

            self.window.log("Appending output to chat window...")  # log
            self.window.controller.output.append_output(ctx)
            self.window.gpt.context.store()
            self.window.set_status(
                trans('status.tokens') + ": {} + {} = {}".format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))
        except Exception as e:
            self.window.log("Output error: {}".format(e))  # log
            print("Error in send text: " + str(e))
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

        return ctx

    def user_send(self, text=None):
        """Sends real user input"""
        text = self.window.controller.plugins.apply('user.send', text)
        self.send(text)

    def send(self, text=None):
        """
        Sends input text to API
        """
        self.window.statusChanged.emit(trans('status.sending'))

        ctx = None
        if text is None:
            text = self.window.data['input'].toPlainText().strip()

        self.window.log("Input text: {}".format(text))  # log
        text = self.window.controller.plugins.apply('input.before', text)

        self.window.log("Input text [after plugin: input.before]: {}".format(text))  # log

        if len(text) > 0:
            if self.window.config.data['send_clear']:
                self.window.data['input'].clear()

            # check API key
            if self.window.config.data['api_key'] is None or self.window.config.data['api_key'] == '':
                self.window.controller.launcher.show_api_monit()
                self.window.controller.ui.update()
                self.window.statusChanged.emit("")
                return

            # init api key if defined later
            self.window.gpt.init()
            self.window.images.init()

            # prepare context
            if len(self.window.gpt.context.contexts) == 0:
                self.window.gpt.context.new()
                self.window.controller.context.update()
                self.window.log("New context created...")  # log

            # process events to update UI
            QApplication.processEvents()

            # send to API
            if self.window.config.data['mode'] == 'img':
                ctx = self.window.controller.image.send_text(text)
            else:
                ctx = self.window.controller.input.send_text(text)
        else:
            self.window.statusChanged.emit("")

        self.window.log("Context: output: {}".format(ctx.dump()))  # log
        ctx = self.window.controller.plugins.apply('ctx.end', ctx)  # apply plugins
        self.window.log("Context: output [after plugin: ctx.end]: {}".format(ctx.dump()))  # log
        self.window.controller.ui.update()

    def append(self, text):
        """
        Appends text to input

        :param text: text to append
        """
        cur = self.window.data['input'].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.window.data['input'].setTextCursor(cur)  # Update visible cursor
