#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 21:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from pygpt_net.utils import trans, trans_reload
from .custom import Custom
from .mapping import Mapping
from .plugins import Plugins
from .settings import Settings


class Lang:
    def __init__(self, window=None):
        """
        Language switch controller

        :param window: Window instance
        """
        self.window = window
        self.custom = Custom(window)
        self.mapping = Mapping(window)
        self.plugins = Plugins(window)
        self.settings = Settings(window)
        self.loaded = False

    def setup(self):
        """Setup language menu"""
        # get files from locale directory
        if not self.loaded:
            langs = self.window.core.config.get_available_langs()
            for lang in langs:
                self.window.ui.menu['lang'][lang] = QAction(lang.upper(), self.window, checkable=True)
                self.window.ui.menu['lang'][lang].triggered.connect(
                    lambda checked=None,
                           lang=lang: self.window.controller.lang.toggle(lang))
                self.window.ui.menu['menu.lang'].addAction(self.window.ui.menu['lang'][lang])
        self.loaded = True
        self.update()

    def update(self):
        """Update language menu"""
        for lang in self.window.ui.menu['lang']:
            self.window.ui.menu['lang'][lang].setChecked(False)
        lang = self.window.core.config.get('lang')
        if lang in self.window.ui.menu['lang']:
            self.window.ui.menu['lang'][lang].setChecked(True)

    def reload_config(self):
        """Reload language config"""
        trans_reload()

    def toggle(self, id: str):
        """
        Toggle language

        :param id: language code to toggle
        """
        self.window.core.config.set('lang', id)
        self.window.core.config.save()
        trans('', True)  # force reload locale

        self.update()  # update menu
        self.mapping.apply()  # nodes mapping
        self.custom.apply()  # custom nodes

        # tabs
        self.window.controller.ui.tabs.reload_titles()

        # calendar
        self.window.controller.calendar.note.update_current()

        # settings
        self.settings.apply()

        # plugins
        try:
            self.plugins.apply()
        except Exception as e:
            print("Error updating plugin locale", e)
            self.window.core.debug.log(e)

        # reload UI
        self.window.controller.ctx.common.update_label_by_current()
        self.window.controller.ctx.update(True, False)
        self.window.controller.ui.update()  # update all (toolbox, etc.)
        self.window.update_status('')  # clear status

    def reload(self):
        """Reload language"""
        self.reload_config()
        self.setup()
