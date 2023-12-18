#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import os

from pathlib import PurePath
from showinfm import show_in_file_manager

from ..utils import trans


class Files:
    def __init__(self, window=None):
        """
        Files controller

        :param window: Window instance
        """
        self.window = window

    def selection_change(self):
        """
        Select on list change
        """
        # TODO: implement this
        pass

    def select(self, idx):
        """
        Select attachment

        :param idx: index
        """
        # TODO: check this
        self.attachments.current = self.attachments.get_uuid_by_idx(idx)

    def delete(self, path, force=False):
        """
        Delete attachment

        :param path: path to file
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('files.delete', path, trans('files.delete.confirm'))
            return

        os.remove(path)

    def rename(self, path):
        """
        Rename attachment

        :param path: path to file
        """
        self.window.ui.dialog['rename'].id = 'output_file'
        self.window.ui.dialog['rename'].input.setText(os.path.basename(path))
        self.window.ui.dialog['rename'].current = path
        self.window.ui.dialog['rename'].show()

    def update_name(self, path, name):
        """
        Update name

        :param path: path
        :param name: name
        """
        os.rename(path, os.path.join(os.path.dirname(path), name))
        self.window.ui.dialog['rename'].close()

    def open_dir(self, path):
        """
        Open in directory

        :param path: path to file
        """
        parts = path_split = PurePath(path).parts
        path_os = os.path.join(*parts)  # fix for windows \\ path separators
        if os.path.exists(path_os):
            show_in_file_manager(path_os, True)
