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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget

from ..widgets import SettingsInput, SettingsSlider, SettingsCheckbox, PluginSettingsDialog, SettingsTextarea
from ...utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Plugins settings dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups plugin settings dialog"""

        dialog_id = "plugin_settings"

        self.window.data['settings.btn.defaults'] = QPushButton(trans("dialog.settings.btn.defaults"))
        self.window.data['settings.btn.save'] = QPushButton(trans("dialog.settings.btn.save"))
        self.window.data['settings.btn.defaults'].clicked.connect(
            lambda: self.window.controller.plugins.load_defaults())
        self.window.data['settings.btn.save'].clicked.connect(
            lambda: self.window.controller.plugins.save_settings())

        # bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['settings.btn.defaults'])
        bottom_layout.addWidget(self.window.data['settings.btn.save'])

        # plugins tabs
        tabs = QTabWidget()

        for id in self.window.controller.plugins.handler.plugins:
            plugin = self.window.controller.plugins.handler.plugins[id]

            """
            options["iterations"] = {
                "type": "int",  # int, float, bool, text, textarea
                "label": "Iterations",
                "desc": "How many iterations to run? 0 = infinite. "
                        "Warning: Setting to 0 can cause a lot of requests and tokens usage!",
                "tooltip": "Some tooltip...",
                "value": 3,
                "min": 0,
                "max": 100,
            }
            """

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QVBoxLayout()

            # create plugin options entry if not exists
            if id not in self.window.plugin_option:
                self.window.plugin_option[id] = {}

            # get plugin options
            options = plugin.setup()
            for key in options:
                option = options[key]
                option_name = 'plugin.' + id + '.' + key

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

                        # slider + text input
                        self.window.plugin_option[id][key] = SettingsSlider(self.window, option_name, '',
                                                                            min,
                                                                            max,
                                                                            step,
                                                                            int(value))
                    else:
                        # text input
                        self.window.plugin_option[id][key] = SettingsInput(self.window, option_name)
                elif option['type'] == 'textarea':
                    # textarea
                    self.window.plugin_option[id][key] = SettingsTextarea(self.window, option_name)
                elif option['type'] == 'bool':
                    # checkbox
                    self.window.plugin_option[id][key] = SettingsCheckbox(self.window, option_name)

                if key not in self.window.plugin_option[id]:
                    continue

                # add option to scroll
                scroll_content.addLayout(self.add_option(key, option, self.window.plugin_option[id][key]))

            # scroll widget
            scroll_widget = QWidget()
            scroll_widget.setLayout(scroll_content)
            scroll.setWidget(scroll_widget)

            desc_label = QLabel(plugin.description)
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setStyleSheet("font-weight: bold;")

            area = QVBoxLayout()
            area.addWidget(desc_label)
            area.addWidget(scroll)

            area_widget = QWidget()
            area_widget.setLayout(area)

            # append to tab
            tabs.addTab(area_widget, plugin.name)

        tabs.currentChanged.connect(
            lambda: self.window.controller.plugins.set_plugin_by_tab(tabs.currentIndex()))

        layout = QVBoxLayout()
        layout.addWidget(tabs)  # plugins tabs
        layout.addLayout(bottom_layout)  # bottom buttons (save, defaults)

        self.window.dialog[dialog_id] = PluginSettingsDialog(self.window, dialog_id)
        self.window.dialog[dialog_id].setLayout(layout)
        self.window.dialog[dialog_id].setWindowTitle(trans('dialog.plugin_settings'))

    def add_option(self, key, option, widget):
        """
        Appends option row

        :param key: option key
        :param option: option
        :param widget: widget
        :return: QVBoxLayout
        """
        widget.setToolTip(option['tooltip'])
        label_key = key + '.label'
        self.window.data[label_key] = QLabel(trans(option['label']))
        self.window.data[label_key].setStyleSheet("font-weight: bold;")

        cols = QHBoxLayout()
        cols.addWidget(self.window.data[label_key])
        cols.addWidget(widget)

        cols_widget = QWidget()
        cols_widget.setLayout(cols)
        cols_widget.setMaximumHeight(90)

        desc_label = QLabel('<i>' + option['description'] + '</i>')
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(30)
        desc_label.setStyleSheet("font-size: 10px;")

        layout = QVBoxLayout()
        layout.addWidget(cols_widget)
        layout.addWidget(desc_label)

        return layout

    def add_raw_option(self, option):
        """
        Adds raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout
