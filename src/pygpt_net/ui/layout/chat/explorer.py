#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.19 02:00:00                  #
# ================================================== #

from pygpt_net.ui.widget.tabs.body import TabBody
from pygpt_net.ui.widget.filesystem.explorer import FileExplorer


class Explorer:
    def __init__(self, window=None):
        """
        Chat output UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> TabBody:
        """
        Setup file explorer

        :return: TabBody
        """
        # index status data
        index_data = {}  # file index status is resolved lazily per visible path

        # file explorer
        path = self.window.core.filesystem.get_data_dir()
        self.window.ui.nodes['output_files'] = FileExplorer(self.window, path, index_data)

        # build tab body
        body = self.window.core.tabs.from_widget(self.window.ui.nodes['output_files'])
        body.append(self.window.ui.nodes['output_files'])
        return body
