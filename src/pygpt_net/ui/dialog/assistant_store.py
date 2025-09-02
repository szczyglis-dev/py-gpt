#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 22:00:00                  #
# ================================================== #

import copy

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QStandardItemModel, QAction, QIcon
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget, QFrame, \
    QSplitter, QSizePolicy, QMenuBar, QCheckBox, QMenu, QListView

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
        ui = self.window.ui
        nodes = ui.nodes
        models = ui.models
        splitters = ui.splitters
        controller = self.window.controller
        core = self.window.core

        nodes['assistant.store.btn.new'] = QPushButton(trans("dialog.assistant.store.btn.new"))
        nodes['assistant.store.btn.save'] = QPushButton(trans("dialog.assistant.store.btn.save"))
        nodes['assistant.store.btn.refresh_status'] = QPushButton(QIcon(":/icons/reload.svg"), "")
        nodes['assistant.store.btn.close'] = QPushButton(trans("dialog.assistant.store.btn.close"))

        nodes['assistant.store.btn.refresh_status'].setToolTip(
            trans("dialog.assistant.store.btn.refresh_status")
        )
        nodes['assistant.store.btn.refresh_status'].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        nodes['assistant.store.btn.upload.files'] = QPushButton(trans("dialog.assistant.store.btn.upload.files"))
        nodes['assistant.store.btn.upload.dir'] = QPushButton(trans("dialog.assistant.store.btn.upload.dir"))

        nodes['assistant.store.hide_thread'] = QCheckBox(trans("assistant.store.hide_threads"))
        nodes['assistant.store.hide_thread'].setChecked(bool(core.config.get("assistant.store.hide_threads")))
        nodes['assistant.store.hide_thread'].toggled.connect(
            controller.assistant.store.set_hide_thread
        )

        nodes['assistant.store.btn.new'].clicked.connect(controller.assistant.store.new)
        nodes['assistant.store.btn.save'].clicked.connect(controller.assistant.store.save)
        nodes['assistant.store.btn.close'].clicked.connect(controller.assistant.store.close)
        nodes['assistant.store.btn.refresh_status'].clicked.connect(controller.assistant.store.refresh_status)
        nodes['assistant.store.btn.upload.files'].clicked.connect(controller.assistant.batch.open_upload_files)
        nodes['assistant.store.btn.upload.dir'].clicked.connect(controller.assistant.batch.open_upload_dir)

        nodes['assistant.store.btn.new'].setAutoDefault(False)
        nodes['assistant.store.btn.refresh_status'].setAutoDefault(False)
        nodes['assistant.store.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        footer.addWidget(nodes['assistant.store.btn.close'])
        footer.addWidget(nodes['assistant.store.btn.save'])

        upload_layout = QHBoxLayout()
        upload_layout.addWidget(nodes['assistant.store.btn.refresh_status'])
        upload_layout.addWidget(nodes['assistant.store.btn.upload.files'])
        upload_layout.addWidget(nodes['assistant.store.btn.upload.dir'])
        upload_layout.setContentsMargins(0, 0, 0, 0)

        ui.tabs['assistant.store'] = QTabWidget()

        parent_id = "assistant.store"

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QVBoxLayout()

        if parent_id not in ui.config:
            ui.config[parent_id] = {}

        options = copy.deepcopy(controller.assistant.store.get_options())
        widgets = self.build_widgets(options)
        advanced_keys = [k for k, v in options.items() if v.get('advanced')]

        for key, w in widgets.items():
            ui.config[parent_id][key] = w

        for key in widgets:
            if key in advanced_keys:
                continue
            content.addLayout(self.add_option(widgets[key], options[key]))

        if advanced_keys:
            group_id = 'assistant.store.advanced'
            ui.groups[group_id] = CollapsedGroup(self.window, group_id, None, False, None)
            ui.groups[group_id].box.setText(trans('settings.advanced.collapse'))
            for key in widgets:
                if key not in advanced_keys:
                    continue
                option = self.add_option(widgets[key], options[key])
                ui.groups[group_id].add_layout(option)
            content.addWidget(ui.groups[group_id])

        content.addLayout(upload_layout)
        content.setContentsMargins(0, 0, 0, 0)

        scroll_widget = QWidget()
        scroll_widget.setLayout(content)
        scroll.setWidget(scroll_widget)

        area = QVBoxLayout()
        area.addWidget(scroll)
        area.setContentsMargins(0, 0, 0, 0)

        area_widget = QWidget()
        area_widget.setLayout(area)

        list_id = 'assistant.store.list'
        nodes[list_id] = AssistantVectorStoreEditorList(self.window, list_id)
        models[list_id] = self.create_model(self.window)
        nodes[list_id].setModel(models[list_id])
        nodes[list_id].setMinimumWidth(250)

        left_layout = QVBoxLayout()
        left_layout.addWidget(nodes['assistant.store.btn.new'])
        left_layout.addWidget(nodes[list_id])
        left_layout.addWidget(nodes['assistant.store.hide_thread'])
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        self.update_list(list_id, core.assistants.store.items)

        # ==================== ADDED: Files panel on the right ====================
        files_panel = QVBoxLayout()
        files_label = QLabel("Files")
        files_label.setStyleSheet("font-weight: bold;")
        files_panel.addWidget(files_label)

        files_list_id = 'assistant.store.files.list'
        nodes[files_list_id] = QListView()
        nodes[files_list_id].setEditTriggers(QListView.NoEditTriggers)
        nodes[files_list_id].setSelectionMode(QListView.SingleSelection)
        nodes[files_list_id].setContextMenuPolicy(Qt.CustomContextMenu)
        nodes[files_list_id].customContextMenuRequested.connect(self.on_files_context_menu)

        models[files_list_id] = self.create_model(self.window)
        nodes[files_list_id].setModel(models[files_list_id])
        nodes[files_list_id].setMinimumWidth(280)

        files_panel.addWidget(nodes[files_list_id])
        files_panel.setContentsMargins(6, 6, 6, 6)
        files_widget = QWidget()
        files_widget.setLayout(files_panel)
        # ========================================================================

        splitters['dialog.assistant.store'] = QSplitter(Qt.Horizontal)
        splitters['dialog.assistant.store'].addWidget(left_widget)

        splitters['dialog.assistant.store.right'] = QSplitter(Qt.Horizontal)
        splitters['dialog.assistant.store.right'].addWidget(area_widget)
        splitters['dialog.assistant.store.right'].addWidget(files_widget)
        splitters['dialog.assistant.store.right'].setStretchFactor(0, 7)
        splitters['dialog.assistant.store.right'].setStretchFactor(1, 3)

        splitters['dialog.assistant.store'].addWidget(splitters['dialog.assistant.store.right'])
        splitters['dialog.assistant.store'].setStretchFactor(0, 2)
        splitters['dialog.assistant.store'].setStretchFactor(1, 8)
        splitters['dialog.assistant.store'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout()
        main_layout.addWidget(splitters['dialog.assistant.store'])
        main_layout.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addLayout(footer)

        layout.setMenuBar(self.setup_menu())

        ui.dialog[self.dialog_id] = AssistantVectorStoreDialog(self.window, self.dialog_id)
        ui.dialog[self.dialog_id].setLayout(layout)
        ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.assistant.store'))

        if idx is not None:
            try:
                controller.assistant.store.set_by_tab(idx)
            except Exception as e:
                print('Failed restore store editor tab: {}'.format(idx))
        else:
            if controller.assistant.store.current is None:
                controller.assistant.store.set_by_tab(0)

        try:
            controller.assistant.store.update_files_list()
        except Exception:
            pass

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

        self.actions["current.import_files"] = QAction(QIcon(":/icons/download.svg"),
                                                   trans("dialog.assistant.store.menu.current.import_files"),
                                                   self.menu_bar)
        self.actions["current.import_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.import_store_files(
                self.window.controller.assistant.store.current
            )
        )

        self.actions["current.refresh_store"] = QAction(QIcon(":/icons/reload.svg"),
                                                     trans("dialog.assistant.store.menu.current.refresh_store"),
                                                     self.menu_bar)
        self.actions["current.refresh_store"].triggered.connect(
            self.window.controller.assistant.store.refresh_status
        )

        self.actions["current.clear_files"] = QAction(QIcon(":/icons/close.svg"),
                                                  trans("dialog.assistant.store.menu.current.clear_files"),
                                                  self.menu_bar)
        self.actions["current.clear_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.clear_store_files(
                self.window.controller.assistant.store.current
            )
        )

        self.actions["current.truncate_files"] = QAction(QIcon(":/icons/delete.svg"),
                                                     trans("dialog.assistant.store.menu.current.truncate_files"),
                                                     self.menu_bar)
        self.actions["current.truncate_files"].triggered.connect(
            lambda: self.window.controller.assistant.batch.truncate_store_files(
                self.window.controller.assistant.store.current
            )
        )

        self.actions["current.delete"] = QAction(QIcon(":/icons/delete.svg"),
                                                         trans("dialog.assistant.store.menu.current.delete"),
                                                         self.menu_bar)
        self.actions["current.delete"].triggered.connect(
            lambda: self.window.controller.assistant.store.delete(
                self.window.controller.assistant.store.current
            )
        )

        self.actions["all.import_all"] = QAction(QIcon(":/icons/download.svg"),
                                                 trans("dialog.assistant.store.menu.all.import_all"),
                                                 self.menu_bar)
        self.actions["all.import_all"].triggered.connect(
            self.window.controller.assistant.batch.import_stores
        )

        self.actions["all.import_files"] = QAction(QIcon(":/icons/download.svg"),
                                             trans("dialog.assistant.store.menu.all.import_files"),
                                             self.menu_bar)
        self.actions["all.import_files"].triggered.connect(
            self.window.controller.assistant.batch.import_files
        )

        self.actions["all.refresh_stores"] = QAction(QIcon(":/icons/reload.svg"),
                                               trans("dialog.assistant.store.menu.all.refresh_store"),
                                               self.menu_bar)
        self.actions["all.refresh_stores"].triggered.connect(
            self.window.controller.assistant.batch.refresh_stores
        )

        self.actions["all.clear_stores"] = QAction(QIcon(":/icons/close.svg"),
                                                  trans("dialog.assistant.store.menu.all.clear_store"),
                                                  self.menu_bar)
        self.actions["all.clear_stores"].triggered.connect(
            self.window.controller.assistant.batch.clear_stores
        )

        self.actions["all.clear_files"] = QAction(QIcon(":/icons/close.svg"),
                                               trans("dialog.assistant.store.menu.all.clear_files"),
                                               self.menu_bar)
        self.actions["all.clear_files"].triggered.connect(
            self.window.controller.assistant.batch.clear_files
        )

        self.actions["all.truncate_stores"] = QAction(QIcon(":/icons/delete.svg"),
                                                      trans("dialog.assistant.store.menu.all.truncate_store"),
                                                      self.menu_bar)
        self.actions["all.truncate_stores"].triggered.connect(
            self.window.controller.assistant.batch.truncate_stores
        )

        self.actions["all.truncate_files"] = QAction(QIcon(":/icons/delete.svg"),
                                                     trans("dialog.assistant.store.menu.all.truncate_files"),
                                                     self.menu_bar)
        self.actions["all.truncate_files"].triggered.connect(
            self.window.controller.assistant.batch.truncate_files
        )

        self.menu["current"].addAction(self.actions["current.import_files"])
        self.menu["current"].addAction(self.actions["current.refresh_store"])
        self.menu["current"].addAction(self.actions["current.clear_files"])
        self.menu["current"].addAction(self.actions["current.truncate_files"])
        self.menu["current"].addAction(self.actions["current.delete"])

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
            if option['type'] == 'text' or option['type'] == 'int' or option['type'] == 'float':
                if 'slider' in option and option['slider'] \
                        and (option['type'] == 'int' or option['type'] == 'float'):
                    widgets[key] = OptionSlider(self.window, parent, key, option)
                else:
                    if 'secret' in option and option['secret']:
                        widgets[key] = PasswordInput(self.window, parent, key, option)
                    else:
                        widgets[key] = OptionInput(self.window, parent, key, option)
            elif option['type'] == 'textarea':
                widgets[key] = OptionTextarea(self.window, parent, key, option)
            elif option['type'] == 'bool':
                widgets[key] = OptionCheckbox(self.window, parent, key, option)
            elif option['type'] == 'bool_list':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCheckboxList(self.window, parent, key, option)
            elif option['type'] == 'dict':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionDict(self.window, parent, key, option)
                widgets[key].setMinimumHeight(200)
            elif option['type'] == 'combo':
                self.window.controller.config.placeholder.apply(option)
                widgets[key] = OptionCombo(self.window, parent, key, option)

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

        if option['type'] not in one_column_types:
            cols = QHBoxLayout()
            cols.addWidget(self.window.ui.nodes[label_key])
            cols.addWidget(widget)

            cols_widget = QWidget()
            cols_widget.setLayout(cols)
            cols_widget.setMaximumHeight(90)

            layout = QVBoxLayout()
            layout.addWidget(cols_widget)
        else:
            layout = QVBoxLayout()
            if option['type'] != 'bool':
                layout.addWidget(self.window.ui.nodes[label_key])
            else:
                widget.box.setText(label)
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
        models = self.window.ui.models
        if id not in models:
            return
        model = models[id]
        hide_threads = bool(self.window.core.config.get("assistant.store.hide_threads"))
        suffix = trans("assistant.store.files.suffix")

        names = []
        for n, store in data.items():
            num_files = store.get_file_count()
            name = store.name
            extras = []
            if not name:
                if hide_threads:
                    continue
                name = store.id
            if num_files > 0:
                extras.append(f"{num_files} {suffix}")
            if store.usage_bytes > 0:
                extras.append(self.window.core.filesystem.sizeof_fmt(store.usage_bytes))
            if extras:
                name = f"{name} ({' - '.join(extras)})"
            names.append(name)

        model.setRowCount(len(names))
        for i, name in enumerate(names):
            model.setData(model.index(i, 0), name)

    # ==================== files context menu handler ====================
    def on_files_context_menu(self, pos: QPoint):
        """
        Context menu for the files list: provides Delete action.
        """
        view_id = 'assistant.store.files.list'
        if view_id not in self.window.ui.nodes:
            return
        view = self.window.ui.nodes[view_id]
        index = view.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        menu = QMenu(view)
        act_delete = QAction(QIcon(":/icons/delete.svg"), trans("assistant.store.menu.file.delete") if hasattr(self.window, 'tr') else "Delete", view)
        act_delete.triggered.connect(lambda r=row: self.window.controller.assistant.store.delete_file_by_idx(r))
        menu.addAction(act_delete)
        menu.exec(view.mapToGlobal(pos))