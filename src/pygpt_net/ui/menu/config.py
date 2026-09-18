#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 12:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.utils import trans

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
        w = self.window
        m = w.ui.menu
        tr = trans

        icon_settings = QIcon(":/icons/settings_filled.svg")
        icon_access = QIcon(":/icons/accessibility.svg")
        icon_reload = QIcon(":/icons/reload.svg")
        icon_edit = QIcon(":/icons/edit.svg")
        icon_add = QIcon(":/icons/add.svg")
        icon_folder = QIcon(":/icons/folder_filled.svg")
        icon_save = QIcon(":/icons/save.svg")

        m['config.settings'] = QAction(icon_settings, tr("menu.config.settings"), w)
        m['config.settings'].setMenuRole(QAction.MenuRole.NoRole)

        m['config.models'] = QMenu(tr("menu.config.models"), w)
        m['config.agents'] = QAction(icon_settings, tr("menu.config.agents"), w)
        m['config.agents'].setMenuRole(QAction.MenuRole.NoRole)
        m['config.agents'].triggered.connect(
            lambda: w.controller.agents_v2.editor.toggle_editor()
        )

        m['config.mcp'] = QAction(icon_settings, tr("menu.config.mcp"), w)
        m['config.mcp'].setMenuRole(QAction.MenuRole.NoRole)
        m['config.mcp'].triggered.connect(
            lambda: w.controller.plugins.settings.open_plugin('mcp')
        )

        m['config.access'] = QAction(icon_access, tr("menu.config.access"), w)
        m['config.access'].setMenuRole(QAction.MenuRole.NoRole)

        m['config.models.edit'] = QAction(icon_settings, tr("menu.config.models.edit"), w)
        m['config.models.edit'].triggered.connect(
            lambda: w.controller.model.editor.toggle_editor()
        )
        m['config.models.import.provider'] = QAction(icon_reload, tr("menu.config.models.import.provider"), w)
        m['config.models.import.provider'].triggered.connect(
            lambda: w.controller.model.importer.toggle_editor()
        )

        m['config.models'].addAction(m['config.models.edit'])
        m['config.models'].addAction(m['config.models.import.provider'])

        m['config.profiles'] = {}
        m['config.profile'] = QMenu(tr("menu.config.profile"), w)

        m['config.profile.new'] = QAction(icon_add, tr("menu.config.profile.new"), w, checkable=False)
        m['config.profile.new'].triggered.connect(
            lambda: w.controller.settings.profile.new()
        )
        m['config.profile.new'].setMenuRole(QAction.MenuRole.NoRole)
        m['config.profile'].addAction(m['config.profile.new'])

        m['config.profile.edit'] = QAction(icon_edit, tr("menu.config.profile.edit"), w, checkable=False)
        m['config.profile.edit'].triggered.connect(
            lambda: w.controller.settings.profile.toggle_editor()
        )
        m['config.profile.edit'].setMenuRole(QAction.MenuRole.NoRole)
        m['config.profile'].addAction(m['config.profile.edit'])
        m['config.profile'].addSeparator()

        m['config.open_dir'] = QAction(icon_folder, tr("menu.config.open_dir"), w)
        m['config.change_dir'] = QAction(icon_settings, tr("menu.config.change_dir"), w)
        m['config.save'] = QAction(icon_save, tr("menu.config.save"), w)

        m['config.settings'].triggered.connect(
            lambda: w.controller.settings.toggle_editor('settings')
        )
        m['config.access'].triggered.connect(
            lambda: w.controller.settings.open_section('access')
        )
        m['config.open_dir'].triggered.connect(
            lambda: w.controller.settings.open_config_dir()
        )
        m['config.change_dir'].triggered.connect(
            lambda: w.controller.settings.workdir.change()
        )
        m['config.save'].triggered.connect(
            lambda: w.controller.settings.save_all()
        )

        self.lang.setup()
        self.theme.setup()

        m['menu.config'] = w.menuBar().addMenu(tr("menu.config"))
        menu = m['menu.config']
        menu.addAction(m['config.settings'])
        menu.addMenu(m['config.models'])
        menu.addAction(m['config.agents'])
        menu.addAction(m['config.mcp'])
        menu.addAction(m['config.access'])
        menu.addMenu(m['menu.theme'])
        menu.addMenu(m['menu.lang'])
        menu.addMenu(m['config.profile'])
        menu.addAction(m['config.open_dir'])
        menu.addAction(m['config.change_dir'])
        menu.addAction(m['config.save'])