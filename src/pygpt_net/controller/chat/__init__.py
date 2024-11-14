#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #

from pygpt_net.core.access.events import AppEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .command import Command
from .common import Common
from .files import Files
from .image import Image
from .input import Input
from .output import Output
from .render import Render
from .reply import Reply
from .response import Response
from .stream import Stream
from .text import Text
from .vision import Vision


class Chat:
    def __init__(self, window=None):
        """
        Chat controller

        :param window: Window instance
        """
        self.window = window
        self.command = Command(window)
        self.common = Common(window)
        self.files = Files(window)
        self.image = Image(window)
        self.input = Input(window)
        self.output = Output(window)
        self.render = Render(window)
        self.reply = Reply(window)
        self.response = Response(window)
        self.stream = Stream(window)
        self.text = Text(window)
        self.vision = Vision(window)

    def init(self):
        """Init"""
        self.render.setup()  # setup render engine

    def setup(self):
        """Setup"""
        self.common.setup()

    def reload(self):
        """Reload"""
        self.common.setup()
        self.render.reload()

    def handle_error(self, err: any):
        """
        Handle error

        :param err: Exception
        """
        self.window.core.debug.log(err)
        self.window.ui.dialogs.alert(str(err))
        self.window.ui.status(str(err))
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
