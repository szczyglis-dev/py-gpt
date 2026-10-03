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
from urllib.parse import unquote

from PySide6.QtWidgets import QFileDialog


class Transfers:
    """Files transfers independent of an open explorer tab."""

    def __init__(self, tool):
        self.tool = tool

    @property
    def window(self):
        return self.tool.window

    def download(self, path: Union[str, list]):
        """
        Download (copy) file or directory to local filesystem.

        Behavior:
        - Single selection: unchanged, prompts Save As dialog per current implementation.
        - Multi selection (>1 item): prompts once for a target directory and copies all selected items there.
          In case of name collision in the target directory, a timestamp prefix is added to the copied name.
        """
        # Multi-selection: choose a directory once and copy all into it
        if isinstance(path, list):
            # Normalize incoming list (decode, map to workdir)
            norm_paths = []
            for p in path:
                try:
                    p_norm = self.window.core.filesystem.to_workdir(unquote(p))
                except Exception:
                    p_norm = p
                if p_norm:
                    norm_paths.append(p_norm)

            if not norm_paths:
                return

            if len(norm_paths) == 1:
                # Defer to single-item path handling
                self.download(norm_paths[0])
                return

            last_dir = self.window.core.config.get_last_used_dir()
            target_dir = QFileDialog.getExistingDirectory(
                self.window,
                "Select target directory",
                last_dir if last_dir else os.path.expanduser("~"),
            )
            if not target_dir:
                return

            # Remember last used directory
            self.window.core.config.set_last_used_dir(target_dir)

            copied = 0

            for src in norm_paths:
                try:
                    if not os.path.exists(src):
                        continue

                    base_name = os.path.basename(src.rstrip(os.sep))
                    dst = os.path.join(target_dir, base_name)

                    # Avoid copying into itself and handle name collisions
                    if os.path.abspath(dst) == os.path.abspath(src) or os.path.exists(dst):
                        dst = os.path.join(target_dir, f"{self.tool.paths.timestamp()}_{base_name}")

                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        copy2(src, dst)
                    copied += 1
                except Exception as e:
                    self.window.core.debug.log(e)
                    print(f"Error downloading item: {src} -> {target_dir} - {e}")

            if copied > 0:
                self.window.update_status(f"[OK] Downloaded: {copied} items to: {target_dir}")
            return

        # Single-item flow (unchanged)
        path = self.window.core.filesystem.to_workdir(unquote(path))
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

    def upload(
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
                    target_directory = self.window.core.filesystem.get_data_dir()
                num = 0
                for file_path in files:
                    path_to = os.path.join(
                        target_directory,
                        os.path.basename(file_path),
                    )
                    try:
                        # if exists, append timestamp
                        if os.path.exists(path_to):
                            new_name = self.tool.paths.timestamp() + "_" + os.path.basename(file_path)
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
                    self.tool.refresh()

    def import_paths(
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
            target_directory = self.window.core.filesystem.get_data_dir()

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
            new_name = self.tool.paths.timestamp() + "_" + name
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
            self.tool.refresh()

