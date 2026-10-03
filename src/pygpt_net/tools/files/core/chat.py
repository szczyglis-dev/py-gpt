#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import os
from typing import Union

from PySide6.QtWidgets import QApplication

from pygpt_net.core.text.mentions import KIND_FILE_CONTEXT, make_tag as make_mention_tag


class Chat:
    """Files chat independent of an open explorer tab."""

    def __init__(self, tool):
        self.tool = tool
        self.uploaded_ids = []

    @property
    def window(self):
        return self.tool.window

    def attach(self, path: Union[str, list]):
        """
        Use file as attachment

        :param path: path to file or list of files
        """
        paths = path if isinstance(path, list) else [path]
        for p in paths:
            title = os.path.basename(p)
            mode = self.window.core.config.get("mode")
            self.window.core.attachments.new(
                mode=mode,
                name=title,
                path=p,
                auto_save=False,
            )
        self.window.core.attachments.save()
        self.window.controller.attachment.update()

    def copy_path(self, path: Union[str, list]):
        """
        Copy system path to clipboard

        :param path: path to file or list of files
        """
        if isinstance(path, list):
            paths = [self.window.core.filesystem.get_path(p) for p in path]
            path_str = "\n".join(paths)
        else:
            path_str = self.window.core.filesystem.get_path(path)
        QApplication.clipboard().setText(path_str)
        self.window.controller.chat.common.append_to_input(path_str)

    def copy_relative_path(self, path: Union[str, list]):
        """
        Copy work path to clipboard

        :param path: path to file  or list of files
        """
        if isinstance(path, list):
            paths = [self.tool.paths.relative(p) for p in path]
            path = "\n".join(paths)
        else:
            path = self.tool.paths.relative(path)
        QApplication.clipboard().setText(path)
        self.window.controller.chat.common.append_to_input(path)

    def mention(self, path: Union[str, list]):
        """
        Append selected file/directory paths to input as mentions.

        :param path: path to file or list of files
        """
        paths = path if isinstance(path, list) else [path]
        meta = self.window.core.ctx.get_current_meta()
        mentions = []
        for item_path in paths:
            value = self.window.core.filesystem.make_local(item_path, ctx=meta).replace("\\", "/")
            if os.path.isdir(item_path):
                value = value.rstrip("/") + "/"
            mentions.append(make_mention_tag(KIND_FILE_CONTEXT, value))
        self.window.controller.chat.common.append_to_input("\n".join(mentions))

    def reset(self):
        """Reset uploaded IDs"""
        self.uploaded_ids = []

