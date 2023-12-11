#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.11 23:00:00                  #
# ================================================== #
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy

from ..widget.settings import SettingsTextarea, SettingsInput, SettingsCheckbox, SettingsDict
from ..widget.dialog import EditorDialog
from ...utils import trans


class Assistant:
    def __init__(self, window=None):
        """
        Assistant editor dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups assistant editor dialog"""

        id = "assistants"
        path = self.window.config.path

        self.window.data['assistant.btn.current'] = QPushButton(trans("dialog.assistant.btn.current"))
        self.window.data['assistant.btn.save'] = QPushButton(trans("dialog.assistant.btn.save"))
        self.window.data['assistant.btn.save'].clicked.connect(
            lambda: self.window.controller.assistant.save())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['assistant.btn.save'])

        section = 'assistant.editor'  # prevent autoupdate current assistant

        func_keys = {
            'name': 'text',
            'params': 'text',
            'desc': 'text',
        }
        func_values = {}

        # fields
        self.window.path_label[id] = QLabel(str(path))
        self.window.config_option['assistant.id'] = SettingsInput(self.window, 'assistant.id', False, section)
        self.window.config_option['assistant.name'] = SettingsInput(self.window, 'assistant.name', False, section)
        self.window.config_option['assistant.instructions'] = SettingsTextarea(self.window, 'assistant.instructions', False, section)

        self.window.config_option['assistant.model'] = SettingsInput(self.window, 'assistant.model', False, section)
        self.window.config_option['assistant.description'] = SettingsInput(self.window, 'assistant.description', False, section)
        self.window.config_option['assistant.tool.code_interpreter'] = SettingsCheckbox(self.window,
                                                                    'assistant.tool.code_interpreter',
                                                                    trans('assistant.tool.code_interpreter'),
                                                                    False, section)
        self.window.config_option['assistant.tool.retrieval'] = SettingsCheckbox(self.window, 'assistant.tool.retrieval',
                                                                          trans('assistant.tool.retrieval'), False, section)

        self.window.config_option['assistant.tool.function'] = SettingsDict(self.window, 'assistant.tool.function', True, section, id,
                                                          func_keys,
                                                          func_values)
        self.window.config_option['assistant.tool.function'].setMinimumHeight(150)
        # {"type": "object", "properties": {}}

        options = {}
        options['id'] = self.add_option('assistant.id', self.window.config_option['assistant.id'])
        options['name'] = self.add_option('assistant.name', self.window.config_option['assistant.name'])
        options['model'] = self.add_option('assistant.model', self.window.config_option['assistant.model'])
        options['description'] = self.add_option('assistant.description', self.window.config_option['assistant.description'])
        options['tool.code_interpreter'] = self.add_raw_option(self.window.config_option['assistant.tool.code_interpreter'])
        options['tool.retrieval'] = self.add_raw_option(self.window.config_option['assistant.tool.retrieval'])
        options['tool.function'] = self.add_raw_option(self.window.config_option['assistant.tool.function'])

        self.window.config_option['assistant.instructions'].setMinimumHeight(150)

        self.window.data['assistant.instructions.label'] = QLabel(trans('assistant.instructions'))
        options['instructions'] = QVBoxLayout()
        options['instructions'].addWidget(self.window.data['assistant.instructions.label'])
        options['instructions'].addWidget(self.window.config_option['assistant.instructions'])

        label_info = QLabel("TIP: Leave empty ID if creating new agent.")
        label_info.setMinimumHeight(40)

        label_func = QLabel("Functions")
        label_func.setMinimumHeight(40)

        # align: center
        label_info.setAlignment(Qt.AlignCenter)

        rows = QVBoxLayout()
        rows.addLayout(options['id'])
        rows.addLayout(options['name'])
        rows.addLayout(options['model'])
        rows.addLayout(options['description'])
        rows.addLayout(options['tool.code_interpreter'])
        rows.addLayout(options['tool.retrieval'])
        rows.addWidget(label_func)
        rows.addLayout(options['tool.function'])
        rows.addWidget(label_info)
        rows.addLayout(options['instructions'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(bottom_layout)
        layout.setStretch(1, 1)

        self.window.dialog['editor.' + id] = EditorDialog(self.window, id)
        self.window.dialog['editor.' + id].setLayout(layout)
        self.window.dialog['editor.' + id].setWindowTitle(trans('dialog.assistant'))

    def add_option(self, title, option, bold=False):
        """
        Adds option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        """
        option.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # this not works becose
        label_key = title + '.label'
        self.window.data[label_key] = QLabel(trans(title))
        self.window.data[label_key].setMaximumWidth(120)
        if bold:
            self.window.data[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.data[label_key].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        layout = QHBoxLayout()
        layout.addWidget(self.window.data[label_key])
        layout.addWidget(option)
        layout.setStretch(0, 1)

        return layout

    def add_raw_option(self, option):
        """
        Adds raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
