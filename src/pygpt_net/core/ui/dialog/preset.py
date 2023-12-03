#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.03 12:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from ..widgets import SettingsTextarea, SettingsInput, SettingsCheckbox, SettingsSlider, EditorDialog
from ...utils import trans


class Preset:
    def __init__(self, window=None):
        """
        Preset editor dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups preset editor dialog"""

        id = "preset.presets"
        path = self.window.config.path

        self.window.data['preset.btn.current'] = QPushButton(trans("dialog.preset.btn.current"))
        self.window.data['preset.btn.save'] = QPushButton(trans("dialog.preset.btn.save"))
        self.window.data['preset.btn.current'].clicked.connect(
            lambda: self.window.controller.presets.from_current())
        self.window.data['preset.btn.save'].clicked.connect(
            lambda: self.window.controller.presets.save())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['preset.btn.current'])
        bottom_layout.addWidget(self.window.data['preset.btn.save'])

        section = 'preset.editor'  # prevent autoupdate current preset

        # fields
        self.window.path_label[id] = QLabel(str(path))
        self.window.config_option['preset.prompt'] = SettingsTextarea(self.window, 'preset.prompt', False, section)
        self.window.config_option['preset.filename'] = SettingsInput(self.window, 'preset.filename', False, section)
        self.window.config_option['preset.name'] = SettingsInput(self.window, 'preset.name', False, section)
        self.window.config_option['preset.ai_name'] = SettingsInput(self.window, 'preset.ai_name', False, section)
        self.window.config_option['preset.user_name'] = SettingsInput(self.window, 'preset.user_name', False, section)
        self.window.config_option['preset.img'] = SettingsCheckbox(self.window, 'preset.img',
                                                                   trans('preset.img'), False, section)
        self.window.config_option['preset.chat'] = SettingsCheckbox(self.window, 'preset.chat', trans('preset.chat'),
                                                                    False, section)
        self.window.config_option['preset.completion'] = SettingsCheckbox(self.window, 'preset.completion',
                                                                          trans('preset.completion'), False, section)
        self.window.config_option['preset.vision'] = SettingsCheckbox(self.window, 'preset.vision',
                                                                      trans('preset.vision'), False, section)
        self.window.config_option['preset.temperature'] = SettingsSlider(self.window, 'preset.temperature',
                                                                         '', 0, 200,
                                                                         1, 100, True, section)

        # set max width
        max_width = 240
        self.window.config_option['preset.filename'].setMaximumWidth(max_width)
        self.window.config_option['preset.name'].setMaximumWidth(max_width)
        self.window.config_option['preset.ai_name'].setMaximumWidth(max_width)
        self.window.config_option['preset.user_name'].setMaximumWidth(max_width)

        options = {}
        options['filename'] = self.add_option('preset.filename', self.window.config_option['preset.filename'])
        options['name'] = self.add_option('preset.name', self.window.config_option['preset.name'])
        options['ai_name'] = self.add_option('preset.ai_name', self.window.config_option['preset.ai_name'])
        options['user_name'] = self.add_option('preset.user_name', self.window.config_option['preset.user_name'])
        options['chat'] = self.add_raw_option(self.window.config_option['preset.chat'])
        options['completion'] = self.add_raw_option(self.window.config_option['preset.completion'])
        options['vision'] = self.add_raw_option(self.window.config_option['preset.vision'])
        options['img'] = self.add_raw_option(self.window.config_option['preset.img'])
        options['temperature'] = self.add_option('preset.temperature', self.window.config_option['preset.temperature'])

        self.window.config_option['preset.prompt'].setMinimumHeight(150)

        self.window.data['preset.prompt.label'] = QLabel(trans('preset.prompt'))
        options['prompt'] = QVBoxLayout()
        options['prompt'].addWidget(self.window.data['preset.prompt.label'])
        options['prompt'].addWidget(self.window.config_option['preset.prompt'])

        rows = QVBoxLayout()
        rows.addLayout(options['filename'])
        rows.addLayout(options['name'])
        rows.addLayout(options['ai_name'])
        rows.addLayout(options['user_name'])
        rows.addLayout(options['chat'])
        rows.addLayout(options['completion'])
        rows.addLayout(options['img'])
        rows.addLayout(options['vision'])
        rows.addLayout(options['temperature'])
        rows.addLayout(options['prompt'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(bottom_layout)

        self.window.dialog['editor.' + id] = EditorDialog(self.window, id)
        self.window.dialog['editor.' + id].setLayout(layout)
        self.window.dialog['editor.' + id].setWindowTitle(trans('dialog.preset'))

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
