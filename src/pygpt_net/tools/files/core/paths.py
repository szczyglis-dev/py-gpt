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

import datetime
import os
from typing import Union


from pygpt_net.core.filesystem.opener import Opener


class Paths:
    """Files paths independent of an open explorer tab."""

    def __init__(self, tool):
        self.tool = tool

    @property
    def window(self):
        return self.tool.window

    def reveal(
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
                    resolved = self.window.core.filesystem.get_path(p)
                    if os.path.exists(resolved):
                        Opener.open_path(resolved, reveal=select)
                if parent not in parents:
                    parents.append(parent)
            return
        path = self.window.core.filesystem.get_path(path)
        if os.path.exists(path):
            Opener.open_path(path, reveal=select)

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


    def timestamp(self) -> str:
        """
        Make timestamp prefix
        """
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def relative(self, path: str) -> str:
        """
        Strip work path

        :param path: path to file
        :return: stripped path
        """
        work_dir = self.window.core.filesystem.get_data_dir()
        path = path.replace(work_dir, "")
        if path.startswith("/") or path.startswith("\\"):
            path = path[1:]
        return path

