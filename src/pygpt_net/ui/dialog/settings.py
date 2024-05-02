#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QSizePolicy, \
    QTabWidget, QSplitter

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.settings import SettingsDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.lists.settings import SettingsSectionList
from pygpt_net.utils import trans


class Settings(BaseConfigDialog):
    def __init__(self, window=None, *args, **kwargs):
        super(Settings, self).__init__(window, *args, **kwargs)
        """
        Settings (main) dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "config"

    def setup(self, idx=None):
        """Setup settings dialog"""
        id = "settings"
        path = self.window.core.config.path
        sections = self.window.core.settings.get_sections()

        # buttons
        self.window.ui.nodes['settings.btn.defaults.user'] = QPushButton(trans("dialog.settings.btn.defaults.user"))
        self.window.ui.nodes['settings.btn.defaults.app'] = QPushButton(trans("dialog.settings.btn.defaults.app"))
        self.window.ui.nodes['settings.btn.save'] = QPushButton(trans("dialog.settings.btn.save"))
        self.window.ui.nodes['settings.btn.defaults.user'].clicked.connect(
            lambda: self.window.controller.settings.editor.load_defaults_user())
        self.window.ui.nodes['settings.btn.defaults.app'].clicked.connect(
            lambda: self.window.controller.settings.editor.load_defaults_app())
        self.window.ui.nodes['settings.btn.save'].clicked.connect(
            lambda: self.window.controller.settings.editor.save(id))

        # set enter key to save button
        self.window.ui.nodes['settings.btn.defaults.user'].setAutoDefault(False)
        self.window.ui.nodes['settings.btn.defaults.app'].setAutoDefault(False)
        self.window.ui.nodes['settings.btn.save'].setAutoDefault(True)

        # bottom buttons layout
        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['settings.btn.defaults.user'])
        bottom.addWidget(self.window.ui.nodes['settings.btn.defaults.app'])
        bottom.addWidget(self.window.ui.nodes['settings.btn.save'])

        self.window.ui.paths[id] = QLabel(str(path))
        self.window.ui.paths[id].setStyleSheet("font-weight: bold;")

        # settings section tabs
        self.window.ui.tabs['settings.section'] = QTabWidget()

        # build settings tabs
        for section_id in sections:
            content_tabs = {}
            scroll_tabs = {}
            advanced_keys = {}  # advanced options keys

            # get settings options for section
            fields = self.window.controller.settings.editor.get_options(section_id)

            # extract tab ids, general is default
            tab_ids = self.extract_option_tabs(fields)
            extra_tabs = self.append_tabs(section_id)
            if extra_tabs:
                tab_ids += extra_tabs
            for tab_id in tab_ids:
                content_tabs[tab_id] = QVBoxLayout()
                scroll_tabs[tab_id] = QScrollArea()
                scroll_tabs[tab_id].setWidgetResizable(True)

            # prepare advanced options keys
            for key in fields:
                if 'advanced' in fields[key] and fields[key]['advanced']:
                    tab_id = "general"
                    if 'tab' in fields[key]:
                        tab = fields[key]['tab']
                        if tab is not None and tab != "":
                            tab_id = tab
                    if tab_id not in advanced_keys:
                        advanced_keys[tab_id] = []
                    advanced_keys[tab_id].append(key)

            # build settings widgets
            widgets = self.build_widgets(self.id, fields)

            # apply settings widgets
            for key in widgets:
                self.window.ui.config[self.id][key] = widgets[key]

            # apply widgets to layouts
            options = {}
            for key in widgets:
                if fields[key]["type"] == 'text' or fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                    options[key] = self.add_option(widgets[key], fields[key])
                elif fields[key]["type"] == 'textarea':
                    options[key] = self.add_row_option(widgets[key], fields[key])
                elif fields[key]["type"] == 'bool':
                    options[key] = self.add_raw_option(widgets[key], fields[key])
                elif fields[key]['type'] == 'dict':
                    options[key] = self.add_row_option(widgets[key], fields[key])  # dict
                    # register dict to editor:
                    self.window.ui.dialogs.register_dictionary(
                        key,
                        parent="config",
                        option=fields[key],
                    )
                elif fields[key]['type'] == 'combo':
                    options[key] = self.add_option(widgets[key], fields[key])  # combobox

            self.window.ui.nodes['settings.api_key.label'].setMinimumHeight(60)

            # append widgets options layouts to scroll area
            for key in options:
                option = options[key]
                tab_id = "general"
                if 'tab' in fields[key]:
                    tab = fields[key]['tab']
                    if tab is not None and tab != "":
                        tab_id = tab

                # hide advanced options
                if tab_id in advanced_keys and key in advanced_keys[tab_id]:
                    continue

                content_tabs[tab_id].addLayout(option)  # add

                # append URLs
                if 'urls' in fields[key]:
                    content_tabs[tab_id].addWidget(self.add_urls(fields[key]['urls']))

                # check if not last option
                if key != list(options.keys())[-1] or tab_id in advanced_keys:
                    content_tabs[tab_id].addWidget(self.add_line())

            # append advanced options at the end
            if len(advanced_keys) > 0:
                groups = {}
                for key in options:
                    tab_id = "general"
                    if 'tab' in fields[key]:
                        tab = fields[key]['tab']
                        if tab is not None and tab != "":
                            tab_id = tab

                    if tab_id not in advanced_keys:
                        continue

                    # ignore non-advanced options
                    if key not in advanced_keys[tab_id]:
                        continue

                    group_id = 'settings.advanced.' + section_id + '.' + tab_id

                    if tab_id not in groups:
                        groups[tab_id] = CollapsedGroup(self.window, group_id, None, False, None)
                        groups[tab_id].box.setText(trans('settings.advanced.collapse'))

                    groups[tab_id].add_layout(options[key])  # add option to group

                    # add line if not last option
                    if key != advanced_keys[tab_id][-1]:
                        groups[tab_id].add_widget(self.add_line())

                # add advanced options group to scrolls
                for tab_id in groups:
                    group_id = 'settings.advanced.' + section_id + '.' + tab_id
                    content_tabs[tab_id].addWidget(groups[tab_id])
                    self.window.ui.groups[group_id] = groups[tab_id]

            # add extra features buttons
            self.append_extra(content_tabs, section_id, options, fields)

            # add stretch to the end of every option tab
            for tab_id in content_tabs:
                content_tabs[tab_id].addStretch()

            # tabs or no tabs
            if len(content_tabs) > 1:
                # tabs
                tab_widget = QTabWidget()

                # sort to make general tab first if exists
                if "general" in content_tabs:
                    content_tabs = {"general": content_tabs.pop("general")} | content_tabs

                for tab_id in content_tabs:
                    if tab_id == "general":
                        name_key = trans("settings.section.tab.general")
                    else:
                        name_key = trans("settings.section." + section_id + "." + tab_id)
                    tab_name = trans(name_key)
                    scroll_widget = QWidget()
                    scroll_widget.setLayout(content_tabs[tab_id])
                    scroll_tabs[tab_id].setWidget(scroll_widget)
                    tab_widget.addTab(scroll_tabs[tab_id], tab_name)

                area = QVBoxLayout()
                area.addWidget(self.add_line())
                area.addWidget(tab_widget)
            else:
                # one scroll only
                scroll_widget = QWidget()
                scroll_widget.setLayout(content_tabs["general"])
                scroll_tabs["general"].setWidget(scroll_widget)

                area = QVBoxLayout()
                area.addWidget(self.add_line())
                area.addWidget(scroll_tabs["general"])

            area_widget = QWidget()
            area_widget.setLayout(area)

            # append to tab
            self.window.ui.tabs['settings.section'].addTab(
                area_widget,
                trans(sections[section_id]['label'])
            )

        # -----------------------

        self.window.ui.tabs['settings.section'].currentChanged.connect(
            lambda: self.window.controller.settings.set_by_tab(
                self.window.ui.tabs['settings.section'].currentIndex())
        )

        data = {}
        for section_id in sections:
            section = sections[section_id]
            data[section_id] = section

        # section list
        data_id = 'settings.section.list'
        self.window.ui.nodes[data_id] = SettingsSectionList(self.window, data_id)
        self.window.ui.models[data_id] = self.create_model(self.window)
        self.window.ui.nodes[data_id].setModel(self.window.ui.models[data_id])

        # update section list
        self.update_list(data_id, data)

        # set max width to list
        self.window.ui.nodes[data_id].setMinimumWidth(200)

        # splitter
        self.window.ui.splitters['dialog.settings'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['dialog.settings'].addWidget(self.window.ui.nodes[data_id])  # list
        self.window.ui.splitters['dialog.settings'].addWidget(self.window.ui.tabs['settings.section'])  # tabs
        self.window.ui.splitters['dialog.settings'].setStretchFactor(0, 2)
        self.window.ui.splitters['dialog.settings'].setStretchFactor(1, 5)
        self.window.ui.splitters['dialog.settings'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.ui.splitters['dialog.settings'])

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list + plugins tabs
        layout.addLayout(bottom)  # bottom buttons (save, defaults)

        self.window.ui.dialog['config.' + id] = SettingsDialog(self.window, id)
        self.window.ui.dialog['config.' + id].setLayout(layout)
        self.window.ui.dialog['config.' + id].setWindowTitle(trans('dialog.settings'))

        # restore current opened tab if idx is set
        if idx is not None:
            try:
                self.window.ui.tabs['settings.section'].setCurrentIndex(idx)
                self.window.controller.settings.set_by_tab(idx)
            except Exception as e:
                print('Failed restore settings tab: {}'.format(idx))
        else:
            self.window.controller.settings.set_by_tab(0)

    def extract_option_tabs(self, options: dict) -> list:
        """
        Get keys for option tabs

        :param options: settings options
        :return: list with keys
        """
        keys = []
        is_default = False
        for key in options:
            option = options[key]
            if 'tab' in option:
                tab = option['tab']
                if tab == "" or tab is None:
                    is_default = True
                if tab not in keys:
                    keys.append(tab)
            else:
                is_default = True

        # add default general tab if not exists
        if len(keys) == 0 or (is_default and "general" not in keys):
            keys.append("general")
        return keys

    def append_extra(self, content: dict, section_id: str, widgets: dict, options: dict):
        """
        Append extra fields in real-time

        :param content: dict with content tabs
        :param section_id: section id
        :param widgets: options dict
        :param options: options dist
        """
        if section_id == 'llama-index':
            content["update"].addWidget(self.add_line())
            self.window.controller.idx.settings.append(content, widgets, options)

    def append_tabs(self, section_id: str) -> list:
        """
        Append extra tabs in real-time

        :param section_id: section id
        :return: list with tabs
        """
        if section_id == 'llama-index':
            return self.window.controller.idx.settings.append_tabs()
        return []

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
            name = trans(data[n]['label'])
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1

    def refresh_list(self):
        """
        Refresh list

        :param id: ID of the list
        """
        sections = self.window.core.settings.get_sections()
        data = {}
        for section_id in sections:
            section = sections[section_id]
            data[section_id] = section

        data_id = 'settings.section.list'

        # update section list
        self.update_list(data_id, data)
