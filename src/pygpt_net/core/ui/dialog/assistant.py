#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy

from ..widget.settings import SettingsTextarea, SettingsInput, SettingsCheckbox, SettingsDict
from ..widget.dialog.editor import EditorDialog
from ...utils import trans


class Assistant:
    def __init__(self, window=None):
        """
        Assistant editor dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setups assistant editor dialog"""
        id = "assistants"
        path = self.window.config.path
        self.window.ui.nodes['assistant.btn.save'] = QPushButton(trans("dialog.assistant.btn.save"))
        self.window.ui.nodes['assistant.btn.save'].clicked.connect(
            lambda: self.window.controller.assistant.save())
        self.window.ui.nodes['assistant.btn.save'].setAutoDefault(True)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['assistant.btn.save'])
        section = 'assistant.editor'  # prevent autoupdate current assistant
        func_keys = {
            'name': 'text',
            'params': 'text',
            'desc': 'text',
        }
        func_values = {}

        # fields
        self.window.ui.paths[id] = QLabel(str(path))
        self.window.ui.config_option['assistant.id'] = SettingsInput(self.window, 'assistant.id', False, section)
        self.window.ui.config_option['assistant.name'] = SettingsInput(self.window, 'assistant.name', False, section)
        self.window.ui.config_option['assistant.instructions'] = SettingsTextarea(self.window, 'assistant.instructions',
                                                                               False, section)
        self.window.ui.config_option['assistant.instructions'].setMinimumHeight(150)

        self.window.ui.config_option['assistant.model'] = SettingsInput(self.window, 'assistant.model', False, section)
        self.window.ui.config_option['assistant.description'] = SettingsInput(self.window, 'assistant.description', False,
                                                                           section)
        self.window.ui.config_option['assistant.tool.code_interpreter'] = SettingsCheckbox(self.window,
                                                                                        'assistant.tool.code_interpreter',
                                                                                        trans(
                                                                                            'assistant.tool.code_interpreter'),
                                                                                        False, section)
        self.window.ui.config_option['assistant.tool.code_interpreter'].box.setChecked(True)  # default True
        self.window.ui.config_option['assistant.tool.retrieval'] = SettingsCheckbox(self.window,
                                                                                 'assistant.tool.retrieval',
                                                                                 trans('assistant.tool.retrieval'),
                                                                                 False, section)
        self.window.ui.config_option['assistant.tool.retrieval'].box.setChecked(True)  # default True

        self.window.ui.config_option['assistant.tool.function'] = SettingsDict(self.window, 'assistant.tool.function',
                                                                            True, section, id,
                                                                            func_keys,
                                                                            func_values)
        self.window.ui.config_option['assistant.tool.function'].setMinimumHeight(150)
        self.window.ui.config_option['assistant.tool.function'].add_btn.setText(trans('assistant.func.add'))
        # Empty params: {"type": "object", "properties": {}}

        self.window.ui.nodes['assistant.id_tip'] = QLabel(trans('assistant.new.id_tip'))
        self.window.ui.nodes['assistant.id_tip'].setMinimumHeight(40)

        self.window.ui.nodes['assistant.api.tip'] = QPushButton(trans('assistant.api.tip'))
        self.window.ui.nodes['assistant.api.tip'].setAutoDefault(False)

        # make button look like a label:
        self.window.ui.nodes['assistant.api.tip'].setFlat(True)
        self.window.ui.nodes['assistant.api.tip'].setStyleSheet("text-align: left; color: #fff; text-decoration: "
                                                            "underline; text-transform: none;")
        # disable CSS text capitalize, only small letters:
        self.window.ui.nodes['assistant.api.tip'].setStyleSheet("text-transform: none;")
        self.window.ui.nodes['assistant.api.tip'].setCursor(Qt.PointingHandCursor)
        self.window.ui.nodes['assistant.api.tip'].clicked.connect(
            lambda: self.window.controller.assistant.goto_online())

        options = {}
        options['id'] = self.add_option('assistant.id', self.window.ui.config_option['assistant.id'])
        options['name'] = self.add_option('assistant.name', self.window.ui.config_option['assistant.name'])
        options['model'] = self.add_option('assistant.model', self.window.ui.config_option['assistant.model'])
        options['description'] = self.add_option('assistant.description',
                                                 self.window.ui.config_option['assistant.description'])
        options['tool.code_interpreter'] = self.add_raw_option(
            self.window.ui.config_option['assistant.tool.code_interpreter'])
        options['tool.retrieval'] = self.add_raw_option(self.window.ui.config_option['assistant.tool.retrieval'])
        options['tool.function'] = self.add_raw_option(self.window.ui.config_option['assistant.tool.function'])

        self.window.ui.nodes['assistant.instructions.label'] = QLabel(trans('assistant.instructions'))
        options['instructions'] = QVBoxLayout()
        options['instructions'].addWidget(self.window.ui.nodes['assistant.instructions.label'])
        options['instructions'].addWidget(self.window.ui.config_option['assistant.instructions'])

        self.window.ui.nodes['assistant.functions.label'] = QLabel(trans('assistant.functions.label'))
        self.window.ui.nodes['assistant.functions.label'].setMinimumHeight(30)

        rows = QVBoxLayout()
        rows.addLayout(options['id'])
        rows.addWidget(self.window.ui.nodes['assistant.id_tip'])
        rows.addLayout(options['name'])
        rows.addLayout(options['model'])
        rows.addLayout(options['description'])
        rows.addLayout(options['tool.code_interpreter'])
        rows.addLayout(options['tool.retrieval'])
        rows.addWidget(self.window.ui.nodes['assistant.functions.label'])
        rows.addLayout(options['tool.function'])
        rows.addLayout(options['instructions'])
        rows.addWidget(self.window.ui.nodes['assistant.api.tip'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(bottom_layout)
        layout.setStretch(1, 1)

        self.window.ui.dialog['editor.' + id] = EditorDialog(self.window, id)
        self.window.ui.dialog['editor.' + id].setLayout(layout)
        self.window.ui.dialog['editor.' + id].setWindowTitle(trans('dialog.assistant'))

    def add_option(self, title, option, bold=False):
        """
        Add option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        """
        option.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        label_key = title + '.label'
        self.window.ui.nodes[label_key] = QLabel(trans(title))
        self.window.ui.nodes[label_key].setMaximumWidth(120)
        if bold:
            self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.ui.nodes[label_key].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(option)
        layout.setStretch(0, 1)
        return layout

    def add_raw_option(self, option):
        """
        Add raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
