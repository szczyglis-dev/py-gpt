#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 03:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.utils import trans


class Config:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup config menu"""
        self.window.ui.menu['config.settings'] = QAction(QIcon.fromTheme("preferences-other"),
                                                         trans("menu.config.settings"), self.window)
        self.window.ui.menu['config.models'] = QAction(QIcon.fromTheme("preferences-other"),
                                                       trans("menu.config.models"), self.window)

        css_files = []
        css_files.append("style.css")
        css_files.append("style.dark.css")
        css_files.append("style.light.css")
        css_files.append("markdown.css")
        css_files.append("markdown.dark.css")
        css_files.append("markdown.light.css")

        json_files = []
        json_files.append("attachments.json")
        json_files.append("assistants.json")
        json_files.append("config.json")
        json_files.append("indexes.json")
        json_files.append("models.json")

        # create submenu for css files
        self.window.ui.menu['config.edit.css'] = QMenu(trans("menu.config.edit.css"), self.window)

        # create submenu for JSON files
        self.window.ui.menu['config.edit.json'] = QMenu(trans("menu.config.edit.json"), self.window)

        for css_file in css_files:
            name = css_file.split("/")[-1]
            self.window.ui.menu['config.edit.css.' + name] = QAction(QIcon.fromTheme("document-edit"),
                                                                     name, self.window)
            self.window.ui.menu['config.edit.css.' + name].triggered.connect(
                lambda checked=True, file=css_file: self.window.controller.settings.toggle_file_editor(file))
            self.window.ui.menu['config.edit.css'].addAction(self.window.ui.menu['config.edit.css.' + name])

        for json_file in json_files:
            name = json_file
            self.window.ui.menu['config.edit.json.' + name] = QAction(QIcon.fromTheme("document-edit"),
                                                                      name, self.window)
            self.window.ui.menu['config.edit.json.' + name].triggered.connect(
                lambda checked=True, file=json_file: self.window.controller.settings.toggle_file_editor(file))
            self.window.ui.menu['config.edit.json'].addAction(self.window.ui.menu['config.edit.json.' + name])

        self.window.ui.menu['config.open_dir'] = QAction(QIcon.fromTheme("folder-open"),
                                                         trans("menu.config.open_dir"), self.window)
        self.window.ui.menu['config.save'] = QAction(QIcon.fromTheme("document-save"),
                                                     trans("menu.config.save"), self.window)

        self.window.ui.menu['config.settings'].triggered.connect(
            lambda: self.window.controller.settings.toggle_editor('settings'))

        self.window.ui.menu['config.models'].triggered.connect(
            lambda: self.window.controller.model.editor.toggle_editor())

        self.window.ui.menu['config.open_dir'].triggered.connect(
            lambda: self.window.controller.settings.open_config_dir())

        self.window.ui.menu['config.save'].triggered.connect(
            lambda: self.window.controller.settings.save_all())

        self.window.ui.menu['menu.config'] = self.window.menuBar().addMenu(trans("menu.config"))
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.settings'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.models'])
        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['config.edit.css'])
        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['config.edit.json'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.open_dir'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.save'])
