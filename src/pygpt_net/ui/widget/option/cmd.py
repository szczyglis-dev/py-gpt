#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.24 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans

import pygpt_net.icons_rc


class OptionCmd(QWidget):
    def __init__(
            self,
            window=None,
            plugin: BasePlugin = None,
            parent_id: str = None,
            id: str = None,
            option: dict = None
    ):
        """
        Command dictionary option widget

        :param window: main window
        :param plugin: plugin instance
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCmd, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option  # option data

        # TODO: implement cmd type option
        # print(self.option)

        key = option['id']
        cmd_id = option['id'].replace("cmd.", "")
        txt_desc = option['description']
        txt_tooltip = option['tooltip']

        # locale
        if plugin.use_locale:
            domain = 'plugin.' + plugin.id
            txt_desc = trans(key + '.description', False, domain)
            txt_tooltip = trans(key + '.tooltip', False, domain)
            # check if translation exists
            if txt_desc == key + '.description':
                txt_desc = trans("settings.cmd.field.desc").format(cmd=cmd_id)
            if txt_tooltip == key + '.tooltip':
                txt_tooltip = trans("settings.cmd.field.tooltip").format(cmd=cmd_id)

        # enable
        option_enabled = {}
        option_enabled["type"] = "bool"
        option_enabled["label"] = trans("settings.cmd.field.enable").format(cmd=cmd_id)
        option_enabled["description"] = ""
        option_enabled["value"] = True

        # params
        option_params = {}
        option_params["name"] = "params"
        option_params["type"] = "dict"
        option_params["keys"] = self.option["params_keys"]
        option_params["value"] = []
        if self.option["value"] is not None and "params" in self.option["value"]:
            option_params["value"] = self.option["value"]["params"]
        option_params["tooltip"] = ""

        # instruction
        option_instruction = {}
        option_instruction["type"] = "textarea"
        option_instruction["label"] = "Instruction"
        option_instruction["value"] = ""

        # keys
        key_enabled = self.id + ".enabled"
        key_params = self.id + ".params"
        key_instruction = self.id + ".instruction"

        label_key = self.parent_id + '.' + id + '.label'
        desc_key = self.parent_id + '.' + id + '.desc'

        self.window.ui.nodes[desc_key] = QLabel(txt_desc)
        self.window.ui.nodes[desc_key].setWordWrap(True)
        self.window.ui.nodes[desc_key].setMaximumHeight(40)
        self.window.ui.nodes[desc_key].setStyleSheet("font-size: 10px;")
        self.window.ui.nodes[desc_key].setProperty('class', 'label-help')
        self.window.ui.nodes[desc_key].setContentsMargins(35, 0, 0, 0)

        instr_key = "settings.cmd.field.instruction"
        params_key = "settings.cmd.field.params"
        instr_label = QLabel(trans(instr_key))
        params_label = QLabel(trans(params_key))

        # widgets
        self.enabled = OptionCheckbox(self.window, parent_id, key_enabled, option_enabled, icon = ":/icons/build.svg")  # enable checkbox
        self.params = OptionDict(self.window, parent_id, key_params, option_params)  # command params
        self.instruction = OptionTextarea(self.window, parent_id, key_instruction, option_instruction)  # command instruction

        # layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.enabled)
        self.layout.addWidget(self.window.ui.nodes[desc_key])

        params_layout = QVBoxLayout()
        params_layout.addWidget(instr_label)
        params_layout.addWidget(self.instruction)
        params_layout.addWidget(params_label)
        params_layout.addWidget(self.params)

        group_id = self.parent_id + '.' + id + '.config'
        group = CollapsedGroup(self.window, group_id, None, False, None)
        group.box.setText(trans('settings.cmd.config.collapse'))
        group.box.setIcon(QIcon(":/icons/expand.svg"))
        group.add_layout(params_layout)
        group.layout.setContentsMargins(25, 0, 0, 0)

        # add to groups
        self.window.ui.groups[group_id] = group

        self.layout.addWidget(group)
        self.setLayout(self.layout)

        # show tooltip only if different from description
        # if txt_tooltip != txt_desc:
            # self.setToolTip(txt_tooltip)

        # update
        self.update()

    def update_item(self, idx, data):
        """
        Update item in params list

        :param idx: Item index
        :param data: Item data
        """
        self.params.update_item(idx, data)

    def update(self):
        """Update widget"""
        pass