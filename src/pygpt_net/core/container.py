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

from .assistants import Assistants
from .attachments import Attachments
from .chain import Chain
from .command import Command
from .context import Context
from .debugger import Debug
from .dispatcher import Dispatcher
from .gpt import Gpt
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
        self.context = Context(window)
        self.debug = Debug(window)
        self.dispatcher = Dispatcher(window)
        self.gpt = Gpt(window)
        self.history = History(window)
        self.images = Image(window)
        self.info = Info(window)
        self.notepad = Notepad(window)
        self.plugins = Plugins(window)
        self.settings = Settings(window)
