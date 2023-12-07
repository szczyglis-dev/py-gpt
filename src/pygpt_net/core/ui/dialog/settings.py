#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.07 10:00:00                  #
# ================================================== #

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
                                                                       '', 1, 256000,
                                                                       1, 400)
        self.window.config_option['font_size'] = SettingsSlider(self.window, 'font_size',
                                                                '', 8, 20,
                                                                1, 12)
        self.window.config_option['font_size.input'] = SettingsSlider(self.window, 'font_size.input',
                                                                      '', 8, 20,
                                                                      1, 12)
        self.window.config_option['font_size.ctx'] = SettingsSlider(self.window, 'font_size.ctx',
                                                                    '', 8, 20,
                                                                    1, 12)

        # v2.0.1
        self.window.config_option['ctx.auto_summary'] = SettingsCheckbox(self.window, 'ctx.auto_summary',
                                                                         trans('settings.ctx.auto_summary'))
        self.window.config_option['ctx.auto_summary.system'] = SettingsInput(self.window, 'ctx.auto_summary.system')
        self.window.config_option['ctx.auto_summary.prompt'] = SettingsTextarea(self.window, 'ctx.auto_summary.prompt')

        options = {}
        options['api_key'] = self.add_option('settings.api_key', self.window.config_option['api_key'], 'text', True)
        options['organization_key'] = self.add_option('settings.organization_key',
                                                      self.window.config_option['organization_key'], 'text', True)
        options['temperature'] = self.add_option('settings.temperature', self.window.config_option['temperature'],
                                                 'float')
        options['top_p'] = self.add_option('settings.top_p', self.window.config_option['top_p'], 'float')
        options['frequency_penalty'] = self.add_option('settings.frequency_penalty',
                                                       self.window.config_option['frequency_penalty'], 'float')
        options['presence_penalty'] = self.add_option('settings.presence_penalty',
                                                      self.window.config_option['presence_penalty'], 'float')
        options['use_context'] = self.add_raw_option(self.window.config_option['use_context'], 'bool')
        options['store_history'] = self.add_raw_option(self.window.config_option['store_history'], 'bool')
        options['store_history_time'] = self.add_raw_option(self.window.config_option['store_history_time'], 'bool')
        options['context_threshold'] = self.add_option('settings.context_threshold',
                                                       self.window.config_option['context_threshold'], 'int')
        options['max_output_tokens'] = self.add_option('settings.max_output_tokens',
                                                       self.window.config_option['max_output_tokens'], 'int')
        options['max_total_tokens'] = self.add_option('settings.max_total_tokens',
                                                      self.window.config_option['max_total_tokens'], 'int')
        options['font_size'] = self.add_option('settings.font_size',
                                               self.window.config_option['font_size'], 'int')
        options['font_size.input'] = self.add_option('settings.font_size.input',
                                                     self.window.config_option['font_size.input'], 'int')
        options['font_size.ctx'] = self.add_option('settings.font_size.ctx',
                                                   self.window.config_option['font_size.ctx'], 'int')
        options['img_resolution'] = self.add_option('settings.img_resolution',
                                                    self.window.config_option['img_resolution'], 'text')

        # v2.0.1
        options['ctx.auto_summary'] = self.add_raw_option(self.window.config_option['ctx.auto_summary'])
        options['ctx.auto_summary.system'] = self.add_option('settings.ctx.auto_summary.system',
                                                             self.window.config_option['ctx.auto_summary.system'],
                                                             'text')
        options['ctx.auto_summary.prompt'] = self.add_row_option('settings.ctx.auto_summary.prompt',
                                                                 self.window.config_option['ctx.auto_summary.prompt'],
                                                                 'textarea')

        rows = QVBoxLayout()
        rows.addLayout(options['api_key'])
        rows.addLayout(options['organization_key'])

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        line = self.add_line()
        scroll_content = QVBoxLayout()
        scroll_content.addWidget(line)

        for option in options.values():
            # prevent already added options
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
        layout.addLayout(rows)
        layout.addWidget(scroll)
        layout.addLayout(bottom_layout)

        self.window.dialog['config.' + id] = SettingsDialog(self.window, id)
        self.window.dialog['config.' + id].setLayout(layout)
        self.window.dialog['config.' + id].setWindowTitle(trans('dialog.settings'))

    def add_line(self):
        """
        Makes line
        """
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def add_option(self, title, option, type, bold=False):
        """
        Adds option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        :param type: Option type
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

    def add_row_option(self, title, option, type, bold=False):
        """
        Adds option

        :param title: Title
        :param option: Option
        :param bold: Bold title
        :param type: Option type
        """
        label_key = title + '.label'
        self.window.data[label_key] = QLabel(trans(title))
        if bold:
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
