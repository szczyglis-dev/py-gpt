#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 14:00:00                  #
# ================================================== #
from .debugger import Debug
from .dispatcher import Dispatcher
from .settings import Settings
from .info import Info
from .gpt import Gpt
from .chain import Chain
from .context import Context
from .command import Command
from .image import Image
from .assistants import Assistants
from .attachments import Attachments
from .notepad import Notepad
from .plugins import Plugins
from .history import History


class Container:
    def __init__(self, window=None):
        """
        Container

        :param window: Window instance
        """
        self.window = window

        # setup core
        self.context = Context(self.window)
        self.dispatcher = Dispatcher(self.window)
        self.debug = Debug(self.window)
        self.info = Info(self.window)
        self.settings = Settings(self.window)
        self.command = Command(self.window)
        self.assistants = Assistants(self.window)
        self.attachments = Attachments(self.window)
        self.notepad = Notepad(self.window)
        self.plugins = Plugins(self.window)
        self.history = History(self.window)

        # setup GPT, Langchain, DALL-E, etc.
        self.gpt = Gpt(self.window)
        self.chain = Chain(self.window)
        self.images = Image(self.window)