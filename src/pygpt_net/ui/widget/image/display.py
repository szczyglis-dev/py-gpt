#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 14:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QLabel

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ImageLabel(QLabel):
    def __init__(self, window=None, path=None):
        """
        Presets select menu

        :param window: Window instance
        :param path: image path
        """
        super(ImageLabel, self).__init__(window)
        self.window = window
        self.path = path

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['open'] = QAction(QIcon(":/icons/fullscreen.svg"), trans('img.action.open'), self)
        actions['open'].triggered.connect(
            lambda: self.action_open(event))

        actions['open_dir'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open_dir'), self)
        actions['open_dir'].triggered.connect(
            lambda: self.action_open_dir(event))

        actions['save'] = QAction(QIcon(":/icons/save.svg"), trans('img.action.save'), self)
        actions['save'].triggered.connect(
            lambda: self.action_save(event))

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['open'])
        menu.addAction(actions['open_dir'])
        menu.addAction(actions['save'])
        menu.addAction(actions['delete'])

        menu.exec_(event.globalPos())

    def action_open(self, event):
        """
        Open action handler

        :param event: mouse event
        """
        self.window.controller.chat.image.open(self.path)

    def action_open_dir(self, event):
        """
        Open dir action handler

        :param event: mouse event
        """
        self.window.controller.chat.image.open_dir(self.path)

    def action_save(self, event):
        """
        Save action handler

        :param event: mouse event
        """
        self.window.controller.chat.image.save(self.path)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        self.window.controller.chat.image.delete(self.path)
