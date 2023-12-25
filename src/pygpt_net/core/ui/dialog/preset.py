#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from pygpt_net.core.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.core.ui.widget.option.input import OptionInput
from pygpt_net.core.ui.widget.option.slider import OptionSlider
from pygpt_net.core.ui.widget.option.textarea import OptionTextarea
from pygpt_net.core.ui.widget.dialog.editor import EditorDialog
from pygpt_net.core.utils import trans


class Preset:
    def __init__(self, window=None):
        """
        Preset editor dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup preset editor dialog"""

        id = "preset.presets"
        path = self.window.app.config.path

        self.window.ui.nodes['preset.btn.current'] = QPushButton(trans("dialog.preset.btn.current"))
        self.window.ui.nodes['preset.btn.save'] = QPushButton(trans("dialog.preset.btn.save"))
        self.window.ui.nodes['preset.btn.current'].clicked.connect(
            lambda: self.window.controller.presets.from_current())
        self.window.ui.nodes['preset.btn.save'].clicked.connect(
            lambda: self.window.controller.presets.save())

        self.window.ui.nodes['preset.btn.current'].setAutoDefault(False)
        self.window.ui.nodes['preset.btn.save'].setAutoDefault(True)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['preset.btn.current'])
        bottom_layout.addWidget(self.window.ui.nodes['preset.btn.save'])

        section = 'preset.editor'  # prevent autoupdate current preset

        # fields
        self.window.ui.paths[id] = QLabel(str(path))
        self.window.ui.config_option['preset.prompt'] = OptionTextarea(self.window, 'preset.prompt', False, section)
        self.window.ui.config_option['preset.filename'] = OptionInput(self.window, 'preset.filename', False, section)
        self.window.ui.config_option['preset.name'] = OptionInput(self.window, 'preset.name', False, section)
        self.window.ui.config_option['preset.ai_name'] = OptionInput(self.window, 'preset.ai_name', False, section)
        self.window.ui.config_option['preset.user_name'] = OptionInput(self.window, 'preset.user_name', False, section)
        self.window.ui.config_option['preset.img'] = OptionCheckbox(self.window, 'preset.img',
                                                                    trans('preset.img'), False, section)
        self.window.ui.config_option['preset.chat'] = OptionCheckbox(self.window, 'preset.chat', trans('preset.chat'),
                                                                     False, section)
        self.window.ui.config_option['preset.completion'] = OptionCheckbox(self.window, 'preset.completion',
                                                                           trans('preset.completion'), False, section)
        self.window.ui.config_option['preset.vision'] = OptionCheckbox(self.window, 'preset.vision',
                                                                       trans('preset.vision'), False, section)
        self.window.ui.config_option['preset.langchain'] = OptionCheckbox(self.window, 'preset.langchain',
                                                                          trans('preset.langchain'), False, section)
        self.window.ui.config_option['preset.assistant'] = OptionCheckbox(self.window, 'preset.assistant',
                                                                          trans('preset.assistant'), False, section)
        self.window.ui.config_option['preset.temperature'] = OptionSlider(self.window, 'preset.temperature',
                                                                          '', 0, 200,
                                                                          1, 100, True, section)

        # set max width
        max_width = 240
        self.window.ui.config_option['preset.filename'].setMaximumWidth(max_width)
        self.window.ui.config_option['preset.name'].setMaximumWidth(max_width)
        self.window.ui.config_option['preset.ai_name'].setMaximumWidth(max_width)
        self.window.ui.config_option['preset.user_name'].setMaximumWidth(max_width)

        options = {}
        options['filename'] = self.add_option('preset.filename', self.window.ui.config_option['preset.filename'])
        options['name'] = self.add_option('preset.name', self.window.ui.config_option['preset.name'])
        options['ai_name'] = self.add_option('preset.ai_name', self.window.ui.config_option['preset.ai_name'])
        options['user_name'] = self.add_option('preset.user_name', self.window.ui.config_option['preset.user_name'])
        options['chat'] = self.add_raw_option(self.window.ui.config_option['preset.chat'])
        options['completion'] = self.add_raw_option(self.window.ui.config_option['preset.completion'])
        options['vision'] = self.add_raw_option(self.window.ui.config_option['preset.vision'])
        options['assistant'] = self.add_raw_option(self.window.ui.config_option['preset.assistant'])
        options['langchain'] = self.add_raw_option(self.window.ui.config_option['preset.langchain'])
        options['img'] = self.add_raw_option(self.window.ui.config_option['preset.img'])
        options['temperature'] = self.add_option('preset.temperature',
                                                 self.window.ui.config_option['preset.temperature'])

        self.window.ui.config_option['preset.prompt'].setMinimumHeight(150)

        self.window.ui.nodes['preset.prompt.label'] = QLabel(trans('preset.prompt'))
        options['prompt'] = QVBoxLayout()
        options['prompt'].addWidget(self.window.ui.nodes['preset.prompt.label'])
        options['prompt'].addWidget(self.window.ui.config_option['preset.prompt'])

        rows = QVBoxLayout()
        rows.addLayout(options['filename'])
        rows.addLayout(options['name'])
        rows.addLayout(options['ai_name'])
        rows.addLayout(options['user_name'])
        rows.addLayout(options['chat'])
        rows.addLayout(options['completion'])
        rows.addLayout(options['img'])
        rows.addLayout(options['vision'])
        rows.addLayout(options['assistant'])
        rows.addLayout(options['langchain'])
        rows.addLayout(options['temperature'])
        rows.addLayout(options['prompt'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['editor.' + id] = EditorDialog(self.window, id)
        self.window.ui.dialog['editor.' + id].setLayout(layout)
        self.window.ui.dialog['editor.' + id].setWindowTitle(trans('dialog.preset'))

    def add_option(self, title, option, bold=False):
        """
        Add option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        """
        label_key = title + '.label'
        self.window.ui.nodes[label_key] = QLabel(trans(title))
        if bold:
            self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(option)

        return layout

    def add_raw_option(self, option):
        """
        Add raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
