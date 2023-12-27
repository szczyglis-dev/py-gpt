#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSplitter, QWidget

from pygpt_net.ui.widget.lists.preset import PresetList
from pygpt_net.ui.layout.toolbox.footer import Footer
from pygpt_net.utils import trans


class Presets:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.footer = Footer(window)
        self.id = 'preset.presets'

    def setup(self):
        """
        Setup presets

        :return: QSplitter
        :rtype: QSplitter
        """
        presets = self.setup_presets()

        self.window.ui.models['preset.presets'] = self.create_model(self.window)
        self.window.ui.nodes['preset.presets'].setModel(self.window.ui.models['preset.presets'])

        self.window.ui.nodes['presets.widget'] = QWidget()
        self.window.ui.nodes['presets.widget'].setLayout(presets)
        self.window.ui.nodes['presets.widget'].setMinimumHeight(150)

        return self.window.ui.nodes['presets.widget']

    def setup_presets(self,):
        """
        Setup list

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        self.window.ui.nodes['preset.presets.new'] = QPushButton(trans('preset.new'))
        self.window.ui.nodes['preset.presets.new'].clicked.connect(
            lambda: self.window.controller.presets.editor.edit())

        self.window.ui.nodes['preset.presets.label'] = QLabel(trans("toolbox.presets.label"))
        self.window.ui.nodes['preset.presets.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['preset.presets.label'])
        header.addWidget(self.window.ui.nodes['preset.presets.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(0, 0, 0, 0)

        header_widget = QWidget()
        header_widget.setLayout(header)

        self.window.ui.nodes[self.id] = PresetList(self.window, self.id)
        self.window.ui.nodes[self.id].selection_locked = self.window.controller.presets.preset_change_locked

        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[self.id])

        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

        return layout

    def create_model(self, parent):
        """
        Create list model
        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        # store previous selection
        self.window.ui.nodes[self.id].backup_selection()
        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[self.id].insertRow(i)
            name = data[n].name
            if not n.startswith('current.'):
                name = data[n].name + ' (' + str(n) + ')'
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), name)
            i += 1

        # restore previous selection
        self.window.ui.nodes[self.id].restore_selection()
