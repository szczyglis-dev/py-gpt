#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

from .config import Config
from .core.access import Access
from .core.agents import Agents
from .core.assistants import Assistants
from .core.attachments import Attachments
from .core.audio import Audio
from .core.bridge import Bridge
from .core.calendar import Calendar
from .core.camera import Camera
# from .core.chain import Chain
from .core.command import Command
from .core.ctx import Ctx
from .core.db import Database
from .core.debug import Debug
from .core.dispatcher import Dispatcher
from .core.experts import Experts
from .core.idx import Idx
from .core.installer import Installer
from .core.filesystem import Filesystem
from .core.history import History
from .core.image import Image
from .core.llm import LLM
from .core.models import Models
from .core.modes import Modes
from .core.notepad import Notepad
from .core.platforms import Platforms
from .core.plugins import Plugins
from .core.presets import Presets
from .core.prompt import Prompt
from .core.remote_store import RemoteStore
from .core.settings import Settings
from .core.tabs import Tabs
from .core.text import Text
from .core.tokens import Tokens
from .core.updater import Updater
from .core.video import Video
from .core.vision import Vision
from .core.web import Web

from .provider.api import Api

class Core:
    def __init__(self, window=None):
        """
        App core

        :param window: Window instance
        """
        self.window = window

        self.access = Access(window)
        self.agents = Agents(window)
        self.api = Api(window)
        self.assistants = Assistants(window)
        self.attachments = Attachments(window)
        self.audio = Audio(window)
        self.bridge = Bridge(window)
        self.calendar = Calendar(window)
        self.camera = Camera(window)
        # self.chain = Chain(window)  # deprecated from v2.5.20
        self.command = Command(window)
        self.config = Config(window)
        self.ctx = Ctx(window)
        self.db = Database(window)
        self.debug = Debug(window)
        self.dispatcher = Dispatcher(window)
        self.experts = Experts(window)
        self.filesystem = Filesystem(window)
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
        self.remote_store = RemoteStore(window)
        self.settings = Settings(window)
        self.tabs = Tabs(window)
        self.text = Text(window)
        self.tokens = Tokens(window)
        self.updater = Updater(window)
        self.video = Video(window)
        self.vision = Vision(window)
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
        self.prompt.custom.reload()
