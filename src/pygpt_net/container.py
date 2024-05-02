#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

from pygpt_net.config import Config
from pygpt_net.core.access import Access
from pygpt_net.core.agents import Agents
from pygpt_net.core.assistants import Assistants
from pygpt_net.core.attachments import Attachments
from pygpt_net.core.audio import Audio
from pygpt_net.core.bridge import Bridge
from pygpt_net.core.calendar import Calendar
from pygpt_net.core.camera import Camera
from pygpt_net.core.chain import Chain
from pygpt_net.core.command import Command
from pygpt_net.core.ctx import Ctx
from pygpt_net.core.db import Database
from pygpt_net.core.debug import Debug
from pygpt_net.core.dispatcher import Dispatcher
from pygpt_net.core.experts import Experts
from pygpt_net.core.idx import Idx
from pygpt_net.core.installer import Installer
from pygpt_net.core.filesystem import Filesystem
from pygpt_net.core.history import History
from pygpt_net.core.image import Image
from pygpt_net.core.llm import LLM
from pygpt_net.core.models import Models
from pygpt_net.core.modes import Modes
from pygpt_net.core.notepad import Notepad
from pygpt_net.core.platforms import Platforms
from pygpt_net.core.plugins import Plugins
from pygpt_net.core.presets import Presets
from pygpt_net.core.prompt import Prompt
from pygpt_net.core.settings import Settings
from pygpt_net.core.tokens import Tokens
from pygpt_net.core.updater import Updater
from pygpt_net.core.web import Web
from pygpt_net.provider.gpt import Gpt


class Container:
    def __init__(self, window=None):
        """
        Service container

        :param window: Window instance
        """
        self.window = window

        # core
        self.access = Access(window)
        self.agents = Agents(window)
        self.assistants = Assistants(window)
        self.attachments = Attachments(window)
        self.audio = Audio(window)
        self.bridge = Bridge(window)
        self.calendar = Calendar(window)
        self.camera = Camera(window)
        self.chain = Chain(window)
        self.command = Command(window)
        self.config = Config(window)
        self.ctx = Ctx(window)
        self.db = Database(window)
        self.debug = Debug(window)
        self.dispatcher = Dispatcher(window)
        self.experts = Experts(window)
        self.filesystem = Filesystem(window)
        self.gpt = Gpt(window)
        self.history = History(window)
        self.idx = Idx(window)
        self.image = Image(window)
        self.llm = LLM(window)
        self.installer = Installer(window)
        self.models = Models(window)
        self.modes = Modes(window)
        self.notepad = Notepad(window)
        self.platforms = Platforms(window)
        self.plugins = Plugins(window)
        self.presets = Presets(window)
        self.prompt = Prompt(window)
        self.settings = Settings(window)
        self.tokens = Tokens(window)
        self.updater = Updater(window)
        self.web = Web(window)

    def init(self):
        """Initialize all components"""
        self.config.init(all=True)
        self.platforms.init()

    def patch(self):
        """Patch version"""
        self.updater.patch()

    def post_setup(self):
        """Post setup"""
        self.config.setup_env()

    def reload(self):
        """Reload core"""
        self.db.reload()
        self.patch()
        self.debug.update_logger_path()
        self.config.setup_env()
