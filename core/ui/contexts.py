#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget

from core.ui.widgets import ContextSelectMenu
from core.utils import trans


class Contexts:
    def __init__(self, window=None):
        """
        Contexts UI

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """
        Setups contexts list

        :return: QVBoxLayout
        """
        # contexts
        contexts = self.setup_contexts()
        self.window.models['ctx.contexts'] = self.create_model(self.window)
        self.window.data['ctx.contexts'].setModel(self.window.models['ctx.contexts'])
        self.window.data['ctx.contexts'].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.context.selection_change())

        ctx_widget = QWidget()
        ctx_widget.setLayout(contexts)
        ctx_widget.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addWidget(ctx_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        return layout

    def setup_contexts(self):
        """
        Setups contexts list

        :return: QVBoxLayout
        """
        id = 'ctx.contexts'
        self.window.data['contexts.new'] = QPushButton(trans('context.new'))
        self.window.data['contexts.new'].clicked.connect(
            lambda: self.window.controller.context.new())

        self.window.data[id] = ContextSelectMenu(self.window, id)
        self.window.data['contexts.label'] = QLabel(trans("ctx.contexts.label"))
        self.window.data['contexts.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        layout = QVBoxLayout()
        layout.addWidget(self.window.data['contexts.label'])
        layout.addWidget(self.window.data[id])
        layout.addWidget(self.window.data['contexts.new'])

        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])
        return layout

    def create_model(self, parent):
        """
        Creates list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 1, parent)
        return model

    def update_list(self, id, data):
        """
        Updates list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.models[id].removeRows(0, self.window.models[id].rowCount())
        i = 0
        for n in data:
            if 'name' in data[n] and 'date' in data[n]:
                self.window.models[id].insertRow(i)
                name = data[n]['name'] + ' (' + data[n]['date'] + ')'
                self.window.models[id].setData(self.window.models[id].index(i, 0), name)
                i += 1
