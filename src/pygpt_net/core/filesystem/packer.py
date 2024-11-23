#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.23 21:00:00                  #
# ================================================== #

import os
import shutil

from uuid import uuid4

class Packer:
    def __init__(self, window=None):
        """
        Archive packer/unpacker

        :param window: Window instance
        """
        self.window = window
        self.zip_ext = [".zip"]
        self.tar_ext = [".tar", ".gz", ".bz2"]

    def is_archive(self, path: str) -> bool:
        """
        Check if path is archive

        :param path: Path to file
        :return: True if archive
        """
        ext = os.path.splitext(path)[1]
        return ext in self.zip_ext or ext in self.tar_ext

    def unpack(self, path: str) -> str:
        """
        Unpack archive

        :param path: path to archive
        :return: path to unpacked directory
        """
        uuid = str(uuid4())
        tmp_dir = os.path.join(self.window.core.config.get_user_dir("tmp"), uuid)
        os.makedirs(tmp_dir, exist_ok=True)
        ext = os.path.splitext(path)[1]
        if ext in self.zip_ext:
            return self.unpack_zip(path, tmp_dir)
        elif ext in self.tar_ext:
            return self.unpack_tar(path, tmp_dir)

    def unpack_zip(self, path: str, dir: str) -> str:
        """
        Unpack archive to temporary directory

        :param path: path to archive
        :param dir: temporary directory
        :return: path to unpacked directory
        """
        import zipfile
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(dir)
        return dir

    def unpack_tar(self, path: str, dir: str) -> str:
        """
        Unpack archive to temporary directory

        :param path: path to archive
        :param dir: temporary directory
        :return: path to unpacked directory
        """
        import tarfile
        with tarfile.open(path, 'r') as tar_ref:
            tar_ref.extractall(dir)
        return dir

    def remove_tmp(self, path: str):
        """
        Remove temporary directory

        :param path: path to directory
        """
        if os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path)