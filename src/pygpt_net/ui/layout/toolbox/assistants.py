#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget

from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.lists.assistant import AssistantList
from pygpt_net.utils import trans

class Assistants:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'assistants'

    def setup(self) -> QWidget:
        """
        Setup assistants

        :return: QWidget
        """
        layout = self.setup_assistants()

        self.window.ui.nodes['assistants.widget'] = QWidget()
        self.window.ui.nodes['assistants.widget'].setLayout(layout)
        self.window.ui.nodes['assistants.widget'].setMinimumHeight(180)

        return self.window.ui.nodes['assistants.widget']

    def setup_assistants(self) -> QVBoxLayout:
        """
        Setup list of assistants

        :return: QVBoxLayout
        """
        nodes = self.window.ui.nodes
        ctrl = self.window.controller

        # new
        nodes['assistants.new'] = QPushButton(QIcon(":/icons/add.svg"), "")
        _cb_new = ctrl.assistant.editor.edit
        nodes['assistants.new'].clicked.connect(lambda checked=False, cb=_cb_new: cb())

        # import
        nodes['assistants.import'] = QPushButton(trans('assistant.import'))
        _cb_import = ctrl.assistant.batch.import_assistants
        nodes['assistants.import'].clicked.connect(lambda checked=False, cb=_cb_import: cb())

        # label
        nodes['assistants.label'] = TitleLabel(trans("toolbox.assistants.label"))

        # header
        header = QHBoxLayout()
        header.addWidget(nodes['assistants.label'])
        header.addStretch(1)
        header.addWidget(nodes['assistants.new'], alignment=Qt.AlignRight)
        header.addWidget(nodes['assistants.import'], alignment=Qt.AlignRight)
        header.setContentsMargins(5, 0, 0, 0)
        header_widget = QWidget()
        header_widget.setLayout(header)

        # list
        nodes[self.id] = AssistantList(self.window, self.id)
        nodes[self.id].selection_locked = ctrl.assistant.change_locked
        nodes[self.id].setMinimumWidth(40)

        nodes['tip.toolbox.assistants'] = HelpLabel(trans('tip.toolbox.assistants'), self.window)
        nodes['tip.toolbox.assistants'].setAlignment(Qt.AlignCenter)

        # rows
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(nodes[self.id])
        layout.addWidget(nodes['tip.toolbox.assistants'])
        layout.setContentsMargins(2, 5, 5, 5)

        # model
        self.window.ui.models[self.id] = self.create_model(nodes[self.id])
        nodes[self.id].setModel(self.window.ui.models[self.id])

        return layout

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update(self, data):
        """
        Update list of assistants

        :param data: Data to update
        """
        view = self.window.ui.nodes[self.id]
        model = self.window.ui.models[self.id]

        view.backup_selection()
        view.setUpdatesEnabled(False)
        try:
            with QtCore.QSignalBlocker(model):
                model.setRowCount(0)
                count = len(data)
                if count:
                    model.setRowCount(count)
                    for i, item in enumerate(data.values()):
                        index = model.index(i, 0)
                        model.setData(index, "ID: " + item.id, QtCore.Qt.ToolTipRole)
                        model.setData(index, item.name)
        finally:
            view.setUpdatesEnabled(True)

        view.restore_selection()