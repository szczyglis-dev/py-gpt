#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 19:00:00                  #
# ================================================== #

from .assistants import Assistants
from .attachments import Attachments
from .chain import Chain
from .command import Command
from .ctx import Ctx
from .debugger import Debug
from .dispatcher import Dispatcher
from .error_handler import ErrorHandler
from .gpt import Gpt
from .gpt_assistants import GptAssistants
from .history import History
from .image import Image
from .info import Info
from .notepad import Notepad
from .plugins import Plugins
from .settings import Settings


class Container:
    def __init__(self, window=None):
        """
        Container

        :param window: Window instance
        """
        self.window = window

        # core components
        self.assistants = Assistants(window)
        self.attachments = Attachments(window)
        self.chain = Chain(window)
        self.command = Command(window)
        self.ctx = Ctx(window)
        self.debug = Debug(window)
        self.dispatcher = Dispatcher(window)
        self.error = ErrorHandler(window)
        self.gpt = Gpt(window)
        self.gpt_assistants = GptAssistants(window)
        self.history = History(window)
        self.images = Image(window)
        self.info = Info(window)
        self.notepad = Notepad(window)
        self.plugins = Plugins(window)
        self.settings = Settings(window)
