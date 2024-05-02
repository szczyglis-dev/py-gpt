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

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.utils import trans
import pygpt_net.icons_rc

from .lang import Lang
from .theme import Theme


class Config:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window
        self.lang = Lang(window)
        self.theme = Theme(window)

    def setup(self):
        """Setup config menu"""
        self.window.ui.menu['config.settings'] = QAction(QIcon(":/icons/settings_filled.svg"),
                                                         trans("menu.config.settings"), self.window)
        self.window.ui.menu['config.settings'].setMenuRole(QAction.MenuRole.NoRole)

        self.window.ui.menu['config.models'] = QAction(QIcon(":/icons/settings_filled.svg"),
                                                       trans("menu.config.models"), self.window)

        self.window.ui.menu['config.access'] = QAction(QIcon(":/icons/accessibility.svg"),
                                                       trans("menu.config.access"), self.window)

        css_files = []
        css_files.append("style.css")
        css_files.append("style.dark.css")
        css_files.append("style.light.css")
        css_files.append("markdown.css")
        css_files.append("markdown.dark.css")
        css_files.append("markdown.light.css")
        css_files.append("web.css")
        css_files.append("web.dark.css")
        css_files.append("web.light.css")

        json_files = []
        json_files.append("attachments.json")
        json_files.append("assistants.json")
        json_files.append("config.json")
        json_files.append("models.json")
        json_files.append("plugin_presets.json")

        # -------------------------------------------- #

        # create submenu for css files
        self.window.ui.menu['config.edit.css'] = QMenu(trans("menu.config.edit.css"), self.window)

        for css_file in css_files:
            name = css_file.split("/")[-1]
            self.window.ui.menu['config.edit.css.' + name] = QAction(QIcon(":/icons/edit.svg"),
                                                                     name, self.window)
            self.window.ui.menu['config.edit.css.' + name].triggered.connect(
                lambda checked=True, file=css_file: self.window.controller.settings.toggle_file_editor(file))
            self.window.ui.menu['config.edit.css'].addAction(self.window.ui.menu['config.edit.css.' + name])

        # restore css files
        self.window.ui.menu['config.edit.css'].addSeparator()
        self.window.ui.menu['config.edit.css.restore'] = QAction(QIcon(":/icons/undo.svg"),
                                                                 trans('menu.config.edit.css.restore'), self.window)
        self.window.ui.menu['config.edit.css.restore'].triggered.connect(
            lambda checked=True: self.window.controller.layout.restore_default_css(force=False))
        self.window.ui.menu['config.edit.css'].addAction(self.window.ui.menu['config.edit.css.restore'])

        # -------------------------------------------- #

        # create submenu for JSON files
        self.window.ui.menu['config.edit.json'] = QMenu(trans("menu.config.edit.json"), self.window)

        for json_file in json_files:
            name = json_file
            self.window.ui.menu['config.edit.json.' + name] = QAction(QIcon(":/icons/edit.svg"),
                                                                      name, self.window)
            self.window.ui.menu['config.edit.json.' + name].triggered.connect(
                lambda checked=True, file=json_file: self.window.controller.settings.toggle_file_editor(file))
            self.window.ui.menu['config.edit.json'].addAction(self.window.ui.menu['config.edit.json.' + name])

        # -------------------------------------------- #

        # create submenu for profiles
        self.window.ui.menu['config.profiles'] = {}
        self.window.ui.menu['config.profile'] = QMenu(trans("menu.config.profile"), self.window)

        # add new
        self.window.ui.menu['config.profile.new'] = QAction(
            QIcon(":/icons/add.svg"), trans("menu.config.profile.new"), self.window, checkable=False)
        self.window.ui.menu['config.profile.new'].triggered.connect(
            lambda: self.window.controller.settings.profile.new())
        self.window.ui.menu['config.profile.new'].setMenuRole(QAction.MenuRole.NoRole)
        self.window.ui.menu['config.profile'].addAction(self.window.ui.menu['config.profile.new'])

        # edit
        self.window.ui.menu['config.profile.edit'] = QAction(
            QIcon(":/icons/edit.svg"), trans("menu.config.profile.edit"), self.window, checkable=False)
        self.window.ui.menu['config.profile.edit'].triggered.connect(
            lambda: self.window.controller.settings.profile.toggle_editor())
        self.window.ui.menu['config.profile.edit'].setMenuRole(QAction.MenuRole.NoRole)
        self.window.ui.menu['config.profile'].addAction(self.window.ui.menu['config.profile.edit'])
        self.window.ui.menu['config.profile'].addSeparator()

        # -------------------------------------------- #

        self.window.ui.menu['config.open_dir'] = QAction(QIcon(":/icons/folder_filled.svg"),
                                                         trans("menu.config.open_dir"), self.window)
        self.window.ui.menu['config.change_dir'] = QAction(QIcon(":/icons/settings_filled.svg"),
                                                         trans("menu.config.change_dir"), self.window)
        self.window.ui.menu['config.save'] = QAction(QIcon(":/icons/save.svg"),
                                                     trans("menu.config.save"), self.window)

        self.window.ui.menu['config.settings'].triggered.connect(
            lambda: self.window.controller.settings.toggle_editor('settings'))

        self.window.ui.menu['config.models'].triggered.connect(
            lambda: self.window.controller.model.editor.toggle_editor())

        self.window.ui.menu['config.access'].triggered.connect(
            lambda: self.window.controller.settings.open_section('access'))

        self.window.ui.menu['config.open_dir'].triggered.connect(
            lambda: self.window.controller.settings.open_config_dir())

        self.window.ui.menu['config.change_dir'].triggered.connect(
            lambda: self.window.controller.settings.workdir.change())

        self.window.ui.menu['config.save'].triggered.connect(
            lambda: self.window.controller.settings.save_all())

        self.lang.setup()
        self.theme.setup()

        self.window.ui.menu['menu.config'] = self.window.menuBar().addMenu(trans("menu.config"))
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.settings'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.models'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.access'])

        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['menu.theme'])
        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['menu.lang'])
        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['config.edit.css'])
        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['config.edit.json'])
        self.window.ui.menu['menu.config'].addMenu(self.window.ui.menu['config.profile'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.open_dir'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.change_dir'])
        self.window.ui.menu['menu.config'].addAction(self.window.ui.menu['config.save'])
