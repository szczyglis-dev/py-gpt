#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QCheckBox, QHBoxLayout

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.option.input import DirectoryInput
from pygpt_net.utils import trans


class FilesTab:
    def __init__(self, window=None):
        """
        Tab: Files indexing

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup tab widget
        """
        # path: files
        self.window.ui.nodes["tool.indexer.file.path_file"] = DirectoryInput(
            self.window,
            "tool.indexer",
            "files.file",
            {
                "label": "Path",
                "value": "",
                "extra": {
                    "allow_file": True,
                    "allow_multiple": True,
                },
            }
        )
        self.window.ui.nodes["tool.indexer.file.path_file.label"] = QLabel(trans("tool.indexer.tab.files.path.files"))

        # path: directory
        self.window.ui.nodes["tool.indexer.file.path_dir"] = DirectoryInput(
            self.window,
            "tool.indexer",
            "files.dir",
            {
                "label": "Path",
                "value": "",
                "extra": {
                    "allow_file": False,
                    "allow_multiple": True,
                },
            }
        )
        self.window.ui.nodes["tool.indexer.file.path_dir.label"] = QLabel(trans("tool.indexer.tab.files.path.dir"))

        self.window.ui.nodes["tool.indexer.file.options.recursive"] = QCheckBox(trans("tool.indexer.option.recursive"))
        self.window.ui.nodes["tool.indexer.file.options.recursive"].setChecked(True)
        self.window.ui.nodes["tool.indexer.file.options.replace"] = QCheckBox(trans("tool.indexer.option.replace"))
        self.window.ui.nodes["tool.indexer.file.options.replace"].setChecked(True)
        self.window.ui.nodes["tool.indexer.file.options.clear"] = QCheckBox(trans("tool.indexer.option.clear"))
        self.window.ui.nodes["tool.indexer.file.options.clear"].setChecked(True)

        self.window.ui.nodes["tool.indexer.file.loaders"] = HelpLabel("")

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.window.ui.nodes["tool.indexer.file.path_file.label"])
        file_layout.addWidget(self.window.ui.nodes["tool.indexer.file.path_file"])

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.window.ui.nodes["tool.indexer.file.path_dir.label"])
        dir_layout.addWidget(self.window.ui.nodes["tool.indexer.file.path_dir"])

        options_layout = QVBoxLayout()
        options_layout.addWidget(self.window.ui.nodes["tool.indexer.file.options.recursive"])
        options_layout.addWidget(self.window.ui.nodes["tool.indexer.file.options.replace"])
        options_layout.addWidget(self.window.ui.nodes["tool.indexer.file.options.clear"])

        # layout
        self.window.ui.nodes["tool.indexer.file.header.tip"] = HelpLabel(trans("tool.indexer.tab.files.tip"))
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes["tool.indexer.file.header.tip"])
        layout.addLayout(file_layout)
        layout.addLayout(dir_layout)
        layout.addWidget(self.window.ui.nodes["tool.indexer.file.loaders"])
        layout.addLayout(options_layout)
        layout.addStretch(1)

        self.window.tools.get("indexer").update_tab_files()

        widget = QWidget()
        widget.setLayout(layout)

        return widget
