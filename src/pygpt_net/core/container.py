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
from .camera import Camera
from .chain import Chain
from .command import Command
from .config import Config
from .ctx import Ctx
from .debugger import Debug
from .dispatcher import Dispatcher
from .error_handler import ErrorHandler
from .filesystem import Filesystem
from .gpt import Gpt
from .gpt_assistants import GptAssistants
from .history import History
from .image import Image
from .info import Info
from .installer import Installer
from .models import Models
from .modes import Modes
from .notepad import Notepad
from .platform import Platform
from .plugins import Plugins
from .presets import Presets
from .settings import Settings
from .updater import Updater


class Container:
    def __init__(self, window=None):
        """
        Service container

        :param window: Window instance
        """
        self.window = window

        # core services
        self.assistants = Assistants(window)
        self.attachments = Attachments(window)
        self.camera = Camera(window)
        self.chain = Chain(window)
        self.command = Command(window)
        self.config = Config(window)
        self.ctx = Ctx(window)
        self.debug = Debug(window)
        self.dispatcher = Dispatcher(window)
        self.errors = ErrorHandler(window)
        self.filesystem = Filesystem(window)
        self.gpt = Gpt(window)
        self.gpt_assistants = GptAssistants(window)
        self.history = History(window)
        self.image = Image(window)
        self.info = Info(window)
        self.installer = Installer(window)
        self.models = Models(window)
        self.modes = Modes(window)
        self.notepad = Notepad(window)
        self.platform = Platform(window)
        self.plugins = Plugins(window)
        self.presets = Presets(window)
        self.settings = Settings(window)
        self.updater = Updater(window)

    def init(self):
        """Initialize all components"""
        self.platform.init()
        self.config.init(all=True)


    def patch(self):
        """Patch version"""
        self.updater.patch()
