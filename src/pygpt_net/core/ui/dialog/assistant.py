#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from ..widgets import SettingsTextarea, SettingsInput, SettingsCheckbox, EditorDialog
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
        self.window.config_option['assistant.tool.function'] = SettingsCheckbox(self.window, 'assistant.tool.function',
                                                                      trans('assistant.tool.function'), False, section)

        # set max width
        max_width = 240
        self.window.config_option['assistant.id'].setMaximumWidth(max_width)
        self.window.config_option['assistant.name'].setMaximumWidth(max_width)
        self.window.config_option['assistant.model'].setMaximumWidth(max_width)
        self.window.config_option['assistant.description'].setMaximumWidth(max_width)

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

        rows = QVBoxLayout()
        rows.addLayout(options['id'])
        rows.addLayout(options['name'])
        rows.addLayout(options['model'])
        rows.addLayout(options['description'])
        rows.addLayout(options['tool.code_interpreter'])
        rows.addLayout(options['tool.retrieval'])
        rows.addLayout(options['tool.function'])
        rows.addLayout(options['instructions'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(bottom_layout)

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
        label_key = title + '.label'
        self.window.data[label_key] = QLabel(trans(title))
        if bold:
            self.window.data[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        layout = QHBoxLayout()
        layout.addWidget(self.window.data[label_key])
        layout.addWidget(option)

        return layout

    def add_raw_option(self, option):
        """
        Adds raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
