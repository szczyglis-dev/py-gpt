#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 00:00:00                  #
# ================================================== #

from typing import Any

from pygpt_net.core.events import AppEvent
from pygpt_net.item.ctx import CtxItem

from .attachment import Attachment
from .audio import Audio
from .command import Command
from .common import Common
from .files import Files
from .image import Image
from .input import Input
from .output import Output
from .render import Render
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
        self.attachment = Attachment(window)
        self.audio = Audio(window)
        self.command = Command(window)
        self.common = Common(window)
        self.files = Files(window)
        self.image = Image(window)
        self.input = Input(window)
        self.output = Output(window)
        self.render = Render(window)
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
        self.attachment.setup()

    def reload(self):
        """Reload"""
        self.common.setup()
        self.render.reload()
        self.attachment.reload()

    def handle_error(self, err: Any):
        """
        Handle error

        :param err: Exception
        """
        self.window.core.debug.log(err)
        self.window.ui.dialogs.alert(str(err))
        self.window.update_status(str(err))
        self.window.controller.chat.common.unlock_input()  # always unlock input on error
        self.window.stateChanged.emit(self.window.STATE_ERROR)
        self.window.dispatch(AppEvent(AppEvent.INPUT_ERROR))  # app event

        # stop agent on error
        if self.window.controller.agent.legacy.enabled():
            self.window.controller.agent.legacy.on_stop()

    def log_ctx(self, ctx: CtxItem, mode: str):
        """
        Log context item

        :param ctx: CtxItem
        :param mode: mode (input/output)
        """
        if self.window.core.config.get("log.ctx"):
            self.log("[ctx] {}: {}".format(mode.upper(), ctx.dump()))  # log
        else:
            self.log("[ctx] {}.".format(mode.upper()))

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info("[chat] " + str(data))
