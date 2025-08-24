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

from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class File:
    def __init__(self, window=None):
        """
        Menu setup

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup file menu"""
        w = self.window
        m = w.ui.menu
        ctx = w.controller.ctx

        icon_logout = QIcon(":/icons/logout.svg")
        icon_delete = QIcon(":/icons/delete.svg")
        icon_add = QIcon(":/icons/add.svg")
        icon_folder = QIcon(":/icons/folder_filled.svg")
        icon_fullscreen = QIcon(":/icons/fullscreen.svg")

        m['app.exit'] = QAction(icon_logout, trans("menu.file.exit"), w, shortcut="Ctrl+Q", triggered=w.close)
        m['app.exit'].setMenuRole(QAction.MenuRole.NoRole)

        m['app.clear_history'] = QAction(icon_delete, trans("menu.file_clear_history"), w)
        m['app.clear_history_groups'] = QAction(icon_delete, trans("menu.file_clear_history_groups"), w)

        m['app.ctx.new'] = QAction(icon_add, trans("menu.file.new"), w)
        m['app.ctx.group.new'] = QAction(icon_folder, trans("menu.file.group.new"), w)
        m['app.ctx.current'] = QAction(icon_fullscreen, trans("menu.file.current"), w)

        m['app.clear_history'].triggered.connect(ctx.delete_history)
        m['app.clear_history_groups'].triggered.connect(ctx.delete_history_groups)
        m['app.ctx.new'].triggered.connect(ctx.new_ungrouped)  # new context without group
        m['app.ctx.group.new'].triggered.connect(ctx.new_group)
        m['app.ctx.current'].triggered.connect(
            lambda checked=False: ctx.select_by_current(True)
        )  # new context without group

        m['menu.app'] = w.menuBar().addMenu(trans("menu.file"))
        m_app = m['menu.app']
        m_app.addActions([
            m['app.ctx.new'],
            m['app.ctx.group.new'],
            m['app.ctx.current'],
            m['app.clear_history'],
            m['app.clear_history_groups'],
            m['app.exit'],
        ])