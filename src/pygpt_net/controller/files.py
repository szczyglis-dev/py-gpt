#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.18 12:00:00                  #
# ================================================== #

import os

from pathlib import PurePath

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog
from showinfm import show_in_file_manager
from shutil import copy2
import subprocess

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

    def upload_local(self):
        """
        Upload local file(s)
        """
        files, _ = QFileDialog.getOpenFileNames(self.window, "Select files to upload", "")
        if files:
            target_directory = self.window.core.config.get_user_dir('data')
            num = 0
            for file_path in files:
                try:
                    os.makedirs(target_directory, exist_ok=True)
                    copy2(file_path, target_directory)
                    num += 1
                except Exception as e:
                    print(f'Error copying file {file_path}: {e}')
            if num > 0:
                self.window.update_status(f'[OK] Uploaded: {num} files.')

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

    def open_dir(self, path: str, select: bool = False):
        """
        Open in directory

        :param path: path to file or directory
        :param select: select file in file manager
        """
        self.open_in_file_manager(path, select)

    def open(self, path: str):
        """
        Open file or directory

        :param path: path to file or directory
        """
        if os.path.isdir(path):
            self.open_dir(path)
        else:
            if not self.window.core.platforms.is_snap():
                parts = PurePath(path).parts
                path_os = os.path.join(*parts)  # fix for windows \\ path separators
                url = QUrl.fromLocalFile(path_os)
                QDesktopServices.openUrl(url)
            else:
                subprocess.run(['xdg-open', path])

    def open_in_file_manager(self, path: str, select: bool = False):
        """
        Open in file manager

        :param path: path to file or directory
        :param select: select file in file manager
        """
        parts = PurePath(path).parts
        path_os = os.path.join(*parts)  # fix for windows \\ path separators
        if select:
            # get directory path:
            parts = PurePath(os.path.dirname(path)).parts
            path_os = os.path.join(*parts)  # fix for windows \\ path separators
        if os.path.exists(path_os):
            if not self.window.core.platforms.is_snap():
                url = QUrl("file:///" + path_os, QUrl.TolerantMode)
                QDesktopServices.openUrl(url)
                # show_in_file_manager(path_os, select)
            else:
                subprocess.run(['xdg-open', path_os])
