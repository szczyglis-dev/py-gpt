# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.16 06:00:00                  #
# ================================================== #

from .model import Model
from .presets import Presets
from .plugins import Plugins
from .debug import Debug
from .settings import Settings
from .info import Info
from .input import Input
from .output import Output
from .context import Context
from .confirm import Confirm
from .ui import UI
from .launcher import Launcher
from .lang import Lang
from .image import Image
from .theme import Theme
from .audio import Audio
from .attachment import Attachment
from .notepad import Notepad
from .files import Files
from .assistant import Assistant


class Controller:
    def __init__(self, window=None):
        """
        Main controller

        :param window: main window object
        """
        self.window = window
        self.model = Model(window)
        self.presets = Presets(window)
        self.plugins = Plugins(window)
        self.debug = Debug(window)
        self.settings = Settings(window)
        self.info = Info(window)
        self.input = Input(window)
        self.output = Output(window)
        self.context = Context(window)
        self.confirm = Confirm(window)
        self.ui = UI(window)
        self.launcher = Launcher(window)
        self.lang = Lang(window)
        self.image = Image(window)
        self.theme = Theme(window)
        self.audio = Audio(window)
        self.attachment = Attachment(window)
        self.notepad = Notepad(window)
        self.files = Files(window)
        self.assistant = Assistant(window)

    def setup(self):
        """Setups controller"""
        # init material theme
        self.theme.setup()

        # setup all controllers
        self.lang.setup()
        self.model.setup()
        self.assistant.setup()
        self.input.setup()
        self.output.setup()
        self.context.setup()
        self.ui.setup()
        self.info.setup()
        self.launcher.setup()
        self.audio.setup()
        self.attachment.setup()
        self.notepad.setup()

    def setup_plugins(self):
        """Setup plugins"""
        # setup plugins settings
        self.plugins.setup_settings()
