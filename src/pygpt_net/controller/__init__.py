# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.07 23:00:00                  #
# ================================================== #

from pygpt_net.controller.access import Access
from pygpt_net.controller.agent import Agent
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
from pygpt_net.controller.dialogs import Dialogs
from pygpt_net.controller.files import Files
from pygpt_net.controller.finder import Finder
from pygpt_net.controller.idx import Idx
from pygpt_net.controller.lang import Lang
from pygpt_net.controller.launcher import Launcher
from pygpt_net.controller.layout import Layout
from pygpt_net.controller.mode import Mode
from pygpt_net.controller.model import Model
from pygpt_net.controller.notepad import Notepad
from pygpt_net.controller.painter import Painter
from pygpt_net.controller.plugins import Plugins
from pygpt_net.controller.presets import Presets
from pygpt_net.controller.settings import Settings
from pygpt_net.controller.theme import Theme
from pygpt_net.controller.tools import Tools
from pygpt_net.controller.ui import UI

class Controller:
    def __init__(self, window=None):
        """
        Main controller

        :param window: Window instance
        """
        self.window = window
        self.access = Access(window)
        self.agent = Agent(window)
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
        self.finder = Finder(window)
        self.idx = Idx(window)
        self.lang = Lang(window)
        self.launcher = Launcher(window)
        self.layout = Layout(window)
        self.mode = Mode(window)
        self.model = Model(window)
        self.notepad = Notepad(window)
        self.painter = Painter(window)
        self.plugins = Plugins(window)
        self.presets = Presets(window)
        self.settings = Settings(window)
        self.theme = Theme(window)
        self.tools = Tools(window)
        self.ui = UI(window)
        self.reloading = False

    def setup(self):
        """Setup controller"""
        self.debug.setup()  # prepare log level
        self.chat.init()

        # setup layout
        self.ui.pre_setup()
        self.layout.setup()
        self.ui.setup()

        # setup controllers
        self.lang.setup()
        self.assistant.setup()
        self.chat.setup()
        self.agent.setup()
        self.ctx.setup()
        self.presets.setup()
        self.idx.setup()
        self.ui.update_tokens()
        self.dialogs.setup()
        self.audio.setup()
        self.attachment.setup()
        self.camera.setup_ui()
        self.access.setup()
        self.tools.setup()

    def post_setup(self):
        """Post-setup, after plugins are loaded"""
        self.settings.setup()
        self.plugins.settings.setup()
        self.model.editor.setup()
        self.launcher.post_setup()
        self.calendar.setup()  # after everything is loaded
        self.painter.setup()  # load previous image if exists
        self.debug.post_setup()  # post setup debug after all loaded

        # show license terms dialog
        if not self.window.core.config.get('license.accepted'):
            self.dialogs.info.toggle(
                'license',
                width=500,
                height=480,
            )
            self.window.ui.dialog['info.license'].setFocus()

    def after_setup(self):
        """After-setup, after all loaded"""
        self.plugins.update()

    def on_update(self):
        """On app main loop update"""
        pass

    def init(self):
        """Init base settings"""
        self.settings.load()

    def reload(self):
        """Reload components"""
        self.reloading = True
        self.window.core.reload()  # db, config, patch, etc.
        self.ui.tabs.reload()
        self.ctx.reload()
        self.settings.reload()
        self.assistant.reload()
        self.attachment.reload()
        self.presets.reload()
        self.idx.reload()
        self.agent.reload()
        self.calendar.reload()
        self.plugins.reload()
        self.painter.reload()
        self.notepad.reload()
        self.files.reload()
        self.lang.reload()
        self.theme.reload_all()
        self.debug.reload()
        self.chat.reload()
        self.window.tools.on_reload()
        self.access.reload()
        self.tools.reload()
        # self.layout.reload()

        # post-reload
        self.ui.tabs.reload_after()
        self.ctx.reload_after()

        self.reloading = False
