#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

from .about import About
from .audio import Audio
from .config import Config
from .debug import Debug
from .file import File
from .lang import Lang
from .plugins import Plugins
from .theme import Theme
from .tools import Tools
from .video import Video


class Menu:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window
        self.about = About(window)
        self.audio = Audio(window)
        self.config = Config(window)
        self.debug = Debug(window)
        self.file = File(window)
        self.lang = Lang(window)
        self.plugins = Plugins(window)
        self.theme = Theme(window)
        self.tools = Tools(window)
        self.video = Video(window)

    def setup(self):
        """Setup all menus"""
        self.window.ui.menu = {}
        self.file.setup()
        self.plugins.setup()
        self.audio.setup()
        self.video.setup()
        self.config.setup()
        self.about.setup()

    def post_setup(self):
        """Post setup menus"""
        # tools menu
        self.tools.setup()

        # debug menu
        show = self.window.core.config.get('debug')
        self.debug.setup()
        self.window.ui.menu['menu.debug'].menuAction().setVisible(show)
