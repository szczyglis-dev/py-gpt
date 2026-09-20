#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 14:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class Skills:
    def __init__(self, window=None):
        self.window = window

    def setup(self):
        w = self.window
        ui_menu = w.ui.menu
        ctrl = w.controller.skills

        menu = ui_menu.get("menu.skills")
        if menu is None:
            menu = w.menuBar().addMenu(trans("menu.skills"))
            ui_menu["menu.skills"] = menu
        else:
            menu.setTitle(trans("menu.skills"))
            menu.clear()

        manage = QAction(QIcon(":/icons/settings_filled.svg"), trans("skills.manage"), w)
        manage.setMenuRole(QAction.MenuRole.NoRole)
        manage.triggered.connect(lambda _=False: ctrl.open(False))
        menu.addAction(manage)
        ui_menu["skills.manage"] = manage

        explore = QAction(QIcon(":/icons/apps.svg"), trans("skills.explore"), w)
        explore.setMenuRole(QAction.MenuRole.NoRole)
        explore.triggered.connect(lambda _=False: ctrl.open(True))
        menu.addAction(explore)
        ui_menu["skills.explore"] = explore

        menu.addSeparator()

        github = QAction(QIcon(":/icons/download.svg"), trans("skills.import.github"), w)
        github.setMenuRole(QAction.MenuRole.NoRole)
        github.triggered.connect(lambda _=False: ctrl.import_github())
        menu.addAction(github)
        ui_menu["skills.import.github"] = github

        local_file = QAction(QIcon(":/icons/upload.svg"), trans("skills.import.file"), w)
        local_file.setMenuRole(QAction.MenuRole.NoRole)
        local_file.triggered.connect(lambda _=False: ctrl.import_file())
        menu.addAction(local_file)
        ui_menu["skills.import.file"] = local_file

        local_folder = QAction(QIcon(":/icons/add_folder.svg"), trans("skills.import.folder"), w)
        local_folder.setMenuRole(QAction.MenuRole.NoRole)
        local_folder.triggered.connect(lambda _=False: ctrl.import_folder())
        menu.addAction(local_folder)
        ui_menu["skills.import.folder"] = local_folder

        menu.addSeparator()

        open_dir = QAction(QIcon(":/icons/folder_open.svg"), trans("skills.open_dir"), w)
        open_dir.setMenuRole(QAction.MenuRole.NoRole)
        open_dir.triggered.connect(lambda _=False: ctrl.open_directory())
        menu.addAction(open_dir)
        ui_menu["skills.open_dir"] = open_dir
        menu.setToolTipsVisible(True)
