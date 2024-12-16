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

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QScrollArea, QWidget, QSizePolicy

from pygpt_net.ui.widget.element.group import QHLine
from pygpt_net.ui.widget.element.labels import HelpLabel, UrlLabel, IconLabel
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.utils import trans
from pygpt_net.ui.widget.textarea.url import UrlInput


class UrlDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Url dialog

        :param window: main window
        :param id: info window id
        """
        super(UrlDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None
        #self.input = UrlInput(window, id)
        #self.input.setMinimumWidth(400)
        self.initialized = False
        self.params_scroll = None

    def init(self):
        """Initialize dialog"""
        if self.initialized:
            return

        self.window.ui.nodes['dialog.url.btn.update'] = QPushButton(trans('dialog.url.update'))
        self.window.ui.nodes['dialog.url.btn.update'].clicked.connect(
            lambda: self.window.controller.attachment.attach_url()
        )

        self.window.ui.nodes['dialog.url.btn.dismiss'] = QPushButton(trans('dialog.url.dismiss'))
        self.window.ui.nodes['dialog.url.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss_url())

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.url.btn.dismiss'])
        bottom.addWidget(self.window.ui.nodes['dialog.url.btn.update'])

        #self.window.ui.nodes['dialog.url.label'] = QLabel(trans("dialog.url.title"))
        #self.window.ui.nodes['dialog.url.tip'] = HelpLabel(trans("dialog.url.tip"))

        # -----------------

        loaders = self.window.controller.config.placeholder.apply_by_id("llama_index_loaders_web")
        loaders_list = []
        for loader in loaders:
            k = list(loader.keys())[0]
            key = k.replace("web_", "")
            value = loader[k]
            loaders_list.append({
                key: value,
            })

        self.window.ui.nodes["dialog.url.loader"] = OptionCombo(
            self.window,
            "dialog.url",
            "web.loader",
            {
                "label": trans("tool.indexer.tab.web.loader"),
                "keys": loaders_list,
                "value": "webpage",
            }
        )

        self.window.ui.nodes["dialog.url.loader"].layout.setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes["dialog.url.loader.label"] = HelpLabel(trans("tool.indexer.tab.web.loader"))
        self.window.ui.add_hook("update.dialog.url.web.loader", self.hook_loader_change)

        self.window.ui.nodes["dialog.url.options.label"] = HelpLabel(trans("tool.indexer.tab.web.source"))

        config_label = HelpLabel(trans("tool.indexer.tab.web.cfg"))
        config_label.setWordWrap(False)

        config_label_layout = QHBoxLayout()
        config_label_layout.addWidget(IconLabel(QIcon(":/icons/settings_filled.svg")))
        config_label_layout.addWidget(config_label)
        config_label_layout.setAlignment(Qt.AlignLeft)

        self.window.ui.nodes["dialog.url.config.label"] = QWidget()
        self.window.ui.nodes["dialog.url.config.label"].setLayout(config_label_layout)

        self.window.ui.nodes["dialog.url.config.help"] = UrlLabel(
            trans("tool.indexer.tab.web.help"),
            "https://pygpt.readthedocs.io/en/latest/configuration.html#data-loaders")

        params_layout = QVBoxLayout()
        params_layout.setContentsMargins(0, 0, 0, 0)

        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.window.ui.nodes["dialog.url.loader.option"] = {}
        self.window.ui.nodes["dialog.url.loader.option_group"] = {}
        self.window.ui.nodes["dialog.url.loader.config"] = {}
        self.window.ui.nodes["dialog.url.loader.config_group"] = {}

        # params
        params_layout.addWidget(self.window.ui.nodes["dialog.url.options.label"])
        inputs, groups = self.window.core.idx.ui.loaders.setup_loader_options()

        for loader in inputs:
            for k in inputs[loader]:
                self.window.ui.nodes["dialog.url.loader.option." + loader + "." + k] = inputs[loader][k]
        for loader in groups:
            self.window.ui.nodes["dialog.url.loader.option_group"][loader] = groups[loader]
            params_layout.addWidget(self.window.ui.nodes["dialog.url.loader.option_group"][loader])
            self.window.ui.nodes["dialog.url.loader.option_group"][loader].hide()  # hide on start

        # separator
        params_layout.addWidget(QHLine())

        # config
        params_layout.addWidget(self.window.ui.nodes["dialog.url.config.label"])
        inputs, groups = self.window.core.idx.ui.loaders.setup_loader_config()

        for loader in inputs:
            for k in inputs[loader]:
                self.window.ui.nodes["dialog.url.loader.config." + loader + "." + k] = inputs[loader][k]
        for loader in groups:
            self.window.ui.nodes["dialog.url.loader.config_group"][loader] = groups[loader]
            params_layout.addWidget(self.window.ui.nodes["dialog.url.loader.config_group"][loader])
            self.window.ui.nodes["dialog.url.loader.config_group"][loader].hide()  # hide on start
        params_layout.addWidget(self.window.ui.nodes["dialog.url.config.help"], alignment=Qt.AlignCenter)

        # stretch
        params_layout.addStretch(1)

        self.params_widget = QWidget()
        self.params_widget.setLayout(params_layout)
        self.params_scroll.setWidget(self.params_widget)

        # resize
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # -----------------

        layout = QVBoxLayout()
        #layout.addWidget(self.window.ui.nodes['dialog.url.label'])
        #layout.addWidget(self.input)
        #layout.addWidget(self.window.ui.nodes['dialog.url.tip'])
        layout.addWidget(self.window.ui.nodes['dialog.url.loader.label'])
        layout.addWidget(self.window.ui.nodes['dialog.url.loader'])
        layout.addWidget(self.params_scroll)
        layout.addLayout(bottom)

        # defaults
        self.window.ui.nodes["dialog.url.loader"].set_value("webpage")

        self.setLayout(layout)

        self.initialized = True

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
        for loader in self.window.ui.nodes["dialog.url.loader.option_group"]:
            self.window.ui.nodes["dialog.url.loader.option_group"][loader].hide()
        if value in self.window.ui.nodes["dialog.url.loader.option_group"]:
            self.window.ui.nodes["dialog.url.loader.option_group"][value].show()

        # show/hide label if options are available
        self.window.ui.nodes["dialog.url.options.label"].hide()
        if value in self.window.ui.nodes["dialog.url.loader.option_group"]:
            self.window.ui.nodes["dialog.url.options.label"].show()

        # hide/show config
        for loader in self.window.ui.nodes["dialog.url.loader.config_group"]:
            self.window.ui.nodes["dialog.url.loader.config_group"][loader].hide()
        if value in self.window.ui.nodes["dialog.url.loader.config_group"]:
            self.window.ui.nodes["dialog.url.loader.config_group"][value].show()

        # show/hide label if config are available
        self.window.ui.nodes["dialog.url.config.label"].hide()
        self.window.ui.nodes["dialog.url.config.help"].hide()
        if value in self.window.ui.nodes["dialog.url.loader.config_group"]:
            self.window.ui.nodes["dialog.url.config.label"].show()
            self.window.ui.nodes["dialog.url.config.help"].show()

        self.params_widget.adjustSize()
        self.params_scroll.update()
