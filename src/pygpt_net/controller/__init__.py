# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

from pygpt_net.controller.assistant import Assistant
from pygpt_net.controller.attachment import Attachment
from pygpt_net.controller.audio import Audio
from pygpt_net.controller.camera import Camera
from pygpt_net.controller.command import Command
from pygpt_net.controller.confirm import Confirm
from pygpt_net.controller.ctx import Ctx
from pygpt_net.controller.debug import Debug
from pygpt_net.controller.files import Files
from pygpt_net.controller.image import Image
from pygpt_net.controller.info import Info
from pygpt_net.controller.input import Input
from pygpt_net.controller.lang import Lang
from pygpt_net.controller.launcher import Launcher
from pygpt_net.controller.layout import Layout
from pygpt_net.controller.mode import Mode
from pygpt_net.controller.model import Model
from pygpt_net.controller.notepad import Notepad
from pygpt_net.controller.output import Output
from pygpt_net.controller.plugins import Plugins
from pygpt_net.controller.presets import Presets
from pygpt_net.controller.settings import Settings
from pygpt_net.controller.summarize import Summarize
from pygpt_net.controller.theme import Theme
from pygpt_net.controller.ui import UI


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
        self.mode = Mode(window)
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
        self.mode.setup()
        self.assistant.setup()
        self.input.setup()
        self.output.setup()
        self.ctx.setup()
        self.ui.update_tokens()
        self.info.setup()
        self.audio.setup()
        self.attachment.setup()
        self.notepad.setup()
        self.camera.setup_ui()
        self.image.setup()

    def post_setup(self):
        """Post-setup, after plugins are loaded"""
        self.plugins.settings.setup()
        self.launcher.post_setup()

    def on_update(self):
        """On app main loop update"""
        self.camera.update()

    def init(self):
        """Init base settings"""
        self.settings.load()
