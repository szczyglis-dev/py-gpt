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
from typing import Dict, Tuple, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.option.input import OptionInput


class Loaders:
    def __init__(self, window=None):
        """
        UI - loaders components

        :param window: Window instance
        """
        self.window = window

    def handle_options(
            self,
            select_loader,
            prefix_options,
            prefix_config
    ) -> Tuple[bool, Optional[str], Dict[str, Any], Dict[str, Any]]:
        """
        Handle options

        :param select_loader: loader selection
        :param prefix_options: prefix for options
        :param prefix_config: prefix for config
        :return: bool, loader name, input_params, input_config
        """
        input_params = {}
        input_config = {}
        loader = select_loader.get_value()
        if not loader:
            return False, loader, input_params, input_config
        loaders = self.window.core.idx.indexing.get_external_instructions()
        if loader in loaders:
            params = loaders[loader]
            for k in params["args"]:
                key_path = prefix_options + "." + loader + "." + k
                if key_path in self.window.ui.nodes:
                    tmp_value = self.window.ui.nodes[key_path].text()
                    type = params["args"][k]["type"]
                    try:
                        if tmp_value:
                            if type == "int":
                                tmp_value = int(tmp_value)
                            elif type == "float":
                                tmp_value = float(tmp_value)
                            elif type == "bool":
                                if tmp_value.lower() in ["true", "1"]:
                                    tmp_value = True
                                else:
                                    tmp_value = False
                            elif type == "list":
                                tmp_value = tmp_value.split(",")
                            elif type == "dict":
                                tmp_value = json.loads(tmp_value)
                            input_params[k] = tmp_value
                    except Exception as e:
                        self.window.core.debug.log(e)
                        self.window.ui.dialogs.alert(e)

        loaders = self.window.core.idx.indexing.get_external_config()
        if loader in loaders:
            params = loaders[loader]
            for k in params:
                key_path = prefix_config + "." + loader + "." + k
                type = params[k]["type"]
                if key_path in self.window.ui.nodes:
                    tmp_value = self.window.ui.nodes[key_path].text()
                    try:
                        if tmp_value:
                            if type == "int":
                                tmp_value = int(tmp_value)
                            elif type == "float":
                                tmp_value = float(tmp_value)
                            elif type == "bool":
                                if tmp_value.lower() in ["true", "1"]:
                                    tmp_value = True
                                else:
                                    tmp_value = False
                            elif type == "list":
                                tmp_value = tmp_value.split(",")
                            elif type == "dict":
                                tmp_value = json.loads(tmp_value)
                            input_config[k] = tmp_value
                    except Exception as e:
                        self.window.core.debug.log(e)
                        self.window.ui.dialogs.alert(e)

        return True, loader, input_params, input_config

    def setup_loader_options(self):
        """Setup loader options"""
        inputs = {}
        groups = {}
        loaders = self.window.core.idx.indexing.get_external_instructions()
        for loader in loaders:
            params = loaders[loader]
            inputs[loader] = {}
            group = QVBoxLayout()
            for k in params["args"]:
                label = k
                description = None
                is_label = False
                if "label" in params["args"][k]:
                    label = params["args"][k]["label"]
                    is_label = True
                if "description" in params["args"][k]:
                    description = params["args"][k]["description"]
                option_id = "web.loader." + loader + ".option." + k
                option_widget = OptionInput(self.window, "tool.indexer", option_id, {
                    "label": label,
                    "value": "",
                })
                option_widget.setPlaceholderText(params["args"][k]["type"])
                inputs[loader][k] = option_widget

                option_label = QLabel(label)
                option_label.setToolTip(k)

                row = QHBoxLayout()  # cols
                row.addWidget(option_label)
                row.addWidget(option_widget)
                row.setContentsMargins(5, 0, 5, 0)

                option_layout = QVBoxLayout()
                option_layout.addLayout(row)
                if description:
                    option_layout.addWidget(HelpLabel(description))

                option_layout.setContentsMargins(5, 0, 0, 0)

                group.addLayout(option_layout)
                group.setContentsMargins(0, 0, 0, 0)

            group_widget = QWidget()
            group_widget.setLayout(group)
            groups[loader] = group_widget

        return inputs, groups

    def setup_loader_config(self):
        """Setup loader config"""
        inputs = {}
        groups = {}
        loaders = self.window.core.idx.indexing.get_external_config()
        for loader in loaders:
            params = loaders[loader]
            inputs[loader] = {}
            group = QVBoxLayout()
            for k in params:
                label = k
                description = None
                is_label = False
                if "label" in params[k]:
                    label = params[k]["label"]
                    is_label = True
                if "description" in params[k]:
                    description = params[k]["description"]
                option_id = "web.loader." + loader + ".config." + k
                option_widget = OptionInput(self.window, "tool.indexer", option_id, {
                    "label": label,
                    "value": params[k]["value"],
                })
                try:
                    if params[k]["value"] is not None:
                        if params[k]["type"] == "list" and isinstance(params[k]["value"], list):
                            option_widget.setText(", ".join(params[k]["value"]))
                        elif params[k]["type"] == "dict" and isinstance(params[k]["value"], dict):
                            option_widget.setText(json.dumps(params[k]["value"]))
                        else:
                            option_widget.setText(str(params[k]["value"]))
                except Exception as e:
                    self.window.core.debug.log(e)

                option_widget.setPlaceholderText(params[k]["type"])
                inputs[loader][k] = option_widget

                option_label = QLabel(label)
                option_label.setToolTip(k)

                row = QHBoxLayout()  # cols
                row.addWidget(option_label)
                row.addWidget(option_widget)
                row.setContentsMargins(5, 0, 5, 0)

                option_layout = QVBoxLayout()
                option_layout.addLayout(row)
                if description:
                    option_layout.addWidget(HelpLabel(description))

                option_layout.setContentsMargins(5, 0, 0, 0)

                group.addLayout(option_layout)
                group.setContentsMargins(0, 0, 0, 0)

            group_widget = QWidget()
            group_widget.setLayout(group)
            groups[loader] = group_widget

        return inputs, groups