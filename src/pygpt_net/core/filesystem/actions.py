#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 17:00:00                  #
# ================================================== #

import os
from typing import List, Union

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from pygpt_net.utils import trans


class Actions:
    def __init__(self, window=None):
        """
        Filesystem actions

        :param window: Window instance
        """
        self.window = window

    def has_preview(self, path: Union[str, list]) -> bool:
        """
        Check if file has preview action

        :param path: path to file or list of paths
        :return: True if file has preview
        """
        if isinstance(path, list):
            for p in path:
                if not os.path.isdir(p):
                    return True  # allow preview for any file in the list
            return False
        else:
            if os.path.isdir(path):
                return False
            return True

    def has_use(self, path: str) -> bool:
        """
        Check if file has preview action

        :param path: path to file
        :return: True if file has preview
        """
        return (self.window.core.filesystem.types.is_image(path)
                or self.window.core.filesystem.types.is_video(path))

    def get_preview_batch(self, parent: QWidget, path: list) -> List[QAction]:
        """
        Get preview actions for multiple files

        :param parent: explorer widget
        :param path: list of paths
        :return: list of context menu actions
        """
        actions = []
        paths_video = []
        paths_image = []
        paths_edit = []
        for p in path:
            if os.path.isdir(p):
                continue
            actions = []
            if (self.window.core.filesystem.types.is_video(p)
                    or self.window.core.filesystem.types.is_audio(p)):
                paths_video.append(p)
            elif self.window.core.filesystem.types.is_image(p):
                paths_image.append(p)
            else:
                extra_excluded = ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt"]
                ext = os.path.splitext(p)[1][1:].lower()
                if ext not in self.window.core.filesystem.types.get_excluded_extensions() + extra_excluded:
                    paths_edit.append(p)

        # video/audio - single action for first file
        if paths_video:
            p = paths_video[0]  # single action for first video
            action = QAction(
                QIcon(":/icons/video.svg"),
                trans('action.video.play'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("player").play(p),
            )
            actions.append(action)
            action = QAction(
                QIcon(":/icons/hearing.svg"),
                trans('action.video.transcribe'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("transcriber").from_file(p),
            )
            actions.append(action)

        # image - batch preview
        if paths_image:
            action = QAction(
                QIcon(":/icons/image.svg"),
                trans('action.preview'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("viewer").open_preview_batch(paths_image),
            )
            actions.append(action)

        # edit - batch edit
        if paths_edit:
            action = QAction(
                QIcon(":/icons/edit.svg"),
                trans('action.edit'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("editor").open_batch(paths_edit),
            )
            actions.append(action)

        return actions


    def get_preview(self, parent: QWidget, path: Union[str, list]) -> List[QAction]:
        """
        Get preview actions for context menu

        :param parent: explorer widget
        :param path: path to file or list of paths
        :return: list of context menu actions
        """
        if isinstance(path, list):
            return self.get_preview_batch(parent, path)

        actions = []
        if (self.window.core.filesystem.types.is_video(path)
                or self.window.core.filesystem.types.is_audio(path)):
            action = QAction(
                QIcon(":/icons/video.svg"),
                trans('action.video.play'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("player").play(path),
            )
            actions.append(action)
            action = QAction(
                QIcon(":/icons/hearing.svg"),
                trans('action.video.transcribe'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("transcriber").from_file(path),
            )
            actions.append(action)
        elif self.window.core.filesystem.types.is_image(path):
            action = QAction(
                QIcon(":/icons/image.svg"),
                trans('action.preview'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.tools.get("viewer").open_preview(path),
            )
            actions.append(action)
        else:
            extra_excluded = ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt"]
            ext = os.path.splitext(path)[1][1:].lower()
            if ext not in self.window.core.filesystem.types.get_excluded_extensions() + extra_excluded:
                action = QAction(
                    QIcon(":/icons/edit.svg"),
                    trans('action.edit'),
                    parent,
                )
                action.triggered.connect(
                    lambda: self.window.tools.get("editor").open(path),
                )
                actions.append(action)
        return actions

    def get_use_batch(self, parent: QWidget, path: list) -> List[QAction]:
        """
        Get use actions for multiple files

        :param parent: explorer widget
        :param path: list of paths
        :return: list of context menu actions
        """
        actions = []
        for p in path:
            actions.extend(self.get_use(parent, p))
        return actions

    def get_use(self, parent: QWidget, path: Union[str, list]) -> List[QAction]:
        """
        Get use actions for context menu

        :param parent: explorer widget
        :param path: path to file or list of paths
        :return: list of context menu actions
        """
        if isinstance(path, list):
            return self.get_use_batch(parent, path)

        actions = []
        if self.window.core.filesystem.types.is_image(path):
            action = QAction(
                QIcon(":/icons/brush.svg"),
                trans('action.use.image'),
                parent,
            )
            action.triggered.connect(
                lambda: self.window.controller.painter.open_external(path),
            )
            actions.append(action)
        return actions
