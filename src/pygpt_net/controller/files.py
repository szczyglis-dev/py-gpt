#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 19:00:00                  #
# ================================================== #

import os
import shutil

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QApplication
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

    def delete_recursive(self, path: str, force: bool = False):
        """
        Delete directory with all files
        :param path: path to directory
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                'files.delete.recursive',
                path,
                trans('files.delete.recursive.confirm'),
            )
            return
        try:
            shutil.rmtree(path)  # delete directory with all files
            self.window.update_status("[OK] Deleted directory: {}".format(os.path.basename(path)))
            self.update_explorer()
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error deleting directory: {} - {}".format(path, e))

    def touch_file(self, path: str, name: str = None, force: bool = False):
        """Touch empty file"""
        if not force:
            self.window.ui.dialog['create'].id = 'touch'
            self.window.ui.dialog['create'].input.setText("")
            self.window.ui.dialog['create'].current = path
            self.window.ui.dialog['create'].show()
            self.window.ui.dialog['create'].input.setFocus()
            return
        try:
            filepath = os.path.join(path, name)
            open(filepath, 'a').close()
            self.window.update_status("[OK] Created file: {}".format(os.path.basename(filepath)))
            self.update_explorer()
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error creating file: {} - {}".format(path, e))

    def delete(self, path: str, force: bool = False):
        """
        Delete file or directory

        :param path: path to file
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm(
                'files.delete',
                path,
                trans('files.delete.confirm'),
            )
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
                    "[OK] Deleted file: {}".format(os.path.basename(path))
                )
                self.update_explorer()
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error deleting file: {} - {}".format(path, e))

    def duplicate_local(self, path: str, name: str, force: bool = False):
        """
        Duplicate file

        :param path: path to file
        :param name: new file name
        :param force: force duplicate
        """
        if not force:
            self.window.ui.dialog['create'].id = 'duplicate'
            self.window.ui.dialog['create'].input.setText(os.path.basename(path) + ' - copy')
            self.window.ui.dialog['create'].current = path
            self.window.ui.dialog['create'].show()
            self.window.ui.dialog['create'].input.setFocus()
            return

        self.window.ui.dialog['create'].close()
        self.update_explorer()

        try:
            parent_dir = os.path.dirname(path)
            new_path = os.path.join(parent_dir, name)

            if os.path.exists(new_path):
                self.window.update_status("[ERROR] File already exists: {}".format(os.path.basename(new_path)))
                return

            if os.path.isdir(path):
                shutil.copytree(path, new_path)
            else:
                copy2(path, new_path)
            self.window.update_status("[OK] Duplicated file: {}".format(os.path.basename(path)))
            self.update_explorer()
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error duplicating file: {} - {}".format(path, e))

    def download_local(self, path: str):
        """
        Download (copy) file to local directory

        :param path: path to source file
        """
        last_dir = self.window.core.config.get_last_used_dir()
        dialog = QFileDialog(self.window)
        dialog.setDirectory(last_dir)
        dialog.selectFile(os.path.basename(path))
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.window.core.config.set_last_used_dir(os.path.dirname(files[0]))
                try:
                    if os.path.isdir(path):
                        shutil.copytree(path, files[0])
                    else:
                        shutil.copy2(path, files[0])
                    self.window.update_status("[OK] Downloaded file: {}".format(os.path.basename(path)))
                except Exception as e:
                    self.window.core.debug.log(e)
                    print("Error downloading file: {} - {}".format(path, e))

    def upload_local(self, parent_path: str = None):
        """
        Upload local file(s)

        :param parent_path: parent path
        """
        last_dir = self.window.core.config.get_last_used_dir()
        dialog = QFileDialog(self.window)
        dialog.setDirectory(last_dir)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.window.core.config.set_last_used_dir(os.path.dirname(files[0]))
                if parent_path is not None:
                    target_directory = parent_path
                else:
                    target_directory = self.window.core.config.get_user_dir('data')
                num = 0
                for file_path in files:
                    try:
                        os.makedirs(target_directory, exist_ok=True)
                        copy2(file_path, target_directory)
                        num += 1
                    except Exception as e:
                        self.window.core.debug.log(e)
                        print("Error copying file {}: {}".format(file_path, e))
                if num > 0:
                    self.window.update_status("[OK] Uploaded: {} files.".format(num))
                    self.update_explorer()

    def rename(self, path: str):
        """
        Rename file or directory

        :param path: path to file
        """
        self.window.ui.dialog['rename'].id = 'output_file'
        self.window.ui.dialog['rename'].input.setText(os.path.basename(path))
        self.window.ui.dialog['rename'].current = path
        self.window.ui.dialog['rename'].show()
        self.window.ui.dialog['rename'].input.setFocus()

    def update_name(self, path: str, name: str):
        """
        Update name

        :param path: path
        :param name: name
        """
        os.rename(path, os.path.join(os.path.dirname(path), name))
        self.window.update_status("[OK] Renamed: {} -> {}".format(os.path.basename(path), name))
        self.window.ui.dialog['rename'].close()
        self.update_explorer()

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
                path = self.window.core.filesystem.get_path(path)
                url = QUrl.fromLocalFile(path)
                QDesktopServices.openUrl(url)
            else:
                subprocess.run(['xdg-open', path])

    def open_in_file_manager(self, path: str, select: bool = False):
        """
        Open in file manager

        :param path: path to file or directory
        :param select: select file in file manager
        """
        path = self.window.core.filesystem.get_path(path)
        if select:  # path to file: open containing directory
            path = self.window.core.filesystem.get_path(os.path.dirname(path))

        if os.path.exists(path):
            if not self.window.core.platforms.is_snap():
                url = self.window.core.filesystem.get_url(path)
                QDesktopServices.openUrl(url)
                # show_in_file_manager(path, select)
            else:
                subprocess.run(['xdg-open', path])

    def make_dir_dialog(self, path: str):
        """
        Open make dir directory name dialog

        :param path: path to file or directory
        """
        print("make dir")
        print(path)
        self.window.ui.dialog['create'].id = 'mkdir'
        self.window.ui.dialog['create'].input.setText("")
        self.window.ui.dialog['create'].current = path
        self.window.ui.dialog['create'].show()
        self.window.ui.dialog['create'].input.setFocus()

    def make_dir(self, path: str, name: str = None):
        """
        Make directory

        :param path: path to directory
        :param name: directory name
        """
        print("make dir: {} => {}".format(path, name))
        self.window.ui.dialog['create'].close()
        if name is None:
            self.window.update_status("[ERROR] Directory name is empty.")
            return
        path_dir = os.path.join(path, name)
        if os.path.exists(path_dir):
            self.window.update_status("ERROR] Directory already exists.")
            return
        os.makedirs(path_dir, exist_ok=True)
        self.window.update_status("[OK] Directory created: {}".format(name))
        self.update_explorer()

    def update_explorer(self):
        """Update file explorer view"""
        all_idx_data = self.window.core.idx.get_idx_data()  # get all files data, from all indexes
        self.window.ui.nodes['output_files'].model.update_idx_status(all_idx_data)

    def use_attachment(self, path: str):
        """
        Use as attachment

        :param path: path to file
        """
        title = os.path.basename(path)
        mode = self.window.core.config.get("mode")
        self.window.core.attachments.new(mode, title, path, False)
        self.window.core.attachments.save()
        self.window.controller.attachment.update()

    def copy_sys_path(self, path: str):
        """
        Copy system path to clipboard

        :param path: path to file
        """
        QApplication.clipboard().setText(path)
        self.window.controller.chat.common.append_to_input(path)

    def copy_work_path(self, path: str):
        """
        Copy work path to clipboard

        :param path: path to file
        """
        path = self.strip_work_path(path)
        QApplication.clipboard().setText(path)
        self.window.controller.chat.common.append_to_input(path)

    def make_read_cmd(self, path: str):
        """
        Make read command

        :param path: path to file
        """
        if os.path.isdir(path):
            cmd = "Please read files from current directory: {}".format(self.strip_work_path(path))
        else:
            cmd = "Please read file from current directory: {}".format(self.strip_work_path(path))
        self.window.controller.chat.common.append_to_input(cmd)

    def strip_work_path(self, path: str):
        """
        Strip work path

        :param path: path to file
        """
        work_dir = self.window.core.config.get_user_dir("data")
        path = path.replace(work_dir, "")
        if path.startswith("/") or path.startswith("\\"):
            path = path[1:]
        return path
