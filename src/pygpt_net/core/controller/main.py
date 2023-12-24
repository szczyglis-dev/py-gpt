# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

from .assistant import Assistant
from .assistant_files import AssistantFiles
from .assistant_thread import AssistantThread
from .attachment import Attachment
from .audio import Audio
from .camera import Camera
from .command import Command
from .confirm import Confirm
from .ctx import Ctx
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
from .summarize import Summarize
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
        self.assistant_files = AssistantFiles(window)
        self.assistant_thread = AssistantThread(window)
        self.attachment = Attachment(window)
        self.audio = Audio(window)
        self.camera = Camera(window)
        self.command = Command(window)
        self.confirm = Confirm(window)
        self.ctx = Ctx(window)
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
        self.summarize = Summarize(window)
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
        self.ctx.setup()
        self.ui.update_tokens()
        self.info.setup()
        self.audio.setup()
        self.attachment.setup()
        self.notepad.setup()
        self.camera.setup_settings()
        self.image.setup()

    def post_setup(self):
        """Post-setup, after plugins are loaded"""
        # setup plugins settings
        self.plugins.setup_settings()

    def update(self):
        """On app main loop update"""
        self.camera.update()

    def init(self):
        """Init base settings"""
        self.settings.load()
