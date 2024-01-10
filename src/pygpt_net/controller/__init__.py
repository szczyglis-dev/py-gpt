# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

from pygpt_net.controller.assistant import Assistant
from pygpt_net.controller.attachment import Attachment
from pygpt_net.controller.audio import Audio
from pygpt_net.controller.calendar import Calendar
from pygpt_net.controller.camera import Camera
from pygpt_net.controller.chat import Chat
from pygpt_net.controller.command import Command
from pygpt_net.controller.config import Config
from pygpt_net.controller.ctx import Ctx
from pygpt_net.controller.debug import Debug
from pygpt_net.controller.files import Files
from pygpt_net.controller.dialogs import Dialogs
from pygpt_net.controller.lang import Lang
from pygpt_net.controller.launcher import Launcher
from pygpt_net.controller.layout import Layout
from pygpt_net.controller.mode import Mode
from pygpt_net.controller.model import Model
from pygpt_net.controller.notepad import Notepad
from pygpt_net.controller.plugins import Plugins
from pygpt_net.controller.presets import Presets
from pygpt_net.controller.settings import Settings
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
        self.calendar = Calendar(window)
        self.camera = Camera(window)
        self.chat = Chat(window)
        self.command = Command(window)
        self.config = Config(window)
        self.ctx = Ctx(window)
        self.debug = Debug(window)
        self.dialogs = Dialogs(window)
        self.files = Files(window)
        self.lang = Lang(window)
        self.launcher = Launcher(window)
        self.layout = Layout(window)
        self.mode = Mode(window)
        self.model = Model(window)
        self.notepad = Notepad(window)
        self.plugins = Plugins(window)
        self.presets = Presets(window)
        self.settings = Settings(window)
        self.theme = Theme(window)
        self.ui = UI(window)

    def setup(self):
        """Setup controller"""

        # setup layout
        self.layout.setup()
        self.ui.setup()

        # setup controllers
        self.lang.setup()
        self.assistant.setup()
        self.chat.setup()
        self.ctx.setup()
        self.presets.setup()
        self.ui.update_tokens()
        self.dialogs.setup()
        self.audio.setup()
        self.attachment.setup()
        self.notepad.setup()
        self.camera.setup_ui()

    def post_setup(self):
        """Post-setup, after plugins are loaded"""
        self.plugins.settings.setup()
        self.launcher.post_setup()
        self.calendar.setup()  # after everything is loaded

    def on_update(self):
        """On app main loop update"""
        pass

    def init(self):
        """Init base settings"""
        self.settings.load()
