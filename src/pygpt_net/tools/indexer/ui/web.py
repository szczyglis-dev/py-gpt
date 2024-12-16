#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QCheckBox, QHBoxLayout, QScrollArea, \
    QSizePolicy

from pygpt_net.ui.widget.element.group import QVLine, QHLine
from pygpt_net.ui.widget.element.labels import HelpLabel, UrlLabel, IconLabel
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.input import OptionInput
from pygpt_net.utils import trans


class WebTab:
    def __init__(self, window=None):
        """
        Tab: Web

        :param window: Window instance
        """
        self.window = window
        self.params_scroll = None
        self.params_widget = None

    def setup(self):
        """Setup tab widget"""
        # get loaders list
        loaders = self.window.controller.config.placeholder.apply_by_id("llama_index_loaders_web")
        loaders_list = []
        for loader in loaders:
            k = list(loader.keys())[0]
            key = k.replace("web_", "")
            value = loader[k]
            loaders_list.append({
                key: value,
            })

        self.window.ui.nodes["tool.indexer.web.loader"] = OptionCombo(
            self.window,
            "tool.indexer",
            "web.loader",
            {
                "label": trans("tool.indexer.tab.web.loader"),
                "keys": loaders_list,
                "value": "webpage",
            }
        )

        self.window.ui.nodes["tool.indexer.web.loader"].layout.setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes["tool.indexer.web.loader.label"] = HelpLabel(trans("tool.indexer.tab.web.loader"))
        self.window.ui.add_hook("update.tool.indexer.web.loader", self.hook_loader_change)

        self.window.ui.nodes["tool.indexer.web.options.label"] = HelpLabel(trans("tool.indexer.tab.web.source"))

        config_label = HelpLabel(trans("tool.indexer.tab.web.cfg"))
        config_label.setWordWrap(False)

        config_label_layout = QHBoxLayout()
        config_label_layout.addWidget(IconLabel(QIcon(":/icons/settings_filled.svg")))
        config_label_layout.addWidget(config_label)
        config_label_layout.setAlignment(Qt.AlignLeft)

        self.window.ui.nodes["tool.indexer.web.config.label"] = QWidget()
        self.window.ui.nodes["tool.indexer.web.config.label"].setLayout(config_label_layout)

        self.window.ui.nodes["tool.indexer.web.config.help"] = UrlLabel(
            trans("tool.indexer.tab.web.help"),
            "https://pygpt.readthedocs.io/en/latest/configuration.html#data-loaders")

        # --------------------------------------------------

        params_layout = QVBoxLayout()
        params_layout.setContentsMargins(0, 0, 0, 0)

        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.window.ui.nodes["tool.indexer.web.loader.option"] = {}
        self.window.ui.nodes["tool.indexer.web.loader.option_group"] = {}
        self.window.ui.nodes["tool.indexer.web.loader.config"] = {}
        self.window.ui.nodes["tool.indexer.web.loader.config_group"] = {}

        # params
        params_layout.addWidget(self.window.ui.nodes["tool.indexer.web.options.label"])
        inputs, groups = self.window.core.idx.ui.loaders.setup_loader_options()
        for loader in inputs:
            for k in inputs[loader]:
                self.window.ui.nodes["tool.indexer.web.loader.option." + loader + "." + k] = inputs[loader][k]
        for loader in groups:
            self.window.ui.nodes["tool.indexer.web.loader.option_group"][loader] = groups[loader]
            params_layout.addWidget(self.window.ui.nodes["tool.indexer.web.loader.option_group"][loader])
            self.window.ui.nodes["tool.indexer.web.loader.option_group"][loader].hide()  # hide on start

        # separator
        params_layout.addWidget(QHLine())

        # config
        params_layout.addWidget(self.window.ui.nodes["tool.indexer.web.config.label"])
        inputs, groups = self.window.core.idx.ui.loaders.setup_loader_config()
        for loader in inputs:
            for k in inputs[loader]:
                self.window.ui.nodes["tool.indexer.web.loader.config." + loader + "." + k] = inputs[loader][k]
        for loader in groups:
            self.window.ui.nodes["tool.indexer.web.loader.config_group"][loader] = groups[loader]
            params_layout.addWidget(self.window.ui.nodes["tool.indexer.web.loader.config_group"][loader])
            self.window.ui.nodes["tool.indexer.web.loader.config_group"][loader].hide()  # hide on start
        params_layout.addWidget(self.window.ui.nodes["tool.indexer.web.config.help"], alignment=Qt.AlignCenter)

        # stretch
        params_layout.addStretch(1)

        self.params_widget = QWidget()
        self.params_widget.setLayout(params_layout)
        self.params_scroll.setWidget(self.params_widget)

        # resize
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # --------------------------------------------------

        self.window.ui.nodes["tool.indexer.web.options.replace"] = QCheckBox(
            trans("tool.indexer.option.replace"))
        self.window.ui.nodes["tool.indexer.web.options.replace"].setChecked(True)

        self.window.ui.nodes["tool.indexer.provider"] = HelpLabel(self.window.core.config.get("llama.idx.storage"))

        loader_layout = QVBoxLayout()
        loader_layout.addWidget(self.window.ui.nodes["tool.indexer.web.loader.label"])
        loader_layout.addWidget(self.window.ui.nodes["tool.indexer.web.loader"])
        loader_layout.setContentsMargins(0, 10, 0, 0)

        options_layout = QVBoxLayout()
        options_layout.addWidget(self.window.ui.nodes["tool.indexer.web.options.replace"])

        self.window.ui.nodes["tool.indexer.web.header.tip"] = HelpLabel(trans("tool.indexer.tab.web.tip"))

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes["tool.indexer.web.header.tip"])
        layout.addLayout(loader_layout)
        layout.addLayout(options_layout)
        layout.addWidget(self.params_scroll)

        # defaults
        self.window.ui.nodes["tool.indexer.web.loader"].set_value("webpage")

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def hook_loader_change(self, key, value, caller, *args, **kwargs):
        """
        Hook: on loader change

        :param key: Option key
        :param value: Option value
        :param caller: Caller
        :param args: Args
        :param kwargs: Kwargs
        """
        # hide/show options
        for loader in self.window.ui.nodes["tool.indexer.web.loader.option_group"]:
            self.window.ui.nodes["tool.indexer.web.loader.option_group"][loader].hide()
        if value in self.window.ui.nodes["tool.indexer.web.loader.option_group"]:
            self.window.ui.nodes["tool.indexer.web.loader.option_group"][value].show()

        # show/hide label if options are available
        self.window.ui.nodes["tool.indexer.web.options.label"].hide()
        if value in self.window.ui.nodes["tool.indexer.web.loader.option_group"]:
            self.window.ui.nodes["tool.indexer.web.options.label"].show()

        # hide/show config
        for loader in self.window.ui.nodes["tool.indexer.web.loader.config_group"]:
            self.window.ui.nodes["tool.indexer.web.loader.config_group"][loader].hide()
        if value in self.window.ui.nodes["tool.indexer.web.loader.config_group"]:
            self.window.ui.nodes["tool.indexer.web.loader.config_group"][value].show()

        # show/hide label if config are available
        self.window.ui.nodes["tool.indexer.web.config.label"].hide()
        self.window.ui.nodes["tool.indexer.web.config.help"].hide()
        if value in self.window.ui.nodes["tool.indexer.web.loader.config_group"]:
            self.window.ui.nodes["tool.indexer.web.config.label"].show()
            self.window.ui.nodes["tool.indexer.web.config.help"].show()

        self.params_widget.adjustSize()
        self.params_scroll.update()
