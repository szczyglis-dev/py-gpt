#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.07 14:00:00                  #
# ================================================== #
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget, QFrame

from ..widget.settings import SettingsInput, SettingsTextarea, SettingsSlider, SettingsCheckbox, SettingsDict, \
    PluginSettingsDialog, PluginSelectMenu
from ...utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Plugins settings dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self, idx=None):
        """Setups plugin settings dialog"""

        dialog_id = "plugin_settings"

        self.window.data['plugin.settings.btn.defaults.user'] = QPushButton(trans("dialog.settings.btn.defaults.user"))
        self.window.data['plugin.settings.btn.defaults.app'] = QPushButton(trans("dialog.settings.btn.defaults.app"))
        self.window.data['plugin.settings.btn.save'] = QPushButton(trans("dialog.settings.btn.save"))

        self.window.data['plugin.settings.btn.defaults.user'].clicked.connect(
            lambda: self.window.controller.plugins.load_defaults_user())
        self.window.data['plugin.settings.btn.defaults.app'].clicked.connect(
            lambda: self.window.controller.plugins.load_defaults_app())
        self.window.data['plugin.settings.btn.save'].clicked.connect(
            lambda: self.window.controller.plugins.save_settings())

        # bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['plugin.settings.btn.defaults.user'])
        bottom_layout.addWidget(self.window.data['plugin.settings.btn.defaults.app'])
        bottom_layout.addWidget(self.window.data['plugin.settings.btn.save'])

        # plugins tabs
        self.window.tabs['plugin.settings'] = QTabWidget()

        # build plugin settings tabs
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
                elif option['type'] == 'dict':
                    # dictionary items
                    self.window.plugin_option[id][key] = SettingsDict(self.window, option_name, True, 'plugin', id,
                                                                      option['keys'],
                                                                      option['value'])

                if key not in self.window.plugin_option[id]:
                    continue

                # add option to scroll
                scroll_content.addLayout(self.add_option(key, option, self.window.plugin_option[id][key], option['type']))

            scroll_content.addStretch()

            # scroll widget
            scroll_widget = QWidget()
            scroll_widget.setLayout(scroll_content)
            scroll.setWidget(scroll_widget)

            desc_label = QLabel(plugin.description)
            desc_label.setWordWrap(True)
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setStyleSheet("font-weight: bold;")

            line = self.add_line()

            area = QVBoxLayout()
            area.addWidget(desc_label)
            area.addWidget(line)
            area.addWidget(scroll)

            area_widget = QWidget()
            area_widget.setLayout(area)

            # append to tab
            self.window.tabs['plugin.settings'].addTab(area_widget, plugin.name)

        self.window.tabs['plugin.settings'].currentChanged.connect(
            lambda: self.window.controller.plugins.set_plugin_by_tab(self.window.tabs['plugin.settings'].currentIndex()))

        # plugins list
        id = 'plugin.list'
        self.window.data[id] = PluginSelectMenu(self.window, id)
        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])

        data = {}
        for plugin_id in self.window.controller.plugins.handler.plugins:
            plugin = self.window.controller.plugins.handler.plugins[plugin_id]
            data[plugin_id] = plugin
        self.update_list(id, data)

        # set max width to list
        self.window.data[id].setMaximumWidth(250)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.data[id])
        main_layout.addWidget(self.window.tabs['plugin.settings'])

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list + plugins tabs
        layout.addLayout(bottom_layout)  # bottom buttons (save, defaults)

        self.window.dialog[dialog_id] = PluginSettingsDialog(self.window, dialog_id)
        self.window.dialog[dialog_id].setLayout(layout)
        self.window.dialog[dialog_id].setWindowTitle(trans('dialog.plugin_settings'))

        # restore current opened tab if idx is set
        if idx is not None:
            try:
                self.window.tabs['plugin.settings'].setCurrentIndex(idx)
                self.window.controller.plugins.set_plugin_by_tab(idx)
            except:
                print('Cannot restore plugin settings tab: {}'.format(idx))

    def add_line(self):
        """
        Makes line
        """
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def add_option(self, key, option, widget, type):
        """
        Appends option row

        :param key: option key
        :param option: option
        :param widget: widget
        :param type: option type
        :return: QVBoxLayout
        """
        widget.setToolTip(option['tooltip'])
        label_key = key + '.label'
        self.window.data[label_key] = QLabel(trans(option['label']))
        self.window.data[label_key].setStyleSheet("font-weight: bold;")

        # 2 cols layout
        if type != 'textarea' and type != 'dict':
            cols = QHBoxLayout()
            cols.addWidget(self.window.data[label_key])
            cols.addWidget(widget)

            cols_widget = QWidget()
            cols_widget.setLayout(cols)
            cols_widget.setMaximumHeight(90)

            desc_label = QLabel(option['description'])
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(30)
            desc_label.setStyleSheet("font-size: 10px;")
            desc_label.setToolTip(option['tooltip'])

            layout = QVBoxLayout()
            layout.addWidget(cols_widget)
            layout.addWidget(desc_label)
        else:
            # textarea and dict
            layout = QVBoxLayout()
            layout.addWidget(self.window.data[label_key])
            layout.addWidget(widget)

            desc_label = QLabel(option['description'])
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(30)
            desc_label.setStyleSheet("font-size: 10px;")
            desc_label.setToolTip(option['tooltip'])

            layout.addWidget(desc_label)

        line = self.add_line()
        layout.addWidget(line)

        return layout

    def add_raw_option(self, option):
        """
        Adds raw option row

        :param option: Option
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout

    def create_model(self, parent):
        """
        Creates list model
        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 1, parent)
        return model

    def update_list(self, id, data):
        """
        Updates list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.models[id].removeRows(0, self.window.models[id].rowCount())
        i = 0
        for n in data:
            self.window.models[id].insertRow(i)
            name = data[n].name
            self.window.models[id].setData(self.window.models[id].index(i, 0), name)
            i += 1
