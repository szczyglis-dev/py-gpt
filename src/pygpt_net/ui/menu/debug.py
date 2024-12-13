#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.13 19:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction

from pygpt_net.utils import trans


class Debug:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup debug menu"""
        self.window.ui.menu['debug.config'] = QAction(trans("menu.debug.config"), self.window, checkable=True)
        self.window.ui.menu['debug.context'] = QAction(trans("menu.debug.context"), self.window, checkable=True)
        self.window.ui.menu['debug.presets'] = QAction(trans("menu.debug.presets"), self.window, checkable=True)
        self.window.ui.menu['debug.models'] = QAction(trans("menu.debug.models"), self.window, checkable=True)
        self.window.ui.menu['debug.plugins'] = QAction(trans("menu.debug.plugins"), self.window, checkable=True)
        self.window.ui.menu['debug.attachments'] = QAction(trans("menu.debug.attachments"), self.window, checkable=True)
        self.window.ui.menu['debug.assistants'] = QAction(trans("menu.debug.assistants"), self.window, checkable=True)
        self.window.ui.menu['debug.agent'] = QAction(trans("menu.debug.agent"), self.window, checkable=True)
        self.window.ui.menu['debug.events'] = QAction(trans("menu.debug.events"), self.window, checkable=True)
        self.window.ui.menu['debug.indexes'] = QAction(trans("menu.debug.indexes"), self.window, checkable=True)
        self.window.ui.menu['debug.ui'] = QAction(trans("menu.debug.ui"), self.window, checkable=True)
        self.window.ui.menu['debug.tabs'] = QAction(trans("menu.debug.tabs"), self.window, checkable=True)
        self.window.ui.menu['debug.db'] = QAction(trans("menu.debug.db"), self.window, checkable=True)
        self.window.ui.menu['debug.logger'] = QAction(trans("menu.debug.logger"), self.window, checkable=True)
        self.window.ui.menu['debug.app.log'] = QAction(trans("menu.debug.app.log"), self.window, checkable=True)
        self.window.ui.menu['debug.kernel'] = QAction(trans("menu.debug.kernel"), self.window, checkable=True)
        self.window.ui.menu['debug.render'] = QAction(trans("menu.debug.render"), self.window, checkable=True)

        self.window.ui.menu['debug.config'].triggered.connect(
            lambda: self.window.controller.debug.toggle('config'))
        self.window.ui.menu['debug.context'].triggered.connect(
            lambda: self.window.controller.debug.toggle('context'))
        self.window.ui.menu['debug.presets'].triggered.connect(
            lambda: self.window.controller.debug.toggle('presets'))
        self.window.ui.menu['debug.models'].triggered.connect(
            lambda: self.window.controller.debug.toggle('models'))
        self.window.ui.menu['debug.plugins'].triggered.connect(
            lambda: self.window.controller.debug.toggle('plugins'))
        self.window.ui.menu['debug.attachments'].triggered.connect(
            lambda: self.window.controller.debug.toggle('attachments'))
        self.window.ui.menu['debug.assistants'].triggered.connect(
            lambda: self.window.controller.debug.toggle('assistants'))
        self.window.ui.menu['debug.agent'].triggered.connect(
            lambda: self.window.controller.debug.toggle('agent'))
        self.window.ui.menu['debug.events'].triggered.connect(
            lambda: self.window.controller.debug.toggle('events'))
        self.window.ui.menu['debug.indexes'].triggered.connect(
            lambda: self.window.controller.debug.toggle('indexes'))
        self.window.ui.menu['debug.logger'].triggered.connect(
            lambda: self.window.controller.debug.toggle_logger())
        self.window.ui.menu['debug.ui'].triggered.connect(
            lambda: self.window.controller.debug.toggle('ui'))
        self.window.ui.menu['debug.tabs'].triggered.connect(
            lambda: self.window.controller.debug.toggle('tabs'))
        self.window.ui.menu['debug.app.log'].triggered.connect(
            lambda: self.window.controller.debug.toggle_app_log())
        self.window.ui.menu['debug.db'].triggered.connect(
            lambda: self.window.controller.debug.toggle('db'))
        self.window.ui.menu['debug.kernel'].triggered.connect(
            lambda: self.window.controller.debug.toggle('kernel'))
        self.window.ui.menu['debug.render'].triggered.connect(
            lambda: self.window.controller.debug.toggle_render())

        self.window.ui.menu['menu.debug'] = self.window.menuBar().addMenu(trans("menu.debug"))
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.logger'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.render'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.db'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.app.log'])
        self.window.ui.menu['menu.debug'].addSeparator()
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.agent'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.assistants'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.attachments'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.config'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.context'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.events'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.indexes'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.kernel'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.models'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.plugins'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.presets'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.tabs'])
        self.window.ui.menu['menu.debug'].addAction(self.window.ui.menu['debug.ui'])

        # restore state
        if self.window.core.config.get('debug.render'):
            self.window.ui.menu['debug.render'].setChecked(True)
        else:
            self.window.ui.menu['debug.render'].setChecked(False)


