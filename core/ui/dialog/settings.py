#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.11 05:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from core.ui.widgets import SettingsInput, SettingsSlider, SettingsCheckbox, SettingsDialog
from core.utils import trans


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

        self.window.data['settings.btn.defaults'] = QPushButton(trans("dialog.settings.btn.defaults"))
        self.window.data['settings.btn.save'] = QPushButton(trans("dialog.settings.btn.save"))
        self.window.data['settings.btn.defaults'].clicked.connect(
            lambda: self.window.settings.load_default_settings())
        self.window.data['settings.btn.save'].clicked.connect(
            lambda: self.window.controller.settings.save(id))

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['settings.btn.defaults'])
        bottom_layout.addWidget(self.window.data['settings.btn.save'])

        self.window.path_label[id] = QLabel(str(path))
        self.window.path_label[id].setStyleSheet("font-weight: bold;")
        self.window.config_option['api_key'] = SettingsInput(self.window, 'api_key')
        self.window.config_option['organization_key'] = SettingsInput(self.window, 'organization_key')
        self.window.config_option['img_resolution'] = SettingsInput(self.window, 'img_resolution')
        self.window.config_option['temperature'] = SettingsSlider(self.window, 'temperature',
                                                                  '', 0, 200,
                                                                  1, 100)
        self.window.config_option['top_p'] = SettingsSlider(self.window, 'top_p',
                                                            '', 0, 200,
                                                            1, 100)
        self.window.config_option['frequency_penalty'] = SettingsSlider(self.window, 'frequency_penalty',
                                                                        '', 0, 200,
                                                                        1, 0)
        self.window.config_option['presence_penalty'] = SettingsSlider(self.window, 'presence_penalty',
                                                                       '', 0, 200,
                                                                       1, 0)
        self.window.config_option['use_context'] = SettingsCheckbox(self.window, 'use_context',
                                                                    trans('settings.use_context'))
        self.window.config_option['store_history'] = SettingsCheckbox(self.window, 'store_history',
                                                                      trans('settings.store_history'))
        self.window.config_option['store_history_time'] = SettingsCheckbox(self.window, 'store_history_time',
                                                                           trans('settings.store_history_time'))
        self.window.config_option['context_threshold'] = SettingsSlider(self.window, 'context_threshold',
                                                                        '', 0, 1000,
                                                                        1, 80)
        self.window.config_option['max_output_tokens'] = SettingsSlider(self.window, 'max_output_tokens',
                                                                        '', 1, 32000,
                                                                        1, 50)
        self.window.config_option['max_total_tokens'] = SettingsSlider(self.window, 'max_total_tokens',
                                                                       '', 1, 32000,
                                                                       1, 400)
        self.window.config_option['font_size'] = SettingsSlider(self.window, 'font_size',
                                                                '', 8, 20,
                                                                1, 12)

        options = {}
        options['api_key'] = self.add_option('settings.api_key', self.window.config_option['api_key'], True)
        options['organization_key'] = self.add_option('settings.organization_key',
                                                      self.window.config_option['organization_key'], True)
        options['temperature'] = self.add_option('settings.temperature', self.window.config_option['temperature'])
        options['top_p'] = self.add_option('settings.top_p', self.window.config_option['top_p'])
        options['frequency_penalty'] = self.add_option('settings.frequency_penalty',
                                                       self.window.config_option['frequency_penalty'])
        options['presence_penalty'] = self.add_option('settings.presence_penalty',
                                                      self.window.config_option['presence_penalty'])
        options['use_context'] = self.add_raw_option(self.window.config_option['use_context'])
        options['store_history'] = self.add_raw_option(self.window.config_option['store_history'])
        options['store_history_time'] = self.add_raw_option(self.window.config_option['store_history_time'])
        options['context_threshold'] = self.add_option('settings.context_threshold',
                                                       self.window.config_option['context_threshold'])
        options['max_output_tokens'] = self.add_option('settings.max_output_tokens',
                                                       self.window.config_option['max_output_tokens'])
        options['max_total_tokens'] = self.add_option('settings.max_total_tokens',
                                                      self.window.config_option['max_total_tokens'])
        options['font_size'] = self.add_option('settings.font_size',
                                               self.window.config_option['font_size'])
        options['img_resolution'] = self.add_option('settings.img_resolution',
                                                    self.window.config_option['img_resolution'])

        rows = QVBoxLayout()
        rows.addLayout(options['temperature'])
        rows.addLayout(options['top_p'])
        rows.addLayout(options['frequency_penalty'])
        rows.addLayout(options['presence_penalty'])
        rows.addLayout(options['use_context'])
        rows.addLayout(options['store_history'])
        rows.addLayout(options['store_history_time'])
        rows.addLayout(options['context_threshold'])
        rows.addLayout(options['max_output_tokens'])
        rows.addLayout(options['max_total_tokens'])
        rows.addLayout(options['font_size'])
        rows.addLayout(options['img_resolution'])
        rows.addLayout(options['api_key'])
        rows.addLayout(options['organization_key'])

        layout = QVBoxLayout()
        layout.addLayout(rows)
        layout.addLayout(bottom_layout)

        self.window.dialog['config.' + id] = SettingsDialog(self.window, id)
        self.window.dialog['config.' + id].setLayout(layout)
        self.window.dialog['config.' + id].setWindowTitle(trans('dialog.settings'))

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

        if title == 'settings.api_key':
            self.window.data[label_key].setMinimumHeight(60)
        return layout

    def add_raw_option(self, option):
        """
        Adds raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
