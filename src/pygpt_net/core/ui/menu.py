#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from ..utils import trans


class Menu:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups all menus"""
        self.window.menu = {}
        self.setup_file()
        self.setup_plugins()
        self.setup_audio()
        self.setup_config()
        self.setup_lang()
        self.setup_theme()
        self.setup_about()

        # debug menu
        if self.window.config.data['debug']:
            self.setup_debug()

    def setup_file(self):
        """Setups file menu"""
        self.window.menu['app.exit'] = QAction(QIcon.fromTheme("application-exit"), trans("menu.file.exit"),
                                               self.window, shortcut="Ctrl+Q", triggered=self.window.close)

        self.window.menu['app.clear_history'] = QAction(trans("menu.file_clear_history"),
                                                        self.window)

        self.window.menu['app.clear_history'].triggered.connect(
            lambda: self.window.controller.context.delete_history())

        self.window.menu['menu.app'] = self.window.menuBar().addMenu(trans("menu.file"))
        self.window.menu['menu.app'].addAction(self.window.menu['app.clear_history'])
        self.window.menu['menu.app'].addAction(self.window.menu['app.exit'])

    def setup_plugins(self):
        """Setups plugins menu"""
        self.window.menu['plugins.settings'] = QAction(trans("menu.plugins.settings"),
                                                       self.window)

        self.window.menu['plugins.settings'].triggered.connect(
            lambda: self.window.controller.plugins.toggle_settings())

        self.window.menu['plugins'] = {}
        self.window.menu['menu.plugins'] = self.window.menuBar().addMenu(trans("menu.plugins"))
        self.window.menu['menu.plugins'].setStyleSheet(self.window.controller.theme.get_style('menu'))  # Windows fix
        self.window.menu['menu.plugins'].addAction(self.window.menu['plugins.settings'])

    def setup_audio(self):
        """Setups audio menu"""
        self.window.menu['audio.empty'] = QAction(QIcon.fromTheme("help-about"), trans("coming_soon"),
                                                  self.window)
        self.window.menu['menu.audio'] = self.window.menuBar().addMenu(trans("menu.audio"))
        self.window.menu['menu.audio'].addAction(self.window.menu['audio.empty'])

    def setup_config(self):
        """Setups config menu"""
        self.window.menu['config.settings'] = QAction(trans("menu.config.settings"),
                                                      self.window)
        self.window.menu['config.edit.config'] = QAction(trans("menu.config.edit.config"),
                                                         self.window)
        self.window.menu['config.edit.models'] = QAction(trans("menu.config.edit.models"),
                                                         self.window)
        self.window.menu['config.open_dir'] = QAction(trans("menu.config.open_dir"),
                                                      self.window)
        self.window.menu['config.save'] = QAction(QIcon.fromTheme("document-save"), trans("menu.config.save"),
                                                  self.window)

        self.window.menu['config.settings'].triggered.connect(
            lambda: self.window.controller.settings.toggle_settings('settings'))

        self.window.menu['config.edit.config'].triggered.connect(
            lambda: self.window.controller.settings.toggle_editor('config.json'))

        self.window.menu['config.edit.models'].triggered.connect(
            lambda: self.window.controller.settings.toggle_editor('models.json'))

        self.window.menu['config.open_dir'].triggered.connect(
            lambda: self.window.controller.settings.open_config_dir())

        self.window.menu['config.save'].triggered.connect(
            lambda: self.window.controller.settings.save_all())

        self.window.menu['menu.config'] = self.window.menuBar().addMenu(trans("menu.config"))
        self.window.menu['menu.config'].addAction(self.window.menu['config.settings'])
        self.window.menu['menu.config'].addAction(self.window.menu['config.edit.config'])
        self.window.menu['menu.config'].addAction(self.window.menu['config.edit.models'])
        self.window.menu['menu.config'].addAction(self.window.menu['config.open_dir'])
        self.window.menu['menu.config'].addAction(self.window.menu['config.save'])

    def setup_debug(self):
        """Setups debug menu"""
        self.window.menu['debug.config'] = QAction(trans("menu.debug.config"), self.window, checkable=True)
        self.window.menu['debug.context'] = QAction(trans("menu.debug.context"), self.window, checkable=True)
        self.window.menu['debug.presets'] = QAction(trans("menu.debug.presets"), self.window, checkable=True)
        self.window.menu['debug.models'] = QAction(trans("menu.debug.models"), self.window, checkable=True)

        self.window.menu['debug.config'].triggered.connect(
            lambda: self.window.controller.debug.toggle('config'))
        self.window.menu['debug.context'].triggered.connect(
            lambda: self.window.controller.debug.toggle('context'))
        self.window.menu['debug.presets'].triggered.connect(
            lambda: self.window.controller.debug.toggle('presets'))
        self.window.menu['debug.models'].triggered.connect(
            lambda: self.window.controller.debug.toggle('models'))

        self.window.menu['menu.debug'] = self.window.menuBar().addMenu(trans("menu.debug"))
        self.window.menu['menu.debug'].addAction(self.window.menu['debug.config'])
        self.window.menu['menu.debug'].addAction(self.window.menu['debug.context'])
        self.window.menu['menu.debug'].addAction(self.window.menu['debug.presets'])
        self.window.menu['menu.debug'].addAction(self.window.menu['debug.models'])

    def setup_lang(self):
        """Setups lang menu"""
        self.window.menu['lang'] = {}
        self.window.menu['menu.lang'] = self.window.menuBar().addMenu(trans("menu.lang"))
        self.window.menu['menu.lang'].setStyleSheet(self.window.controller.theme.get_style('menu'))  # Windows fix

    def setup_theme(self):
        """Setups theme menu"""
        self.window.menu['theme'] = {}
        self.window.menu['menu.theme'] = self.window.menuBar().addMenu(trans("menu.theme"))
        self.window.menu['menu.theme'].setStyleSheet(self.window.controller.theme.get_style('menu'))  # Windows fix

    def setup_about(self):
        """Setups about menu"""
        self.window.menu['info.about'] = QAction(QIcon.fromTheme("help-about"), trans("menu.info.about"),
                                                 self.window)
        self.window.menu['info.changelog'] = QAction(trans("menu.info.changelog"),
                                                     self.window)
        self.window.menu['info.website'] = QAction(trans("menu.info.website"),
                                                   self.window)
        self.window.menu['info.github'] = QAction(trans("menu.info.github"),
                                                  self.window)

        self.window.menu['info.about'].triggered.connect(
            lambda: self.window.controller.info.toggle('about'))
        self.window.menu['info.changelog'].triggered.connect(
            lambda: self.window.controller.info.toggle('changelog'))
        self.window.menu['info.website'].triggered.connect(
            lambda: self.window.controller.info.goto_website())
        self.window.menu['info.github'].triggered.connect(
            lambda: self.window.controller.info.goto_github())

        self.window.menu['menu.about'] = self.window.menuBar().addMenu(trans("menu.info"))
        self.window.menu['menu.about'].addAction(self.window.menu['info.about'])
        self.window.menu['menu.about'].addAction(self.window.menu['info.changelog'])
        self.window.menu['menu.about'].addAction(self.window.menu['info.website'])
        self.window.menu['menu.about'].addAction(self.window.menu['info.github'])
