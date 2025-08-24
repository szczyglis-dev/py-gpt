#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QActionGroup

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
        self._lang_group = None

    def _on_lang_triggered(self, action):
        """
        Handle language change triggered by menu action

        :param action: QAction instance
        """
        self.window.controller.lang.toggle(action.data())

    def setup(self):
        """Setup language menu"""
        if not self.loaded:
            w = self.window
            menu = w.ui.menu
            if self._lang_group is None:
                self._lang_group = QActionGroup(w)
                self._lang_group.setExclusive(True)
                self._lang_group.triggered.connect(self._on_lang_triggered)

            langs = w.core.config.get_available_langs()
            menu_lang = menu['lang']
            menu_root = menu['menu.lang']
            for lang in langs:
                act = QAction(lang.upper(), w, checkable=True)
                act.setData(lang)
                menu_lang[lang] = act
                self._lang_group.addAction(act)
                menu_root.addAction(act)
        self.loaded = True
        self.update()

    def update(self):
        """Update language menu"""
        menu_lang = self.window.ui.menu['lang']
        current = self.window.core.config.get('lang')
        act = menu_lang.get(current)
        if act is not None:
            act.setChecked(True)
        else:
            for a in menu_lang.values():
                a.setChecked(False)

    def reload_config(self):
        """Reload language config"""
        trans_reload()

    def toggle(self, id: str):
        """
        Toggle language

        :param id: language code to toggle
        """
        w = self.window
        c = w.controller
        conf = w.core.config

        conf.set('lang', id)
        conf.save()
        trans('', True)

        self.update()
        self.mapping.apply()
        self.custom.apply()

        c.ui.tabs.reload_titles()
        c.calendar.note.update_current()
        self.settings.apply()

        try:
            self.plugins.apply()
        except Exception as e:
            print("Error updating plugin locale", e)
            w.core.debug.log(e)

        w.controller.ctx.common.update_label_by_current()
        w.controller.ctx.update(True, False)
        w.controller.ui.update()
        w.update_status('')

    def reload(self):
        """Reload language"""
        self.reload_config()
        self.setup()