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

from pygpt_net.core.controller.assistant import Assistant
from pygpt_net.core.controller.assistant_files import AssistantFiles
from pygpt_net.core.controller.assistant_thread import AssistantThread
from pygpt_net.core.controller.attachment import Attachment
from pygpt_net.core.controller.audio import Audio
from pygpt_net.core.controller.camera import Camera
from pygpt_net.core.controller.command import Command
from pygpt_net.core.controller.confirm import Confirm
from pygpt_net.core.controller.ctx import Ctx
from pygpt_net.core.controller.debug import Debug
from pygpt_net.core.controller.files import Files
from pygpt_net.core.controller.image import Image
from pygpt_net.core.controller.info import Info
from pygpt_net.core.controller.input import Input
from pygpt_net.core.controller.lang import Lang
from pygpt_net.core.controller.launcher import Launcher
from pygpt_net.core.controller.layout import Layout
from pygpt_net.core.controller.model import Model
from pygpt_net.core.controller.notepad import Notepad
from pygpt_net.core.controller.output import Output
from pygpt_net.core.controller.plugins import Plugins
from pygpt_net.core.controller.presets import Presets
from pygpt_net.core.controller.settings import Settings
from pygpt_net.core.controller.summarize import Summarize
from pygpt_net.core.controller.theme import Theme
from pygpt_net.core.controller.ui import UI


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
        self.launcher.post_setup()

    def update(self):
        """On app main loop update"""
        self.camera.update()

    def init(self):
        """Init base settings"""
        self.settings.load()
