#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.29 18:00:00                  #
# ================================================== #

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QAction, QIcon
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget, QFrame, \
    QSplitter, QSizePolicy, QMenuBar, QCheckBox

from pygpt_net.ui.widget.dialog.assistant_store import AssistantVectorStoreDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.element.labels import UrlLabel
from pygpt_net.ui.widget.lists.assistant_store import AssistantVectorStoreEditorList
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans


class AssistantVectorStore:
    def __init__(self, window=None):
        """
        Assistant vector store editor dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "assistant.store"

    def setup(self, idx=None):
        """
        Setup vector store editor dialog

        :param idx: current model tab index
        """
        self.window.ui.nodes['assistant.store.btn.new'] = \
            QPushButton(trans("dialog.assistant.store.btn.new"))
        self.window.ui.nodes['assistant.store.btn.save'] = \
            QPushButton(trans("dialog.assistant.store.btn.save"))
        self.window.ui.nodes['assistant.store.btn.refresh_status'] = \
            QPushButton(QIcon(":/icons/reload.svg"), "")
        self.window.ui.nodes['assistant.store.btn.close'] = \
            QPushButton(trans("dialog.assistant.store.btn.close"))

        self.window.ui.nodes['assistant.store.btn.refresh_status'].setToolTip(
            trans("dialog.assistant.store.btn.refresh_status")
        )
        self.window.ui.nodes['assistant.store.btn.refresh_status'].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.window.ui.nodes['assistant.store.btn.upload.files'] = \
            QPushButton(trans("dialog.assistant.store.btn.upload.files"))
        self.window.ui.nodes['assistant.store.btn.upload.dir'] = \
            QPushButton(trans("dialog.assistant.store.btn.upload.dir"))

        self.window.ui.nodes['assistant.store.hide_thread'] = QCheckBox(trans("assistant.store.hide_threads"))
        self.window.ui.nodes['assistant.store.hide_thread'].setChecked(True)
        self.window.ui.nodes['assistant.store.hide_thread'].stateChanged.connect(
            lambda: self.window.controller.assistant.store.set_hide_thread(
                self.window.ui.nodes['assistant.store.hide_thread'].isChecked()
            )
        )
        if not self.window.core.config.get("assistant.store.hide_threads"):
            self.window.ui.nodes['assistant.store.hide_thread'].setChecked(False)

        self.window.ui.nodes['assistant.store.btn.new'].clicked.connect(
            lambda: self.window.controller.assistant.store.new()
        )
        self.window.ui.nodes['assistant.store.btn.save'].clicked.connect(
            lambda: self.window.controller.assistant.store.save()
        )
        self.window.ui.nodes['assistant.store.btn.close'].clicked.connect(
            lambda: self.window.controller.assistant.store.close()
        )
        self.window.ui.nodes['assistant.store.btn.refresh_status'].clicked.connect(
            lambda: self.window.controller.assistant.store.refresh_status()
        )
        self.window.ui.nodes['assistant.store.btn.upload.files'].clicked.connect(
            lambda: self.window.controller.assistant.batch.open_upload_files()
        )
        self.window.ui.nodes['assistant.store.btn.upload.dir'].clicked.connect(
            lambda: self.window.controller.assistant.batch.open_upload_dir()
        )

        # set enter key to save button
        self.window.ui.nodes['assistant.store.btn.new'].setAutoDefault(False)
        self.window.ui.nodes['assistant.store.btn.refresh_status'].setAutoDefault(False)
        self.window.ui.nodes['assistant.store.btn.save'].setAutoDefault(True)

        # footer buttons
        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['assistant.store.btn.close'])
        footer.addWidget(self.window.ui.nodes['assistant.store.btn.save'])

        # upload buttons
        upload_layout = QHBoxLayout()
        upload_layout.addWidget(self.window.ui.nodes['assistant.store.btn.refresh_status'])  # reload status btn
        upload_layout.addWidget(self.window.ui.nodes['assistant.store.btn.upload.files'])
        upload_layout.addWidget(self.window.ui.nodes['assistant.store.btn.upload.dir'])
        upload_layout.setContentsMargins(0, 0, 0, 0)

        # editor tabs
        self.window.ui.tabs['assistant.store'] = QTabWidget()

        # build settings tabs
        parent_id = "assistant.store"

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QVBoxLayout()

        # create config options entry if not exists
        if parent_id not in self.window.ui.config:
            self.window.ui.config[parent_id] = {}

        # get options
        options = copy.deepcopy(self.window.controller.assistant.store.get_options())
        widgets = self.build_widgets(options)
        advanced_keys = []
        for key in options:
            if 'advanced' in options[key] and options[key]['advanced']:
                advanced_keys.append(key)

        # apply settings widgets
        for key in widgets:
            self.window.ui.config[parent_id][key] = widgets[key]

        for key in widgets:
            if key in advanced_keys:  # hide advanced options
                continue
            content.addLayout(self.add_option(widgets[key], options[key]))  # add to scroll

        # append advanced options at the end
        if len(advanced_keys) > 0:
            group_id = 'assistant.store.advanced'
            self.window.ui.groups[group_id] = CollapsedGroup(self.window, group_id, None, False, None)
            self.window.ui.groups[group_id].box.setText(trans('settings.advanced.collapse'))
            for key in widgets:
                if key not in advanced_keys:  # ignore non-advanced options
                    continue

                option = self.add_option(widgets[key], options[key])  # build option
                self.window.ui.groups[group_id].add_layout(option)  # add option to group

            # add advanced options group to scroll
            content.addWidget(self.window.ui.groups[group_id])


        content.addLayout(upload_layout)  # upload buttons
        content.setContentsMargins(0, 0, 0, 0)

        # scroll widget
        scroll_widget = QWidget()
        scroll_widget.setLayout(content)
        scroll.setWidget(scroll_widget)

        area = QVBoxLayout()
        area.addWidget(scroll)
        area.setContentsMargins(0, 0, 0, 0)

        area_widget = QWidget()
        area_widget.setLayout(area)

        data = {}
        for store_id in self.window.core.assistants.store.items.keys():
            store = self.window.core.assistants.store.items[store_id]
            data[store_id] = store

        # storage list
        id = 'assistant.store.list'
        self.window.ui.nodes[id] = AssistantVectorStoreEditorList(self.window, id)
        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        # left widget
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.window.ui.nodes['assistant.store.btn.new'])
        left_layout.addWidget(self.window.ui.nodes[id])
        left_layout.addWidget(self.window.ui.nodes['assistant.store.hide_thread'])

        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # update models list
        self.update_list(id, data)

        # set max width to list
        self.window.ui.nodes[id].setMinimumWidth(250)

        # splitter
        self.window.ui.splitters['dialog.assistant.store'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['dialog.assistant.store'].addWidget(left_widget)  # list
        self.window.ui.splitters['dialog.assistant.store'].addWidget(area_widget)  # tabs
        self.window.ui.splitters['dialog.assistant.store'].setStretchFactor(0, 2)
        self.window.ui.splitters['dialog.assistant.store'].setStretchFactor(1, 5)
        self.window.ui.splitters['dialog.assistant.store'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.ui.splitters['dialog.assistant.store'])
        main_layout.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list + model tabs
        layout.addLayout(footer)  # bottom buttons (save, defaults)

        # add menu
        layout.setMenuBar(self.setup_menu())

        self.window.ui.dialog[self.dialog_id] = AssistantVectorStoreDialog(self.window, self.dialog_id)
        self.window.ui.dialog[self.dialog_id].setLayout(layout)
        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.assistant.store'))

        # restore current opened tab if idx is set
        if idx is not None:
            try:
                self.window.controller.assistant.store.set_by_tab(idx)
            except Exception as e:
                print('Failed restore store editor tab: {}'.format(idx))
        else:
            if self.window.controller.assistant.store.current is None:
                self.window.controller.assistant.store.set_by_tab(0)

    def setup_menu(self) -> QMenuBar:
        """
        Setup menu bar

        :return: QMenuBar
        """
        self.actions = {}
        self.menu_bar = QMenuBar()

        self.menu = {}
        self.menu["current"] = self.menu_bar.addMenu(trans("dialog.assistant.store.menu.current"))
        self.menu["all"] = self.menu_bar.addMenu(trans("dialog.assistant.store.menu.all"))

        # --------------------------------------------

        # import files (current)
        self.actions["current.import_files"] = QAction(QIcon(":/icons/download.svg"),
                                                   trans("dialog.assistant.store.menu.current.import_files"))
        self.actions["current.import_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.import_store_files(
                self.window.controller.assistant.store.current  # current selected store
            )
        )

        # refresh (current)
        self.actions["current.refresh_store"] = QAction(QIcon(":/icons/reload.svg"),
                                                     trans("dialog.assistant.store.menu.current.refresh_store"))
        self.actions["current.refresh_store"].triggered.connect(
            lambda: self.window.controller.assistant.store.refresh_status()
        )

        # clear files (current, local)
        self.actions["current.clear_files"] = QAction(QIcon(":/icons/close.svg"),
                                                  trans("dialog.assistant.store.menu.current.clear_files"))
        self.actions["current.clear_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.clear_store_files(
                self.window.controller.assistant.store.current  # current selected store
            )
        )

        # truncate files (current, local + remote)
        self.actions["current.truncate_files"] = QAction(QIcon(":/icons/delete.svg"),
                                                     trans("dialog.assistant.store.menu.current.truncate_files"))
        self.actions["current.truncate_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.truncate_store_files(
                self.window.controller.assistant.store.current  # current selected store
            )
        )

        # delete (current, local + remote)
        self.actions["current.delete"] = QAction(QIcon(":/icons/delete.svg"),
                                                         trans("dialog.assistant.store.menu.current.delete"))
        self.actions["current.delete"].triggered.connect(
            lambda: self.window.controller.assistant.store.delete(
                self.window.controller.assistant.store.current  # current selected store
            )
        )

        # --------------------------------------------

        # import all (stores + files)
        self.actions["all.import_all"] = QAction(QIcon(":/icons/download.svg"), trans("dialog.assistant.store.menu.all.import_all"))
        self.actions["all.import_all"].triggered.connect(
            lambda: self.window.controller.assistant.batch.import_stores()
        )

        # import files (all)
        self.actions["all.import_files"] = QAction(QIcon(":/icons/download.svg"),
                                             trans("dialog.assistant.store.menu.all.import_files"))
        self.actions["all.import_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.import_files()
        )

        # refresh (local)
        self.actions["all.refresh_stores"] = QAction(QIcon(":/icons/reload.svg"),
                                               trans("dialog.assistant.store.menu.all.refresh_store"))
        self.actions["all.refresh_stores"].triggered.connect(
            lambda: self.window.controller.assistant.batch.refresh_stores()
        )

        # clear stores (all, local)
        self.actions["all.clear_stores"] = QAction(QIcon(":/icons/close.svg"),
                                                  trans("dialog.assistant.store.menu.all.clear_store"))
        self.actions["all.clear_stores"].triggered.connect(
            lambda: self.window.controller.assistant.batch.clear_stores()
        )

        # clear files (all, local)
        self.actions["all.clear_files"] = QAction(QIcon(":/icons/close.svg"),
                                               trans("dialog.assistant.store.menu.all.clear_files"))
        self.actions["all.clear_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.clear_files()
        )

        # truncate stores (all, local + remote)
        self.actions["all.truncate_stores"] = QAction(QIcon(":/icons/delete.svg"), trans("dialog.assistant.store.menu.all.truncate_store"))
        self.actions["all.truncate_stores"].triggered.connect(
            lambda: self.window.controller.assistant.batch.truncate_stores()
        )

        # truncate files (all, local + remote)
        self.actions["all.truncate_files"] = QAction(QIcon(":/icons/delete.svg"), trans("dialog.assistant.store.menu.all.truncate_files"))
        self.actions["all.truncate_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.truncate_files()
        )

        # current
        self.menu["current"].addAction(self.actions["current.import_files"])
        self.menu["current"].addAction(self.actions["current.refresh_store"])
        self.menu["current"].addAction(self.actions["current.clear_files"])
        self.menu["current"].addAction(self.actions["current.truncate_files"])
        self.menu["current"].addAction(self.actions["current.delete"])

        # all
        self.menu["all"].addAction(self.actions["all.import_all"])
        self.menu["all"].addAction(self.actions["all.import_files"])
        self.menu["all"].addAction(self.actions["all.refresh_stores"])
        self.menu["all"].addAction(self.actions["all.clear_stores"])
        self.menu["all"].addAction(self.actions["all.clear_files"])
        self.menu["all"].addAction(self.actions["all.truncate_stores"])
        self.menu["all"].addAction(self.actions["all.truncate_files"])

        return self.menu_bar

    def build_widgets(self, options: dict) -> dict:
        """
        Build settings options widgets

        :param options: model options
        :return: dict of widgets
        """
        parent = "model"
        widgets = {}

        for key in options:
            option = options[key]
            option['id'] = key
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
            elif option['type'] == 'bool_list':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCheckboxList(self.window, parent, key, option)  # checkbox list
            elif option['type'] == 'dict':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionDict(self.window, parent, key, option)  # dictionary
                widgets[key].setMinimumHeight(200)
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

    def add_option(self, widget: QWidget, option: dict) -> QVBoxLayout:
        """
        Append option widget to layout

        :param widget: widget instance
        :param option: option dict
        :return: QVBoxLayout
        """
        one_column_types = ['textarea', 'dict', 'bool']
        key = option['id']
        label = trans(option['label'])
        label_key = 'model.' + key + '.label'
        desc = None
        desc_key = None

        if option['type'] != 'bool':
            self.window.ui.nodes[label_key] = QLabel(label)
            self.window.ui.nodes[label_key].setStyleSheet("font-weight: bold;")

        if "description" in option:
            desc = trans(option['description'])
            desc_key = 'model.' + key + '.desc'

        # 2-columns layout
        if option['type'] not in one_column_types:
            cols = QHBoxLayout()
            cols.addWidget(self.window.ui.nodes[label_key])  # disable label in bool type
            cols.addWidget(widget)

            cols_widget = QWidget()
            cols_widget.setLayout(cols)
            cols_widget.setMaximumHeight(90)

            layout = QVBoxLayout()
            layout.addWidget(cols_widget)
        else:
            # 1-column layout: textarea and dict fields
            layout = QVBoxLayout()
            if option['type'] != 'bool':
                layout.addWidget(self.window.ui.nodes[label_key])
            else:
                widget.box.setText(label)  # set checkbox label
            layout.addWidget(widget)

        if desc:
            self.window.ui.nodes[desc_key] = QLabel(desc)
            self.window.ui.nodes[desc_key].setWordWrap(True)
            self.window.ui.nodes[desc_key].setMaximumHeight(40)
            self.window.ui.nodes[desc_key].setStyleSheet("font-size: 10px;")
            layout.addWidget(self.window.ui.nodes[desc_key])

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
        if id not in self.window.ui.models:
            return
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            name = data[n].name
            extra = ""
            if name == "" or name is None:
                if self.window.core.config.get("assistant.store.hide_threads"):
                    continue
                name = data[n].id
            if data[n].num_files > 0:
                extra += "{} {}".format(data[n].num_files, trans("assistant.store.files.suffix"))
            if data[n].usage_bytes > 0:
                extra += " - {}".format(self.window.core.filesystem.sizeof_fmt(data[n].usage_bytes))
            if extra != "":
                name += " ({})".format(extra)
            self.window.ui.models[id].insertRow(i)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
