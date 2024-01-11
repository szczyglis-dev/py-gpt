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
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QSizePolicy

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.settings import SettingsDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
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

    def setup(self):
        """Setup settings dialog"""
        id = "settings"
        path = self.window.core.config.path

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

        # advanced options keys
        advanced_keys = []

        # get settings options config
        fields = self.window.controller.settings.editor.get_options()
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
            elif fields[key]['type'] == 'combo':
                options[key] = self.add_option(widgets[key], fields[key])  # combobox

        fixed_keys = [
            'api_key',
            'organization_key'
        ]
        self.window.ui.nodes['settings.api_key.label'].setMinimumHeight(60)

        # prepare scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        line = self.add_line()
        content = QVBoxLayout()

        # API keys at the top
        for key in fixed_keys:
            content.addLayout(options[key])
            if 'urls' in fields[key]:
                urls_widget = self.add_urls(fields[key]['urls'], Qt.AlignCenter)
                content.addWidget(urls_widget)

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

            line = self.add_line()
            content.addWidget(line)

        # append advanced options at the end
        if len(advanced_keys) > 0:
            group_id = 'settings.advanced'
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

        widget = QWidget()
        widget.setLayout(content)
        scroll.setWidget(widget)

        layout = QVBoxLayout()
        layout.addWidget(scroll)  # options widgets
        layout.addLayout(bottom)  # footer buttons (save, load defaults)

        self.window.ui.dialog['config.' + id] = SettingsDialog(self.window, id)
        self.window.ui.dialog['config.' + id].setLayout(layout)
        self.window.ui.dialog['config.' + id].setWindowTitle(trans('dialog.settings'))
