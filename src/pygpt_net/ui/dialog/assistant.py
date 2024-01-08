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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy

from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.utils import trans


class Assistant:
    def __init__(self, window=None):
        """
        Assistant editor dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "assistant"
        self.dialog_id = "assistants"

    def setup(self):
        """Setups assistant editor dialog"""
        self.window.config_bag.items['assistant'] = {}

        self.window.ui.nodes['assistant.btn.save'] = QPushButton(trans("dialog.assistant.btn.save"))
        self.window.ui.nodes['assistant.btn.save'].clicked.connect(
            lambda: self.window.controller.assistant.editor.save())
        self.window.ui.nodes['assistant.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['assistant.btn.save'])
        func_keys = {
            'name': 'text',
            'params': 'text',
            'desc': 'text',
        }
        func_values = {}

        # get option fields config
        fields = self.window.controller.assistant.editor.get_options()

        # build settings widgets
        widgets = self.build_widgets(fields)

        # apply settings widgets
        for key in widgets:
            self.window.config_bag.items[self.id][key] = widgets[key]

        # btn: add function
        self.window.config_bag.items[self.id]['tool.function'].add_btn.setText(trans('assistant.func.add'))
        # Empty params: {"type": "object", "properties": {}}

        # set tips
        self.window.ui.nodes['assistant.id_tip'] = QLabel(trans('assistant.new.id_tip'))
        self.window.ui.nodes['assistant.id_tip'].setMinimumHeight(40)

        self.window.ui.nodes['assistant.api.tip'] = QPushButton(trans('assistant.api.tip'))  # TODO: url btn
        self.window.ui.nodes['assistant.api.tip'].setAutoDefault(False)
        self.window.ui.nodes['assistant.api.tip'].setFlat(True)
        self.window.ui.nodes['assistant.api.tip'].setStyleSheet("text-align: left; color: #fff; text-decoration: "
                                                                "underline; text-transform: none;")
        self.window.ui.nodes['assistant.api.tip'].setStyleSheet("text-transform: none;")
        self.window.ui.nodes['assistant.api.tip'].setCursor(Qt.PointingHandCursor)
        self.window.ui.nodes['assistant.api.tip'].clicked.connect(
            lambda: self.window.controller.assistant.goto_online())

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if fields[key]["type"] == 'text' or fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                options[key] = self.add_raw_option(widgets[key])
            elif fields[key]["type"] == 'dict':
                options[key] = self.add_row_option(widgets[key], fields[key])
                if key == "tool.function":
                    widgets[key].setMinimumHeight(150)

        rows = QVBoxLayout()

        # append widgets options layouts to rows
        for key in options:
            # extra rows  TODO: add tip to settings config
            if key == "id":
                rows.addWidget(self.window.ui.nodes['assistant.id_tip'])

            rows.addLayout(options[key])

            # extra rows
            if key == "instructions":
                rows.addWidget(self.window.ui.nodes['assistant.api.tip'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(footer)
        layout.setStretch(1, 1)

        self.window.ui.dialog['editor.' + self.dialog_id] = EditorDialog(self.window, self.dialog_id)
        self.window.ui.dialog['editor.' + self.dialog_id].setLayout(layout)
        self.window.ui.dialog['editor.' + self.dialog_id].setWindowTitle(trans('dialog.assistant'))

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
        self.window.ui.nodes[label_key].setMaximumWidth(120)
        if 'bold' in extra and extra['bold']:
            self.window.ui.nodes[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.ui.nodes[label_key].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes[label_key])
        layout.addWidget(widget)
        layout.setStretch(0, 1)
        return layout

    def add_row_option(self, widget, option) -> QHBoxLayout:
        """
        Add option row (label + option)

        :param widget: Widget
        :param option: Option
        """
        label = option['label']
        label_key = label + '.label'
        self.window.ui.nodes[label_key] = QLabel(trans(label))
        self.window.ui.nodes[label_key].setMinimumHeight(30)

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
