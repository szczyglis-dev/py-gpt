#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
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
        w = window
        self.attachment = Attachment(w)
        self.audio = Audio(w)
        self.command = Command(w)
        self.common = Common(w)
        self.files = Files(w)
        self.image = Image(w)
        self.input = Input(w)
        self.output = Output(w)
        self.render = Render(w)
        self.response = Response(w)
        self.stream = Stream(w)
        self.text = Text(w)
        self.vision = Vision(w)

    def init(self) -> None:
        """Init"""
        self.render.setup()  # setup render engine

    def setup(self) -> None:
        """Setup"""
        self.common.setup()
        self.attachment.setup()

    def reload(self) -> None:
        """Reload"""
        self.common.setup()
        self.render.reload()
        self.attachment.reload()

    def handle_error(self, err: Any) -> None:
        """
        Handle error

        :param err: Exception
        """
        w = self.window
        err_str = str(err)
        w.core.debug.log(err)
        w.ui.dialogs.alert(err_str)
        w.update_status(err_str)
        self.common.unlock_input()  # always unlock input on error
        w.stateChanged.emit(w.STATE_ERROR)
        w.dispatch(AppEvent(AppEvent.INPUT_ERROR))  # app event

        if w.controller.agent.legacy.enabled():
            w.controller.agent.legacy.on_stop()

    def log_ctx(self, ctx: CtxItem, mode: str) -> None:
        """
        Log context item

        :param ctx: CtxItem
        :param mode: mode (input/output)
        """
        upper_mode = mode.upper()
        if self.window.core.config.get("log.ctx"):
            self.log(f"[ctx] {upper_mode}: {ctx.dump()}")
        else:
            self.log(f"[ctx] {upper_mode}.")

    def log(self, data: Any) -> None:
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(f"[chat] {data}")