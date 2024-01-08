#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.08 17:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.utils import trans


class Preset:
    def __init__(self, window=None):
        """
        Preset editor dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "preset"

    def setup(self):
        """Setup preset editor dialog"""
        id = "preset.presets"

        self.window.ui.nodes['preset.btn.current'] = QPushButton(trans("dialog.preset.btn.current"))
        self.window.ui.nodes['preset.btn.save'] = QPushButton(trans("dialog.preset.btn.save"))
        self.window.ui.nodes['preset.btn.current'].clicked.connect(
            lambda: self.window.controller.presets.editor.from_current())
        self.window.ui.nodes['preset.btn.save'].clicked.connect(
            lambda: self.window.controller.presets.editor.save())

        self.window.ui.nodes['preset.btn.current'].setAutoDefault(False)
        self.window.ui.nodes['preset.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['preset.btn.current'])
        footer.addWidget(self.window.ui.nodes['preset.btn.save'])

        # fields
        self.window.ui.paths[id] = QLabel(str(self.window.core.config.path))

        # get option fields config
        fields = self.window.controller.presets.editor.get_options()

        # build settings widgets
        widgets = self.build_widgets(fields)

        # apply settings widgets
        for key in widgets:
            self.window.ui.config[self.id][key] = widgets[key]

        # fix max width
        max_width = 240
        self.window.ui.config[self.id]['filename'].setMaximumWidth(max_width)
        self.window.ui.config[self.id]['name'].setMaximumWidth(max_width)
        self.window.ui.config[self.id]['ai_name'].setMaximumWidth(max_width)
        self.window.ui.config[self.id]['user_name'].setMaximumWidth(max_width)

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if fields[key]["type"] == 'text' or fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                options[key] = self.add_raw_option(widgets[key])

        rows = QVBoxLayout()

        # append widgets options layouts to rows
        for key in options:
            rows.addLayout(options[key])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(footer)

        self.window.ui.dialog['editor.' + id] = EditorDialog(self.window, id)
        self.window.ui.dialog['editor.' + id].setLayout(layout)
        self.window.ui.dialog['editor.' + id].setWindowTitle(trans('dialog.preset'))

    def build_widgets(self, options) -> dict:
        """
        Build settings options widgets

        :param options: settings options
        """
        widgets = {}

        for key in options:
            option = options[key]

            # create widget by option type
            if option['type'] == 'text' or option['type'] == 'int' or option['type'] == 'float':
                if 'slider' in option and option['slider'] and (option['type'] == 'int' or option['type'] == 'float'):
                    widgets[key] = OptionSlider(self.window, self.id, key, option)  # slider + text input
                else:
                    if 'secret' in option and option['secret']:
                        widgets[key] = PasswordInput(self.window, self.id, key, option)  # password input
                    else:
                        widgets[key] = OptionInput(self.window, self.id, key, option)  # text input

            elif option['type'] == 'textarea':
                widgets[key] = OptionTextarea(self.window, self.id, key, option)  # textarea
                widgets[key].setMinimumHeight(150)
            elif option['type'] == 'bool':
                widgets[key] = OptionCheckbox(self.window, self.id, key, option)  # checkbox
            elif option['type'] == 'dict':
                widgets[key] = OptionDict(self.window, self.id, key, option)  # dictionary

        return widgets

    def add_option(self, widget, option) -> QHBoxLayout:
        """
        Add option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        """
        label = option['label']
        extra = {}
        if 'extra' in option:
            extra = option['extra']
        label_key = label + '.label'
        self.window.ui.nodes[label_key] = QLabel(trans(label))
        if 'bold' in extra and extra['bold']:
            self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)
        return layout

    def add_row_option(self, widget, option) -> QHBoxLayout:
        """
        Add option row (label + option)

        :param title: Title
        :param option: Option
        :param type: Option type
        :param extra: Extra params
        """
        label = option['label']
        label_key = label + '.label'
        self.window.ui.nodes[label_key] = QLabel(trans(label))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)
        return layout

    def add_raw_option(self, option) -> QHBoxLayout:
        """
        Add raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
