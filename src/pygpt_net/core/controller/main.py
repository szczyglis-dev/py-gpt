# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

from .assistant import Assistant
from .attachment import Attachment
from .audio import Audio
from .camera import Camera
from .confirm import Confirm
from .context import Context
from .debug import Debug
from .files import Files
from .image import Image
from .info import Info
from .input import Input
from .lang import Lang
from .launcher import Launcher
from .layout import Layout
from .model import Model
from .notepad import Notepad
from .output import Output
from .plugins import Plugins
from .presets import Presets
from .settings import Settings
from .theme import Theme
from .ui import UI


class Controller:
    def __init__(self, window=None):
        """
        Main controller

        :param window: Window instance
        """
        self.window = window
        self.assistant = Assistant(window)
        self.attachment = Attachment(window)
        self.audio = Audio(window)
        self.camera = Camera(window)
        self.confirm = Confirm(window)
        self.context = Context(window)
        self.debug = Debug(window)
        self.files = Files(window)
        self.image = Image(window)
        self.info = Info(window)
        self.input = Input(window)
        self.lang = Lang(window)
        self.launcher = Launcher(window)
        self.layout = Layout(window)
        self.model = Model(window)
        self.notepad = Notepad(window)
        self.output = Output(window)
        self.plugins = Plugins(window)
        self.presets = Presets(window)
        self.settings = Settings(window)
        self.theme = Theme(window)
        self.ui = UI(window)

    def setup(self):
        """Setup controller"""
        # init
        self.launcher.setup()

        # setup layout
        self.layout.setup()
        self.ui.setup()

        # setup controllers
        self.lang.setup()
        self.model.setup()
        self.assistant.setup()
        self.input.setup()
        self.output.setup()
        self.context.setup()
        self.ui.update_tokens()
        self.info.setup()
        self.audio.setup()
        self.attachment.setup()
        self.notepad.setup()
        self.camera.setup_settings()
        self.image.setup()

    def setup_plugins(self):
        """Setup plugins"""
        # setup plugins settings
        self.plugins.setup_settings()

    def update(self):
        """On app main loop update"""
        self.camera.update()
