#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.18 18:00:00                  #
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
        options_get = self.window.controller.settings.editor.get_options

        # build settings tabs
        for section_id in sections:
            content_tabs = {}
            scroll_tabs = {}
            advanced_keys = {}  # advanced options keys
            first_tab = "general"

            # get settings options for section
            fields = options_get(section_id)
            is_general = False

            tab_by_key = {}
            for key, field in fields.items():
                if 'tab' in field:
                    tab = field['tab']
                    if tab is not None:
                        if first_tab == "general":
                            first_tab = tab
                        if isinstance(tab, str) and tab.lower() == "general":
                            is_general = True
                else:
                    is_general = True

                tab_id = field['tab'] if field.get('tab') not in (None, "") else "general"
                tab_by_key[key] = tab_id

                if field.get('advanced'):
                    advanced_keys.setdefault(tab_id, []).append(key)

            # extract tab ids, general is default
            tab_ids = self.extract_option_tabs(fields)
            extra_tabs = self.append_tabs(section_id)
            if extra_tabs:
                tab_ids += extra_tabs
            for tab_id in tab_ids:
                content_tabs[tab_id] = QVBoxLayout()
                s = QScrollArea()
                s.setWidgetResizable(True)
                scroll_tabs[tab_id] = s

            # build settings widgets
            widgets = self.build_widgets(self.id, fields)

            # apply settings widgets
            self.window.ui.config[self.id].update(widgets)

            # apply widgets to layouts
            options = {}
            add_option = self.add_option
            add_row_option = self.add_row_option
            add_raw_option = self.add_raw_option
            register_dictionary = self.window.ui.dialogs.register_dictionary

            for key, widget in widgets.items():
                f = fields[key]
                t = f['type']
                if t in ('text', 'int', 'float', 'combo', 'bool_list'):
                    options[key] = add_option(widget, f)
                elif t in ('textarea', 'dict'):
                    options[key] = add_row_option(widget, f)
                    if t == 'dict':
                        # register dict to editor:
                        register_dictionary(
                            key,
                            parent="config",
                            option=f,
                        )
                elif t == 'bool':
                    options[key] = add_raw_option(widget, f)

            # self.window.ui.nodes['settings.api_key.label'].setMinimumHeight(60)

            # append widgets options layouts to scroll area
            advanced_membership = {tid: set(keys) for tid, keys in advanced_keys.items()}
            last_option_key = next(reversed(options)) if options else None

            for key, option in options.items():
                tab_id = tab_by_key.get(key, "general")

                # hide advanced options
                if tab_id in advanced_membership and key in advanced_membership[tab_id]:
                    continue

                content_tabs[tab_id].addLayout(option)

                # append URLs
                if 'urls' in fields[key]:
                    content_tabs[tab_id].addWidget(self.add_urls(fields[key]['urls']))

                # check if not last option
                if key != last_option_key or tab_id in advanced_keys:
                    content_tabs[tab_id].addWidget(self.add_line())

            # append advanced options at the end
            if len(advanced_keys) > 0:
                groups = {}
                for tab_id, adv_list in advanced_keys.items():
                    if not adv_list:
                        continue

                    group_id = 'settings.advanced.' + section_id + '.' + tab_id
                    groups[tab_id] = CollapsedGroup(self.window, group_id, None, False, None)
                    groups[tab_id].box.setText(trans('settings.advanced.collapse'))

                    last_idx = len(adv_list) - 1
                    for idx, key in enumerate(adv_list):
                        groups[tab_id].add_layout(options[key])
                        if idx != last_idx:
                            groups[tab_id].add_widget(self.add_line())

                # add advanced options group to scrolls
                for tab_id, group in groups.items():
                    group_id = 'settings.advanced.' + section_id + '.' + tab_id
                    content_tabs[tab_id].addWidget(group)
                    self.window.ui.groups[group_id] = group

            # add extra features buttons
            self.append_extra(content_tabs, section_id, options, fields)

            # add stretch to the end of every option tab
            for tab_id in content_tabs:
                content_tabs[tab_id].addStretch()

            # tabs or no tabs
            if len(content_tabs) > 1 or (len(content_tabs) == 1 and not is_general):
                # tabs
                tab_widget = QTabWidget()

                # sort to make general tab first if exists
                tab_order = (["general"] + [tid for tid in content_tabs if
                                            tid != "general"]) if "general" in content_tabs else list(content_tabs)

                for tab_id in tab_order:
                    if tab_id == "general":
                        name_key = trans("settings.section.tab.general")
                    else:
                        name_key = trans("settings.section." + section_id + "." + tab_id)
                    tab_name = name_key
                    trans_key = name_key.replace(" ", "_").lower()
                    translated = trans(trans_key)
                    if translated != trans_key:
                        tab_name = translated
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
                scroll_widget.setLayout(content_tabs[first_tab])
                scroll_tabs[first_tab].setWidget(scroll_widget)

                area = QVBoxLayout()
                area.addWidget(self.add_line())
                area.addWidget(scroll_tabs[first_tab])

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
        seen = set()
        is_default = False

        for option in options.values():
            if 'tab' in option:
                tab = option['tab']
                if tab == "" or tab is None:
                    is_default = True
                try:
                    if tab not in seen:
                        seen.add(tab)
                        keys.append(tab)
                except TypeError:
                    if tab not in keys:
                        keys.append(tab)
            else:
                is_default = True

        if not keys or (is_default and "general" not in keys):
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
