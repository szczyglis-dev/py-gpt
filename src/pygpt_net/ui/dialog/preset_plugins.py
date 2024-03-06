#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout

from pygpt_net.ui.widget.dialog.preset_plugins import PresetPluginsDialog
from pygpt_net.ui.widget.lists.preset_plugins import PresetPluginsList
from pygpt_net.utils import trans


class PresetPlugins:
    def __init__(self, window=None):
        """
        Plugins presets editor dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "preset.plugins.editor"

    def setup(self):
        """Setup presets editor dialog"""
        self.window.ui.nodes['plugin.presets.editor.btn.new'] = \
            QPushButton(trans("preset.new"))

        """
        self.window.ui.nodes['models.editor.btn.save'] = \
            QPushButton(trans("plugin.presets.editor.btn.save"))
        """

        self.window.ui.nodes['plugin.presets.editor.btn.new'].clicked.connect(
            lambda: self.window.controller.plugins.presets.new())

        """
        self.window.ui.nodes['plugin.presets.editor.btn.save'].clicked.connect(
            lambda: self.window.controller.plugins.presets.save_editor())
        """

        # set enter key to save button
        self.window.ui.nodes['plugin.presets.editor.btn.new'].setAutoDefault(False)
        # self.window.ui.nodes['plugin.presets.editor.btn.save'].setAutoDefault(True)

        # footer buttons
        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['plugin.presets.editor.btn.new'])
        # footer.addWidget(self.window.ui.nodes['plugin.presets.editor.btn.save'])

        # presets list
        id = 'preset.plugins.list'
        self.window.ui.nodes[id] = PresetPluginsList(self.window, id)
        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        # get presets
        data = self.window.controller.plugins.presets.get_presets()

        # update models list
        self.update_list(id, data)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.ui.nodes[id])

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list
        layout.addLayout(footer)  # bottom buttons (save, new)

        self.window.ui.dialog[self.dialog_id] = PresetPluginsDialog(self.window, self.dialog_id)
        self.window.ui.dialog[self.dialog_id].setLayout(layout)
        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.preset.plugins.editor'))

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update_list(self, id: str, data: dict):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        if id not in self.window.ui.models:
            return

        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n]['name']
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
