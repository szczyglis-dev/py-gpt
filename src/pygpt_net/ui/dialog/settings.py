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
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QSizePolicy, \
    QTabWidget

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.settings import SettingsDialog
from pygpt_net.ui.widget.element.button import ContextMenuButton
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

        fixed_keys = [
            'api_key',
            'organization_key'
        ]

        # build settings tabs
        for section_id in sections:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QVBoxLayout()

            # advanced options keys
            advanced_keys = []

            # get settings options config
            fields = self.window.controller.settings.editor.get_options(section_id)
            for key in fields:
                if 'advanced' in fields[key] and fields[key]['advanced']:
                    advanced_keys.append(key)

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
                    self.window.ui.dialogs.register_dictionary(key, parent="config", option=fields[key])
                elif fields[key]['type'] == 'combo':
                    options[key] = self.add_option(widgets[key], fields[key])  # combobox

            self.window.ui.nodes['settings.api_key.label'].setMinimumHeight(60)

            # prepare scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)

            content = QVBoxLayout()
            is_fixed = False

            for key in fixed_keys:
                if key in options:
                    is_fixed = True
                    content.addLayout(options[key])
                    if 'urls' in fields[key]:
                        urls_widget = self.add_urls(fields[key]['urls'], Qt.AlignCenter)
                        content.addWidget(urls_widget)

            if is_fixed:
                line = self.add_line()
                content.addWidget(line)

            # append widgets options layouts to scroll area
            for key in options:
                option = options[key]

                # hide advanced options
                if key in advanced_keys:
                    continue

                # prevent already added options from being added again
                if key in fixed_keys:
                    continue

                # add option
                content.addLayout(option)

                # append URLs
                if 'urls' in fields[key]:
                    urls_widget = self.add_urls(fields[key]['urls'])
                    content.addWidget(urls_widget)

                # check if not last option
                if key != list(options.keys())[-1] or len(advanced_keys) > 0:
                    line = self.add_line()
                    content.addWidget(line)

            # append advanced options at the end
            if len(advanced_keys) > 0:
                group_id = 'settings.advanced.' + section_id
                self.window.ui.groups[group_id] = CollapsedGroup(self.window, group_id, None, False, None)
                self.window.ui.groups[group_id].box.setText(trans('settings.advanced.collapse'))
                for key in options:
                    # hide non-advanced options
                    if key not in advanced_keys:
                        continue

                    # add option to group
                    option = options[key]
                    self.window.ui.groups[group_id].add_layout(option)

                    # add line if not last option
                    if key != advanced_keys[-1]:
                        line = self.add_line()
                        self.window.ui.groups[group_id].add_widget(line)

                content.addWidget(self.window.ui.groups[group_id])

            line = self.add_line()

            # add extra features buttons
            self.append_extra(content, section_id, options, fields)

            content.addStretch()
            content.addWidget(line)

            widget = QWidget()
            widget.setLayout(content)
            scroll.setWidget(widget)

            area = QVBoxLayout()
            area.addWidget(scroll)

            area_widget = QWidget()
            area_widget.setLayout(area)

            # append to tab
            self.window.ui.tabs['settings.section'].addTab(area_widget, trans(sections[section_id]['label']))

        self.window.ui.tabs['settings.section'].currentChanged.connect(
            lambda: self.window.controller.settings.set_by_tab(
                self.window.ui.tabs['settings.section'].currentIndex()))

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
        self.window.ui.nodes[data_id].setMaximumWidth(250)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.ui.nodes[data_id])
        main_layout.addWidget(self.window.ui.tabs['settings.section'])

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

    def append_extra(self, content, section_id, options, fields):
        if section_id == 'llama-index':
            line = self.add_line()
            content.addWidget(line)
            self.window.controller.idx.settings.append(content, options, fields)

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
