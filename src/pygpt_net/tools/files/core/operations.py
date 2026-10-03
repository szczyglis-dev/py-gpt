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
import shutil
from typing import Optional, Union
from shutil import copy2


from pygpt_net.utils import trans


class Operations:
    """Files operations independent of an open explorer tab."""

    def __init__(self, tool):
        self.tool = tool

    @property
    def window(self):
        return self.tool.window

    def delete_recursive(
            self,
            path: str,
            force: bool = False
    ):
        """
        Delete directory with all files

        :param path: path to directory
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='files.delete.recursive',
                id=path,
                msg=trans('files.delete.recursive.confirm'),
            )
            return
        try:
            shutil.rmtree(path)  # delete directory with all files
            self.window.update_status(
                f"[OK] Deleted directory: {os.path.basename(path)}"
            )
            self.tool.refresh()
        except Exception as e:
            self.window.core.debug.log(e)
            print(f"Error deleting directory: {path} - {e}")

    def touch(
            self,
            path: str,
            name: Optional[str] = None,
            force: bool = False
    ):
        """
        Touch empty file

        :param path: path to file
        :param name: filename
        :param force: force touch
        """
        if not force:
            self.window.ui.dialog['create'].id = 'touch'
            self.window.ui.dialog['create'].input.setText("")
            self.window.ui.dialog['create'].current = path
            self.window.ui.dialog['create'].show()
            self.window.ui.dialog['create'].input.setFocus()
            return

        self.window.ui.dialog['create'].close()
        try:
            filepath = os.path.join(path, name)
            open(filepath, 'a').close()
            self.window.update_status(
                f"[OK] Created file: {filepath}"
            )
            self.tool.refresh()
        except Exception as e:
            self.window.core.debug.log(e)
            print(f"Error creating file: {path} - {e}")

    def delete(
            self,
            path: Union[str, list],
            force: bool = False
    ):
        """
        Delete file or directory

        :param path: path to file
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='files.delete',
                id=path,
                msg=trans('files.delete.confirm'),
            )
            return

        if isinstance(path, list):
            for p in path:
                self.delete(p, True)
            return

        if os.path.isdir(path):
            # check if directory is not empty
            if os.listdir(path):
                self.delete_recursive(path)
                return
            else:
                self.delete_recursive(path, True)
        else:
            try:
                os.remove(path)
                self.window.update_status(
                   f"[OK] Deleted file: {os.path.basename(path)}"
                )
                self.tool.refresh()
            except Exception as e:
                self.window.core.debug.log(e)
                print(f"Error deleting file: {path} - {e}")

    def duplicate(
            self,
            path: Union[str, list],
            name: str,
            force: bool = False
    ):
        """
        Duplicate file or directory

        :param path: path to file or list of files
        :param name: new file name
        :param force: force duplicate
        """
        if isinstance(path, list):
            for p in path:
                if os.path.isdir(p):
                    new_name = os.path.basename(p) + "_copy"
                else:
                    new_name = os.path.splitext(os.path.basename(p))[0] \
                               + "_copy" + os.path.splitext(p)[1]
                self.duplicate(p, new_name, True)
            return

        if not force:
            if os.path.isdir(path):
                new_name = os.path.basename(path) + "_copy"
            else:
                new_name = os.path.splitext(os.path.basename(path))[0] \
                           + "_copy" + os.path.splitext(path)[1]
            self.window.ui.dialog['create'].id = 'duplicate'
            self.window.ui.dialog['create'].input.setText(new_name)
            self.window.ui.dialog['create'].current = path
            self.window.ui.dialog['create'].show()
            self.window.ui.dialog['create'].input.setFocus()
            return

        self.window.ui.dialog['create'].close()
        self.tool.refresh()

        try:
            parent_dir = os.path.dirname(path)
            new_path = os.path.join(parent_dir, name)

            if os.path.exists(new_path):
                # prefix with timestamp if file exists
                ts_prefix = self.tool.paths.timestamp()
                name = f"{ts_prefix}_{name}"
                new_path = os.path.join(parent_dir, name)

            if os.path.isdir(path):
                shutil.copytree(path, new_path)
            else:
                copy2(path, new_path)
            self.window.update_status(
                f"[OK] Duplicated file: {os.path.basename(path)} -> {name}"
            )
            self.tool.refresh()
        except Exception as e:
            self.window.core.debug.log(e)
            print(f"Error duplicating file: {path} - {e}")

    def rename(self, path: Union[str, list]):
        """
        Rename file or directory

        :param path: path to file or list of files
        """
        if isinstance(path, list):
            for p in path:
                self.rename(p)
                return
        self.window.ui.dialog['rename'].id = 'output_file'
        self.window.ui.dialog['rename'].input.setText(os.path.basename(path))
        self.window.ui.dialog['rename'].current = path
        self.window.ui.dialog['rename'].show()
        self.window.ui.dialog['rename'].input.setFocus()

    def apply_name(
            self,
            path: str,
            name: str
    ):
        """
        Update name of file or directory

        :param path: path
        :param name: name
        """
        new_path = os.path.join(os.path.dirname(path), name)
        if os.path.exists(new_path):
            self.window.update_status(
                f"[ERROR] File already exists: {os.path.basename(new_path)}"
            )
            return
        os.rename(path, new_path)
        self.window.update_status(
           f"[OK] Renamed: {os.path.basename(path)} -> {name}"
        )
        self.window.ui.dialog['rename'].close()
        self.tool.refresh()

    def prompt_directory(self, path: str):
        """
        Open make dir directory name dialog

        :param path: path to file or directory
        """
        self.window.ui.dialog['create'].id = 'mkdir'
        self.window.ui.dialog['create'].input.setText("")
        self.window.ui.dialog['create'].current = path
        self.window.ui.dialog['create'].show()
        self.window.ui.dialog['create'].input.setFocus()

    def mkdir(
            self,
            path: str,
            name: Optional[str] = None
    ):
        """
        Make directory

        :param path: path to directory
        :param name: name of directory
        """
        self.window.ui.dialog['create'].close()
        if name is None:
            self.window.update_status(
                "[ERROR] Directory name is empty."
            )
            return
        path_dir = os.path.join(path, name)
        if os.path.exists(path_dir):
            self.window.update_status(
                "[ERROR] Directory or file already exists."
            )
            return
        os.makedirs(path_dir, exist_ok=True)
        self.window.update_status(
            f"[OK] Directory created: {name}"
        )
        self.tool.refresh()

