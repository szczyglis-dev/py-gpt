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
        self.stop = False
        self.generating = False

    def send_input(self):
        """
        Send text from user input (called from UI)
        """
        # get text from input
        text = self.window.ui.nodes['input'].toPlainText().strip()

        if self.generating \
                and text is not None \
                and text.strip() == "stop":
            self.window.controller.chat.common.stop()  # TODO: to chat main
            self.window.controller.chat.render.clear_input()
            return

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
        self.execute(text, force)

    def execute(self, text=None, force=False):
        """
        Execute send input text to API

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
                self.generating = False  # unlock
                return
        elif mode == 'vision':
            # capture frame from camera if auto-capture enabled
            if self.window.controller.camera.is_enabled():
                if self.window.controller.camera.is_auto():
                    self.window.controller.camera.capture_frame(False)

        # unlock Assistant run thread if locked
        self.window.controller.assistant.threads.stop = False
        self.stop = False

        self.log("Input text: {}".format(text))  # log

        # event: input.before
        event = Event('input.before', {
            'value': text,
        })
        self.window.core.dispatcher.dispatch(event)
        text = event.data['value']

        self.log("Input text [after plugin: input.before]: {}".format(text))  # log

        # check if image captured from camera
        camera_captured = (mode == 'vision' and self.window.controller.attachment.has('vision'))

        # allow empty input only for vision mode, otherwise abort
        if len(text.strip()) == 0 and not camera_captured:
            self.generating = False  # unlock as not generating
            return

        # check API key, show monit if not set
        if mode != 'langchain':
            if not self.window.controller.chat.common.check_api_key():
                self.generating = False
                return

        self.window.set_status(trans('status.sending'))

        # clear input field if clear-on-send is enabled
        if self.window.core.config.get('send_clear') and not force:
            self.window.controller.chat.render.clear_input()

        # prepare ctx, create new ctx meta if there is no ctx yet (first run)
        if self.window.core.ctx.count_meta() == 0:
            self.window.core.ctx.new()
            self.window.controller.ctx.update()
            self.log("New context created...")  # log
        else:
            # check if current ctx is allowed for this mode - if not, then create new ctx
            self.window.controller.ctx.handle_allowed(mode)

        # update UI
        QApplication.processEvents()

        # send input to API, return ctx
        if self.window.core.config.get('mode') == 'img':
            ctx = self.window.controller.chat.image.send(text)  # image mode: DALL-E
        else:
            ctx = self.window.controller.chat.text.send(text)  # text mode: OpenAI or LangChain

        # clear attachments after send if enabled
        if self.window.core.config.get('attachments_send_clear'):
            self.window.controller.attachment.clear(True)
            self.window.controller.attachment.update()

        self.log("Context: output: {}".format(self.window.core.ctx.dump(ctx)))  # log

        # event: ctx.end
        event = Event('ctx.end')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        self.log("Context: output [after plugin: ctx.end]: {}".
                 format(self.window.core.ctx.dump(ctx)))  # log
        self.window.controller.ui.update_tokens()  # update UI
        self.generating = False  # unlock

    def log(self, data):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.controller.debug.log(data, True)
