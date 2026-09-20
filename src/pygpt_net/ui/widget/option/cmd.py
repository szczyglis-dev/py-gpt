#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.15 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.element.labels import DescLabel
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.tool_info import ToolInfo
from pygpt_net.utils import trans


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
        Tool option widget. Only the enabled state is editable; the tool
        instruction and parameter schema are read-only metadata defined by
        the plugin itself.

        :param window: main window
        :param plugin: plugin instance
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCmd, self).__init__(window)
        self.window = window
        self.plugin = plugin
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.cmd_id = option['id'].replace("cmd.", "")

        # enable checkbox - this is the only editable field for a tool
        option_enabled = {
            "type": "bool",
            "label": "",
            "description": "",
            "value": True,
        }
        key_enabled = self.id + ".enabled"
        self.enabled = OptionCheckbox(
            self.window,
            parent_id,
            key_enabled,
            option_enabled,
            icon=":/icons/build.svg",
        )

        # description
        desc_key = self.parent_id + '.' + id + '.desc'
        self.window.ui.nodes[desc_key] = DescLabel("", self.window)
        self.window.ui.nodes[desc_key].setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.window.ui.nodes[desc_key].setWordWrap(True)
        self.window.ui.nodes[desc_key].setMaximumHeight(40)
        self.window.ui.nodes[desc_key].setContentsMargins(35, 0, 0, 0)
        self.desc_key = desc_key

        # read-only tool definition (no input fields / dictionaries)
        self.info = ToolInfo(self.window, self.option)

        group_id = self.parent_id + '.' + id + '.config'
        self.group = CollapsedGroup(self.window, group_id, None, False, None)
        self.group.box.setIcon(QIcon(":/icons/expand.svg"))
        self.group.add_widget(self.info)
        self.group.layout.setContentsMargins(25, 0, 0, 0)
        self.window.ui.groups[group_id] = self.group

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.enabled)
        self.layout.addWidget(self.window.ui.nodes[desc_key])
        self.layout.addWidget(self.group)
        self.setLayout(self.layout)

        self.update_locale()

    def _description(self) -> str:
        """Return localized tool description with a generic fallback."""
        txt_desc = self.option.get('description', '')
        key = self.option['id']
        if self.plugin.use_locale:
            domain = 'plugin.' + self.plugin.id
            translated = trans(key + '.description', False, domain)
            if translated != key + '.description':
                txt_desc = translated
            elif not txt_desc:
                txt_desc = trans("settings.cmd.field.desc").format(cmd=self.cmd_id)
        return txt_desc

    def update_locale(self):
        """Refresh generic and plugin-specific translated texts."""
        self.enabled.setText(trans("settings.cmd.field.enable").format(cmd=self.cmd_id))
        self.window.ui.nodes[self.desc_key].setText(self._description())
        self.group.box.setText(trans('settings.cmd.config.collapse'))
        self.info.update_locale()

    def update_item(self, idx, data):
        """Compatibility no-op: tool parameters are read-only."""
        return

    def update(self):
        """Refresh widget locale-dependent content."""
        self.update_locale()
