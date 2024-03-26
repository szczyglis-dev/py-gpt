#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
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
        if not self.path:
            return

        actions = {}
        use_actions = []
        actions['open'] = QAction(QIcon(":/icons/fullscreen.svg"), trans('img.action.open'), self)
        actions['open'].triggered.connect(
            lambda: self.action_open(event)
        )

        actions['open_dir'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open_dir'), self)
        actions['open_dir'].triggered.connect(
            lambda: self.action_open_dir(event)
        )

        actions['save'] = QAction(QIcon(":/icons/save.svg"), trans('img.action.save'), self)
        actions['save'].triggered.connect(
            lambda: self.action_save(event)
        )

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event)
        )

        actions['use_attachment'] = QAction(
            QIcon(":/icons/attachment.svg"),
            trans('action.use.attachment'),
            self,
        )
        actions['use_attachment'].triggered.connect(
            lambda: self.window.controller.files.use_attachment(self.path),
        )
        use_actions.append(actions['use_attachment'])

        # use by filetype
        if self.window.core.filesystem.actions.has_use(self.path):
            extra_use_actions = self.window.core.filesystem.actions.get_use(self, self.path)
            for action in extra_use_actions:
                use_actions.append(action)

        menu = QMenu(self)
        menu.addAction(actions['open'])
        menu.addAction(actions['open_dir'])

        # use by type
        if use_actions:
            # use menu
            use_menu = QMenu(trans('action.use'), self)
            for action in use_actions:
                use_menu.addAction(action)
            menu.addMenu(use_menu)

        menu.addAction(actions['save'])
        menu.addAction(actions['delete'])

        menu.exec_(event.globalPos())

    def action_open(self, event):
        """
        Open action handler

        :param event: mouse event
        """
        self.window.tools.get("viewer").open(self.path)

    def action_open_dir(self, event):
        """
        Open dir action handler

        :param event: mouse event
        """
        self.window.tools.get("viewer").open_dir(self.path)

    def action_save(self, event):
        """
        Save action handler

        :param event: mouse event
        """
        self.window.tools.get("viewer").save(self.path)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        self.window.tools.get("viewer").delete(self.path)
