#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import os

from pathlib import PurePath
from showinfm import show_in_file_manager

from pygpt_net.utils import trans


class Files:
    def __init__(self, window=None):
        """
        Files controller

        :param window: Window instance
        """
        self.window = window

    def selection_change(self):
        """Select on list change"""
        # TODO: implement this
        pass

    def delete(self, path: str, force: bool = False):
        """
        Delete attachment

        :param path: path to file
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('files.delete', path, trans('files.delete.confirm'))
            return

        os.remove(path)

    def rename(self, path: str):
        """
        Rename attachment

        :param path: path to file
        """
        self.window.ui.dialog['rename'].id = 'output_file'
        self.window.ui.dialog['rename'].input.setText(os.path.basename(path))
        self.window.ui.dialog['rename'].current = path
        self.window.ui.dialog['rename'].show()

    def update_name(self, path: str, name: str):
        """
        Update name

        :param path: path
        :param name: name
        """
        os.rename(path, os.path.join(os.path.dirname(path), name))
        self.window.ui.dialog['rename'].close()

    def open_dir(self, path: str):
        """
        Open in directory

        :param path: path to file or directory
        """
        self.open_in_file_manager(path)

    def open_in_file_manager(self, path: str, select: bool = False):
        """
        Open in file manager

        :param path: path to file or directory
        :param select: select file in file manager
        """
        parts = PurePath(path).parts
        path_os = os.path.join(*parts)  # fix for windows \\ path separators
        if os.path.exists(path_os):
            if not self.window.core.platforms.is_snap():
                show_in_file_manager(path_os, select)
            else:
                # show alert info only if running in snap
                info = trans('alert.snap.file_manager') + "\n\n{}".format(path_os)
                if not os.path.isdir(path_os):
                    path_os = os.path.dirname(path_os)
                    info = trans('alert.snap.file_manager') + "\n\n{}".format(path_os)
                    self.window.ui.dialogs.alert(info)
                self.window.ui.dialogs.alert(info)
