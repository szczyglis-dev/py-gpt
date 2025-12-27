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

import datetime
import os
import shutil
from typing import Optional, Union
from shutil import copy2

from PySide6.QtWidgets import QFileDialog, QApplication

from pygpt_net.core.filesystem.opener import Opener
from pygpt_net.utils import trans


class Files:
    def __init__(self, window=None):
        """
        Files controller

        :param window: Window instance
        """
        self.window = window
        self.uploaded_ids = []

    def selection_change(self):
        """Select on list change"""
        # TODO: implement this
        pass

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
            self.update_explorer()
        except Exception as e:
            self.window.core.debug.log(e)
            print(f"Error deleting directory: {path} - {e}")

    def touch_file(
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
            self.update_explorer()
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
                self.update_explorer()
            except Exception as e:
                self.window.core.debug.log(e)
                print(f"Error deleting file: {path} - {e}")

    def duplicate_local(
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
                self.duplicate_local(p, new_name, True)
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
        self.update_explorer()

        try:
            parent_dir = os.path.dirname(path)
            new_path = os.path.join(parent_dir, name)

            if os.path.exists(new_path):
                # prefix with timestamp if file exists
                ts_prefix = self.make_ts_prefix()
                name = f"{ts_prefix}_{name}"
                new_path = os.path.join(parent_dir, name)

            if os.path.isdir(path):
                shutil.copytree(path, new_path)
            else:
                copy2(path, new_path)
            self.window.update_status(
                f"[OK] Duplicated file: {os.path.basename(path)} -> {name}"
            )
            self.update_explorer()
        except Exception as e:
            self.window.core.debug.log(e)
            print(f"Error duplicating file: {path} - {e}")

    def download_local(self, path: Union[str, list]):
        """
        Download (copy) file or directory to local filesystem

        :param path: path to source file or list of files
        """
        if isinstance(path, list):
            for p in path:
                self.download_local(p)
            return
        last_dir = self.window.core.config.get_last_used_dir()
        dialog = QFileDialog(self.window)
        dialog.setDirectory(last_dir)
        dialog.selectFile(os.path.basename(path))
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.window.core.config.set_last_used_dir(
                    os.path.dirname(files[0])
                )
                try:
                    if os.path.isdir(path):
                        shutil.copytree(path, files[0])
                    else:
                        shutil.copy2(path, files[0])
                    self.window.update_status(
                        f"[OK] Downloaded file: {os.path.basename(path)}"
                    )
                except Exception as e:
                    self.window.core.debug.log(e)
                    print(f"Error downloading file: {path} - {e}")

    def upload_local(
            self,
            parent_path: Optional[str] = None
    ):
        """
        Upload local file(s) to directory

        :param parent_path: parent path
        """
        last_dir = self.window.core.config.get_last_used_dir()
        dialog = QFileDialog(self.window)
        dialog.setDirectory(last_dir)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec():
            files = dialog.selectedFiles()
            if files:
                self.window.core.config.set_last_used_dir(
                    os.path.dirname(files[0])
                )
                if parent_path:
                    target_directory = parent_path
                else:
                    target_directory = self.window.core.config.get_user_dir('data')
                num = 0
                for file_path in files:
                    path_to = os.path.join(
                        target_directory,
                        os.path.basename(file_path),
                    )
                    try:
                        # if exists, append timestamp
                        if os.path.exists(path_to):
                            new_name = self.make_ts_prefix() + "_" + os.path.basename(file_path)
                            target_path = os.path.join(
                                target_directory,
                                new_name,
                            )
                        else:
                            target_path = os.path.join(
                                target_directory,
                                os.path.basename(file_path),
                            )
                        if not os.path.exists(target_directory):
                            os.makedirs(
                                target_directory,
                                exist_ok=True,
                            )
                        copy2(file_path, target_path)
                        num += 1
                    except Exception as e:
                        self.window.core.debug.log(e)
                        print(f"Error copying file {file_path}: {e}")
                if num > 0:
                    self.window.update_status(f"[OK] Uploaded: {num} files.")
                    self.update_explorer()

    def upload_paths(
            self,
            paths: list,
            target_directory: Optional[str] = None
    ):
        """
        Upload provided local paths (files or directories) into target directory.
        - Directories are copied recursively.
        - Name collisions are resolved using timestamp prefix, consistent with upload_local().
        - Skips copying directory into itself or its subdirectory.

        :param paths: list of absolute local paths
        :param target_directory: destination directory (defaults to user 'data' dir)
        """
        if not paths:
            return
        if target_directory is None:
            target_directory = self.window.core.config.get_user_dir('data')

        try:
            if not os.path.exists(target_directory):
                os.makedirs(target_directory, exist_ok=True)
        except Exception as e:
            self.window.core.debug.log(e)
            return

        copied = 0

        def unique_dest(dest_path: str) -> str:
            if not os.path.exists(dest_path):
                return dest_path
            base_dir = os.path.dirname(dest_path)
            name = os.path.basename(dest_path)
            new_name = self.make_ts_prefix() + "_" + name
            return os.path.join(base_dir, new_name)

        for src in paths:
            try:
                if not src or not os.path.exists(src):
                    continue

                # Prevent copying a directory into itself or its subdirectory
                try:
                    if os.path.isdir(src):
                        common = os.path.commonpath([os.path.abspath(src), os.path.abspath(target_directory)])
                        if common == os.path.abspath(src):
                            # target is inside src; skip
                            self.window.core.debug.log(f"Skipped copying directory into itself: {src} -> {target_directory}")
                            continue
                except Exception:
                    pass

                dest_base = os.path.join(target_directory, os.path.basename(src))
                dest_path = unique_dest(dest_base)

                if os.path.isdir(src):
                    shutil.copytree(src, dest_path)
                    copied += 1
                else:
                    copy2(src, dest_path)
                    copied += 1
            except Exception as e:
                self.window.core.debug.log(e)
                print(f"Error uploading path {src}: {e}")

        if copied > 0:
            self.window.update_status(f"[OK] Uploaded: {copied} files.")
            self.update_explorer()

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

    def update_name(
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
        self.update_explorer()

    def open_dir(
            self,
            path: Union[str, list],
            select: bool = False
    ):
        """
        Open file or directory in file manager

        :param path: path to file or directory or list of paths
        :param select: select file in file manager
        """
        if isinstance(path, list):
            parents = []
            for p in path:
                parent = os.path.dirname(p)
                if parent not in parents:
                    self.open_in_file_manager(p, select)
                if parent not in parents:
                    parents.append(parent)
            return
        self.open_in_file_manager(path, select)

    def open(self, path: Union[str, list]):
        """
        Open path in file manager or with default application

        :param path: path to file or directory or list of paths
        """
        if isinstance(path, list):
            for p in path:
                self.open(p)
            return
        path = self.window.core.filesystem.get_path(path)
        Opener.open_path(path, reveal=False)

    def open_in_file_manager(
            self,
            path: str,
            select: bool = False
    ):
        """
        Open in file manager

        :param path: path to file or directory
        :param select: select file in file manager
        """
        path = self.window.core.filesystem.get_path(path)
        if os.path.exists(path):
            Opener.open_path(path, reveal=select)

    def make_dir_dialog(self, path: str):
        """
        Open make dir directory name dialog

        :param path: path to file or directory
        """
        self.window.ui.dialog['create'].id = 'mkdir'
        self.window.ui.dialog['create'].input.setText("")
        self.window.ui.dialog['create'].current = path
        self.window.ui.dialog['create'].show()
        self.window.ui.dialog['create'].input.setFocus()

    def make_dir(
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
        self.update_explorer()

    def update_explorer(self, reload: bool = False):
        """
        Update file explorer view

        :param: reload: reload explorer root dir
        """
        data = self.window.core.idx.get_idx_data()  # get all files data, from all indexes
        self.window.ui.nodes['output_files'].index_data = data
        if reload:
            root = self.window.core.config.get_user_dir('data')
            self.window.ui.nodes['output_files'].directory = root
            self.window.ui.nodes['output_files'].update_view()
            self.window.ui.nodes['output_files'].path_label.setText(root)
        self.window.ui.nodes['output_files'].model.update_idx_status(data)

    def use_attachment(self, path: Union[str, list]):
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

    def copy_sys_path(self, path: Union[str, list]):
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

    def copy_work_path(self, path: Union[str, list]):
        """
        Copy work path to clipboard

        :param path: path to file  or list of files
        """
        if isinstance(path, list):
            paths = [self.strip_work_path(p) for p in path]
            path = "\n".join(paths)
        else:
            path = self.strip_work_path(path)
        QApplication.clipboard().setText(path)
        self.window.controller.chat.common.append_to_input(path)

    def make_read_cmd(self, path: Union[str, list]):
        """
        Make read command for file or directory and append to input

        :param path: path to file or list of files
        """
        files_list = path if isinstance(path, list) else [path]
        cmd = ""
        cmd_dir = []
        cmd_current = []
        for path in files_list:
            if os.path.isdir(path):
                cmd_dir.append(self.strip_work_path(path))
            else:
                cmd_current.append(self.strip_work_path(path))
        if len(cmd_dir) > 1:
            cmd = "Please list files from directories: " + ", ".join(cmd_dir)
        elif len(cmd_dir) == 1:
            cmd = f"Please list files from directory: {cmd_dir[0]}"
        if len(cmd_current) > 1:
            cmd = "Please read these files from current directory: " + ", ".join(cmd_current)
        elif len(cmd_current) == 1:
            cmd = f"Please read this file from current directory: {cmd_current[0]}"
        self.window.controller.chat.common.append_to_input(cmd)

    def make_ts_prefix(self) -> str:
        """
        Make timestamp prefix
        """
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def strip_work_path(self, path: str) -> str:
        """
        Strip work path

        :param path: path to file
        :return: stripped path
        """
        work_dir = self.window.core.config.get_user_dir("data")
        path = path.replace(work_dir, "")
        if path.startswith("/") or path.startswith("\\"):
            path = path[1:]
        return path

    def reset(self):
        """Reset uploaded IDs"""
        self.uploaded_ids = []

    def get_ids(self) -> list:
        """
        Get uploaded files IDs

        :return: uploaded files IDs
        """
        return self.uploaded_ids

    def reload(self):
        """Reload files"""
        self.update_explorer(reload=True)