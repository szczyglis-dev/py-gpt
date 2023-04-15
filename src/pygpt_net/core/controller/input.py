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
        self.window.set_status(trans('status.sending'))

        # create ctx item
        ctx = ContextItem()
        user_name = self.window.config.data['user_name']
        user_name = self.window.controller.plugins.apply('user.name', user_name)  # apply plugins
        ctx.set_input(text, user_name)
        ctx = self.window.controller.plugins.apply('ctx.before', ctx)  # apply plugins
        self.window.controller.output.append_input(ctx)

        # call GPT
        try:
            ctx = self.window.gpt.call(text, ctx)
            ctx = self.window.controller.plugins.apply('ctx.after', ctx)  # apply plugins
            self.window.controller.output.append_output(ctx)
            self.window.gpt.context.store()
            self.window.set_status(
                trans('status.tokens') + ": {} + {} = {}".format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

    def send(self):
        """
        Sends input text to API
        """
        text = self.window.data['input'].toPlainText().strip()
        text = self.window.controller.plugins.apply('input.before', text)

        if len(text) > 0:
            if self.window.config.data['send_clear']:
                self.window.data['input'].clear()

            # check API key
            if self.window.config.data['api_key'] is None or self.window.config.data['api_key'] == '':
                self.window.controller.launcher.show_api_monit()
                self.window.controller.ui.update()
                return

            # init api key if defined later
            self.window.gpt.init()
            self.window.images.init()

            # append initial config values
            self.window.gpt.ai_name = self.window.config.data['ai_name']
            self.window.gpt.user_name = self.window.config.data['user_name']
            self.window.gpt.system_prompt = self.window.config.data['prompt']

            # apply plugins
            self.window.gpt.ai_name = self.window.controller.plugins.apply('ai.name', self.window.gpt.ai_name)
            self.window.gpt.user_name = self.window.controller.plugins.apply('user.name', self.window.gpt.user_name)
            self.window.gpt.system_prompt = self.window.controller.plugins.apply('system.prompt', self.window.gpt.system_prompt)

            # prepare context
            if len(self.window.gpt.context.contexts) == 0:
                self.window.gpt.context.new()
                self.window.controller.context.update()

            # send to API
            if self.window.config.data['mode'] == 'img':
                self.window.controller.image.send_text(text)
            else:
                self.window.controller.input.send_text(text)

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
