#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.07 17:00:00                  #
# ================================================== #
import json
import os

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QFrame

from ..widgets import SettingsInput, SettingsSlider, SettingsCheckbox, SettingsDialog, SettingsTextarea
from ...utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Settings dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups settings dialog"""

        id = "settings"
        path = self.window.config.path

        # buttons
        self.window.data['settings.btn.defaults'] = QPushButton(trans("dialog.settings.btn.defaults"))
        self.window.data['settings.btn.save'] = QPushButton(trans("dialog.settings.btn.save"))
        self.window.data['settings.btn.defaults'].clicked.connect(
            lambda: self.window.settings.load_default_settings())
        self.window.data['settings.btn.save'].clicked.connect(
            lambda: self.window.controller.settings.save(id))

        # bottom buttons layout
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['settings.btn.defaults'])
        bottom_layout.addWidget(self.window.data['settings.btn.save'])

        self.window.path_label[id] = QLabel(str(path))
        self.window.path_label[id].setStyleSheet("font-weight: bold;")

        # get settings options config
        settings_options = self.window.controller.settings.get_options()

        # build settings widgets
        settings_widgets = self.build_settings_widgets(settings_options)

        # apply settings widgets
        for key in settings_widgets:
            self.window.config_option[key] = settings_widgets[key]

        # apply widgets to layouts
        options = {}
        for key in settings_widgets:
            type = settings_options[key]['type']
            label = 'settings.' + settings_options[key]['label']
            extra = {}
            if 'extra' in settings_options[key]:
                extra = settings_options[key]['extra']
            if type == 'text' or type == 'int' or type == 'float':
                options[key] = self.add_option(label, settings_widgets[key], type, extra)
            elif type == 'textarea':
                options[key] = self.add_row_option(label, settings_widgets[key], type, extra)
            elif type == 'bool':
                options[key] = self.add_raw_option(settings_widgets[key], type)

        # API keys at the top
        rows = QVBoxLayout()
        rows.addLayout(options['api_key'])
        rows.addLayout(options['organization_key'])

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        line = self.add_line()
        scroll_content = QVBoxLayout()
        scroll_content.addWidget(line)

        # append widgets options layouts to scroll area
        for option in options.values():
            # prevent already added options from being added again
            if option in [options['api_key'], options['organization_key']]:
                continue
            # add option
            scroll_content.addLayout(option)
            line = self.add_line()
            scroll_content.addWidget(line)

        scroll_widget = QWidget()
        scroll_widget.setLayout(scroll_content)
        scroll.setWidget(scroll_widget)

        layout = QVBoxLayout()
        layout.addLayout(rows)  # api keys
        layout.addWidget(scroll)  # rest of options widgets
        layout.addLayout(bottom_layout)  # buttons (save, defaults)

        self.window.dialog['config.' + id] = SettingsDialog(self.window, id)
        self.window.dialog['config.' + id].setLayout(layout)
        self.window.dialog['config.' + id].setWindowTitle(trans('dialog.settings'))

    def build_settings_widgets(self, options):
        widgets = {}
        for key in options:
            option = options[key]
            label = options[key]['label']

            # create widget by option type
            if option['type'] == 'text' or option['type'] == 'int' or option['type'] == 'float':
                if 'slider' in option and option['slider'] \
                        and (option['type'] == 'int' or option['type'] == 'float'):
                    min = 0
                    max = 1
                    step = 1

                    if 'min' in option:
                        min = option['min']
                    if 'max' in option:
                        max = option['max']
                    if 'step' in option:
                        step = option['step']
                    value = min
                    if 'value' in option:
                        value = option['value']

                    multiplier = 1
                    if 'multiplier' in option:
                        multiplier = option['multiplier']

                    if option['type'] == 'float':
                        value = value * multiplier  # multiplier makes effect only on float
                        min = min * multiplier
                        max = max * multiplier
                        # step = step * multiplier
                    elif option['type'] == 'int':
                        value = int(value)

                    # slider + text input
                    widgets[key] = SettingsSlider(self.window, label, '',
                                                           min,
                                                           max,
                                                           step,
                                                           value)
                else:
                    # text input
                    widgets[key] = SettingsInput(self.window, label)
            elif option['type'] == 'textarea':
                # textarea
                widgets[key] = SettingsTextarea(self.window, label)
                widgets[key].setMinimumHeight(100)
            elif option['type'] == 'bool':
                # checkbox
                widgets[key] = SettingsCheckbox(self.window, label, trans('settings.' + key))

        return widgets

    def add_line(self):
        """
        Makes line
        """
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def add_option(self, title, option, type, extra=None):
        """
        Adds option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        :param type: Option type
        """
        label_key = title + '.label'
        self.window.data[label_key] = QLabel(trans(title))
        if extra is not None and 'bold' in extra and extra['bold']:
            self.window.data[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        layout = QHBoxLayout()
        layout.addWidget(self.window.data[label_key])
        layout.addWidget(option)

        if title == 'settings.api_key':
            self.window.data[label_key].setMinimumHeight(60)
        return layout

    def add_row_option(self, title, option, type, extra=None):
        """
        Adds option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        :param type: Option type
        """
        label_key = title + '.label'
        self.window.data[label_key] = QLabel(trans(title))
        if extra is not None and 'bold' in extra and extra['bold']:
            self.window.data[label_key].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        layout = QVBoxLayout()
        layout.addWidget(self.window.data[label_key])
        layout.addWidget(option)

        if title == 'settings.api_key':
            self.window.data[label_key].setMinimumHeight(60)
        return layout

    def add_raw_option(self, option, type):
        """
        Adds raw option row

        :param option: Option
        :param type: Option type
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
