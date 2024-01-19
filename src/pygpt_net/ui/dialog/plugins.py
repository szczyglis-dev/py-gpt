#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 18:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget, QFrame

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.ui.widget.dialog.settings_plugin import PluginSettingsDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.element.url import UrlLabel
from pygpt_net.ui.widget.lists.plugin import PluginList
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window=None):
        """
        Plugins settings dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "plugin_settings"
        self.max_list_width = 250

    def setup(self, idx=None):
        """
        Setup plugin settings dialog

        :param idx: current plugin tab index
        """
        self.window.ui.nodes['plugin.settings.btn.defaults.user'] = \
            QPushButton(trans("dialog.plugin.settings.btn.defaults.user"))
        self.window.ui.nodes['plugin.settings.btn.defaults.app'] = \
            QPushButton(trans("dialog.plugin.settings.btn.defaults.app"))
        self.window.ui.nodes['plugin.settings.btn.save'] = \
            QPushButton(trans("dialog.plugin.settings.btn.save"))

        self.window.ui.nodes['plugin.settings.btn.defaults.user'].clicked.connect(
            lambda: self.window.controller.plugins.settings.load_defaults_user())
        self.window.ui.nodes['plugin.settings.btn.defaults.app'].clicked.connect(
            lambda: self.window.controller.plugins.settings.load_defaults_app())
        self.window.ui.nodes['plugin.settings.btn.save'].clicked.connect(
            lambda: self.window.controller.plugins.settings.save())

        # set enter key to save button
        self.window.ui.nodes['plugin.settings.btn.defaults.user'].setAutoDefault(False)
        self.window.ui.nodes['plugin.settings.btn.defaults.app'].setAutoDefault(False)
        self.window.ui.nodes['plugin.settings.btn.save'].setAutoDefault(True)

        # footer buttons
        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['plugin.settings.btn.defaults.user'])
        footer.addWidget(self.window.ui.nodes['plugin.settings.btn.defaults.app'])
        footer.addWidget(self.window.ui.nodes['plugin.settings.btn.save'])

        # plugins tabs
        self.window.ui.tabs['plugin.settings'] = QTabWidget()

        # build plugin settings tabs
        for id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[id]
            parent_id = "plugin." + id

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QVBoxLayout()

            # create plugin options entry if not exists
            if parent_id not in self.window.ui.config:
                self.window.ui.config[parent_id] = {}

            # get plugin options
            options = plugin.setup()
            widgets = self.build_widgets(plugin, options)
            advanced_keys = []
            for key in options:
                if 'advanced' in options[key] and options[key]['advanced']:
                    advanced_keys.append(key)

            # apply settings widgets
            for key in widgets:
                self.window.ui.config[parent_id][key] = widgets[key]

            # append URLs at the beginning
            if len(plugin.urls) > 0:
                urls_widget = self.add_urls(plugin.urls)
                content.addWidget(urls_widget)

            for key in widgets:
                if key in advanced_keys:  # hide advanced options
                    continue
                content.addLayout(self.add_option(plugin, widgets[key], options[key]))  # add to scroll

            # append advanced options at the end
            if len(advanced_keys) > 0:
                group_id = 'plugin.settings.advanced' + '.' + id
                self.window.ui.groups[group_id] = CollapsedGroup(self.window, group_id, None, False, None)
                self.window.ui.groups[group_id].box.setText(trans('settings.advanced.collapse'))
                for key in widgets:
                    if key not in advanced_keys:  # ignore non-advanced options
                        continue
                    
                    option = self.add_option(plugin, widgets[key], options[key])  # build option
                    self.window.ui.groups[group_id].add_layout(option)  # add option to group

                # add advanced options group to scroll
                content.addWidget(self.window.ui.groups[group_id])

            content.addStretch()

            # scroll widget
            scroll_widget = QWidget()
            scroll_widget.setLayout(content)
            scroll.setWidget(scroll_widget)

            # set description, translate if localization is enabled
            name_txt = plugin.name
            desc_key = 'plugin.settings.' + id + '.desc'
            desc_txt = plugin.description
            if plugin.use_locale:
                domain = 'plugin.' + plugin.id
                name_txt = trans('plugin.name', False, domain)
                desc_txt = trans('plugin.description', False, domain)
            self.window.ui.nodes[desc_key] = QLabel(desc_txt)
            self.window.ui.nodes[desc_key].setWordWrap(True)
            self.window.ui.nodes[desc_key].setAlignment(Qt.AlignCenter)
            self.window.ui.nodes[desc_key].setStyleSheet("font-weight: bold;")

            line = self.add_line()

            area = QVBoxLayout()
            area.addWidget(self.window.ui.nodes[desc_key])
            area.addWidget(line)
            area.addWidget(scroll)

            area_widget = QWidget()
            area_widget.setLayout(area)

            # append to tab
            self.window.ui.tabs['plugin.settings'].addTab(area_widget, name_txt)

        self.window.ui.tabs['plugin.settings'].currentChanged.connect(
            lambda: self.window.controller.plugins.set_by_tab(
                self.window.ui.tabs['plugin.settings'].currentIndex()))

        data = {}
        for plugin_id in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[plugin_id]
            data[plugin_id] = plugin

        # plugins list
        id = 'plugin.list'
        self.window.ui.nodes[id] = PluginList(self.window, id)
        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        # update plugins list
        self.update_list(id, data)

        # set max width to list
        self.window.ui.nodes[id].setMaximumWidth(self.max_list_width)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.ui.nodes[id])
        main_layout.addWidget(self.window.ui.tabs['plugin.settings'])

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list + plugins tabs
        layout.addLayout(footer)  # bottom buttons (save, defaults)

        self.window.ui.dialog[self.dialog_id] = PluginSettingsDialog(self.window, self.dialog_id)
        self.window.ui.dialog[self.dialog_id].setLayout(layout)
        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.plugin_settings'))

        # restore current opened tab if idx is set
        if idx is not None:
            try:
                self.window.ui.tabs['plugin.settings'].setCurrentIndex(idx)
                self.window.controller.plugins.set_by_tab(idx)
            except Exception as e:
                print('Failed restore plugin settings tab: {}'.format(idx))
        else:
            self.window.controller.plugins.set_by_tab(0)

    def build_widgets(self, plugin: BasePlugin, options: dict) -> dict:
        """
        Build settings options widgets

        :param plugin: plugin instance
        :param options: plugin options
        :return: dict of widgets
        """
        id = plugin.id
        parent = "plugin." + id  # parent id for plugins is in format: plugin.<plugin_id>
        widgets = {}

        for key in options:
            option = options[key]
            # create widget by option type
            if option['type'] == 'text' or option['type'] == 'int' or option['type'] == 'float':
                if 'slider' in option and option['slider'] \
                        and (option['type'] == 'int' or option['type'] == 'float'):
                    widgets[key] = OptionSlider(self.window, parent, key, option)  # slider + text input
                else:
                    if 'secret' in option and option['secret']:
                        widgets[key] = PasswordInput(self.window, parent, key, option)  # password input
                    else:
                        widgets[key] = OptionInput(self.window, parent, key, option)  # text input
            elif option['type'] == 'textarea':
                widgets[key] = OptionTextarea(self.window, parent, key, option)  # textarea
            elif option['type'] == 'bool':
                widgets[key] = OptionCheckbox(self.window, parent, key, option)  # checkbox
            elif option['type'] == 'dict':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionDict(self.window, parent, key, option)  # dictionary
            elif option['type'] == 'combo':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCombo(self.window, parent, key, option)  # combobox

        return widgets

    def add_line(self) -> QFrame:
        """
        Make separator line

        :return: separator line
        """
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def add_urls(self, urls: dict) -> QWidget:
        """
        Add clickable urls to list

        :param urls: urls dict
        :return: QWidget
        """
        layout = QVBoxLayout()
        for name in urls:
            url = urls[name]
            label = UrlLabel(name, url)
            layout.addWidget(label)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def add_option(self, plugin: BasePlugin, widget: QWidget, option: dict) -> QVBoxLayout:
        """
        Append option widget to layout

        :param plugin: plugin instance
        :param widget: widget instance
        :param option: option dict
        :return: QVBoxLayout
        """
        one_column_types = ['textarea', 'dict', 'bool']

        key = option['id']
        label_key = 'plugin.' + plugin.id + '.' + key + '.label'
        desc_key = 'plugin.' + plugin.id + '.' + key + '.desc'

        # get option label and description
        txt_title = option['label']
        txt_desc = option['description']
        txt_tooltip = option['tooltip']

        # translate if localization is enabled
        if plugin.use_locale:
            domain = 'plugin.' + plugin.id
            txt_title = trans(key + '.label', False, domain)
            txt_desc = trans(key + '.description', False, domain)
            txt_tooltip = trans(key + '.tooltip', False, domain)

            # if empty tooltip then use description
            if txt_tooltip == key + '.tooltip':
                txt_tooltip = txt_desc

        widget.setToolTip(txt_tooltip)

        if option['type'] != 'bool':
            self.window.ui.nodes[label_key] = QLabel(txt_title)
            self.window.ui.nodes[label_key].setStyleSheet("font-weight: bold;")

        # 2-columns layout
        if option['type'] not in one_column_types:
            cols = QHBoxLayout()
            cols.addWidget(self.window.ui.nodes[label_key])  # disable label in bool type
            cols.addWidget(widget)

            cols_widget = QWidget()
            cols_widget.setLayout(cols)
            cols_widget.setMaximumHeight(90)

            self.window.ui.nodes[desc_key] = QLabel(txt_desc)
            self.window.ui.nodes[desc_key].setWordWrap(True)
            self.window.ui.nodes[desc_key].setMaximumHeight(40)
            self.window.ui.nodes[desc_key].setStyleSheet("font-size: 10px;")
            self.window.ui.nodes[desc_key].setToolTip(txt_tooltip)

            layout = QVBoxLayout()
            layout.addWidget(cols_widget)
            layout.addWidget(self.window.ui.nodes[desc_key])
        else:
            # 1-column layout: textarea and dict fields
            layout = QVBoxLayout()
            if option['type'] != 'bool':
                layout.addWidget(self.window.ui.nodes[label_key])
            else:
                widget.box.setText(txt_title)  # set checkbox label
            layout.addWidget(widget)

            self.window.ui.nodes[desc_key] = QLabel(txt_desc)
            self.window.ui.nodes[desc_key].setWordWrap(True)
            self.window.ui.nodes[desc_key].setMaximumHeight(40)
            self.window.ui.nodes[desc_key].setStyleSheet("font-size: 10px;")
            self.window.ui.nodes[desc_key].setToolTip(txt_tooltip)

            layout.addWidget(self.window.ui.nodes[desc_key])

        # append URLs at the beginning
        if option['urls'] is not None and len(option['urls']) > 0:
            urls_widget = self.add_urls(option['urls'])
            layout.addWidget(urls_widget)

        line = self.add_line()  # TODO: change name to separator
        layout.addWidget(line)

        return layout

    def add_raw_option(self, option: dict) -> QHBoxLayout:
        """
        Add raw option row

        :param option: Option
        :return: QHBoxLayout
        """
        layout = QHBoxLayout()
        layout.addWidget(option)
        return layout

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model
        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update_list(self, id: str, data: dict):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = self.window.core.plugins.get_name(data[n].id)
            tooltip = self.window.core.plugins.get_desc(data[n].id)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), tooltip, Qt.ToolTipRole)
            i += 1
