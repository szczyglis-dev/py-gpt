# ui/dialog/remote_store.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 17:00:00                  #
# ================================================== #

import copy

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QStandardItemModel, QAction, QIcon
from PySide6.QtWidgets import (
    QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget,
    QFrame, QSplitter, QSizePolicy, QMenuBar, QCheckBox, QMenu, QListView
)

from pygpt_net.ui.widget.dialog.remote_store import RemoteStoreDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.element.labels import UrlLabel, DescLabel
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList
from pygpt_net.ui.widget.option.combo import OptionCombo, NoScrollCombo
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans


class RemoteStore:
    def __init__(self, window=None):
        """
        Remote Store editor dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "remote_store"

    # ======================== Build UI ========================

    def setup(self):
        ui = self.window.ui
        nodes = ui.nodes
        models = ui.models
        splitters = ui.splitters
        controller = self.window.controller

        nodes['remote_store.btn.new'] = QPushButton(trans("dialog.remote_store.btn.new"))
        nodes['remote_store.btn.save'] = QPushButton(trans("dialog.remote_store.btn.save"))
        nodes['remote_store.btn.refresh_status'] = QPushButton(QIcon(":/icons/reload.svg"), "")
        nodes['remote_store.btn.close'] = QPushButton(trans("dialog.remote_store.btn.close"))

        nodes['remote_store.btn.refresh_status'].setToolTip(
            trans("dialog.remote_store.btn.refresh_status")
        )
        nodes['remote_store.btn.refresh_status'].setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        nodes['remote_store.btn.upload.files'] = QPushButton(trans("dialog.remote_store.btn.upload.files"))
        nodes['remote_store.btn.upload.dir'] = QPushButton(trans("dialog.remote_store.btn.upload.dir"))

        # Provider selector
        providers = controller.remote_store.get_providers()
        nodes['remote_store.provider.label'] = QLabel(trans("remote_store.provider"))
        nodes['remote_store.provider.desc'] = DescLabel(trans("remote_store.provider.desc"))
        nodes['remote_store.provider.desc'].setWordWrap(True)
        nodes['remote_store.provider.desc'].setMaximumHeight(40)
        nodes['remote_store.provider.desc'].setStyleSheet("font-size: 10px;")
        nodes['remote_store.provider.combo'] = NoScrollCombo()
        for key in providers:
            provider = providers[key]
            nodes['remote_store.provider.combo'].addItem(provider, key)

        nodes['remote_store.hide_thread'] = QCheckBox(trans("remote_store.hide_threads"))

        # Bindings (unified controller only; no per-provider refs)
        nodes['remote_store.btn.new'].clicked.connect(controller.remote_store.new)
        nodes['remote_store.btn.save'].clicked.connect(controller.remote_store.save_btn)
        nodes['remote_store.btn.close'].clicked.connect(controller.remote_store.close)
        nodes['remote_store.btn.refresh_status'].clicked.connect(controller.remote_store.refresh_status)
        nodes['remote_store.btn.upload.files'].clicked.connect(controller.remote_store.batch.open_upload_files)
        nodes['remote_store.btn.upload.dir'].clicked.connect(controller.remote_store.batch.open_upload_dir)

        nodes['remote_store.provider.combo'].currentIndexChanged.connect(
            lambda i: controller.remote_store.set_provider(nodes['remote_store.provider.combo'].itemData(i))
        )
        nodes['remote_store.hide_thread'].toggled.connect(controller.remote_store.set_hide_thread)

        nodes['remote_store.btn.new'].setAutoDefault(False)
        nodes['remote_store.btn.refresh_status'].setAutoDefault(False)
        nodes['remote_store.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        footer.addWidget(nodes['remote_store.btn.close'])
        footer.addWidget(nodes['remote_store.btn.save'])

        # Options panel (right)
        parent_id = "remote_store"
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QVBoxLayout()

        if parent_id not in ui.config:
            ui.config[parent_id] = {}

        options = copy.deepcopy(controller.remote_store.get_options())
        widgets = self.build_widgets(options)
        advanced_keys = [k for k, v in options.items() if v.get('advanced')]

        for key, w in widgets.items():
            ui.config[parent_id][key] = w

        # Provider bar
        provider_bar = QHBoxLayout()
        provider_bar.addWidget(nodes['remote_store.provider.label'], 0)
        provider_bar.addWidget(nodes['remote_store.provider.combo'], 1)
        provider_bar.setContentsMargins(5, 5, 5, 5)
        content.addLayout(provider_bar)
        content.addWidget(nodes['remote_store.provider.desc'])

        for key in widgets:
            if key in advanced_keys:
                continue
            content.addLayout(self.add_option(widgets[key], options[key]))

        if advanced_keys:
            group_id = 'remote_store.advanced'
            ui.groups[group_id] = CollapsedGroup(self.window, group_id, None, False, None)
            ui.groups[group_id].box.setText(trans('settings.advanced.collapse'))
            for key in widgets:
                if key not in advanced_keys:
                    continue
                option = self.add_option(widgets[key], options[key])
                ui.groups[group_id].add_layout(option)
            content.addWidget(ui.groups[group_id])

        content.setContentsMargins(0, 0, 0, 0)

        scroll_widget = QWidget()
        scroll_widget.setLayout(content)
        scroll.setWidget(scroll_widget)

        area = QVBoxLayout()
        area.addWidget(scroll)
        area.setContentsMargins(0, 0, 0, 0)

        area_widget = QWidget()
        area_widget.setLayout(area)

        # Left: stores list
        list_id = 'remote_store.list'
        nodes[list_id] = QListView()
        models[list_id] = self.create_model(self.window)
        nodes[list_id].setModel(models[list_id])
        nodes[list_id].setMinimumWidth(260)
        nodes[list_id].setSelectionMode(QListView.ExtendedSelection)
        nodes[list_id].setEditTriggers(QListView.NoEditTriggers)
        nodes[list_id].clicked.connect(lambda ix: controller.remote_store.select(ix.row()))
        nodes[list_id].setContextMenuPolicy(Qt.CustomContextMenu)
        nodes[list_id].customContextMenuRequested.connect(self.on_stores_context_menu)

        left_layout = QVBoxLayout()
        left_layout.addWidget(nodes['remote_store.btn.new'])
        left_layout.addWidget(nodes[list_id])
        left_layout.addWidget(nodes['remote_store.hide_thread'])
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # Files panel
        files_panel = QVBoxLayout()
        files_label = QLabel("Files")
        files_label.setStyleSheet("font-weight: bold;")
        files_panel.addWidget(files_label)

        files_list_id = 'remote_store.files.list'
        nodes[files_list_id] = QListView()
        nodes[files_list_id].setEditTriggers(QListView.NoEditTriggers)
        nodes[files_list_id].setSelectionMode(QListView.ExtendedSelection)
        nodes[files_list_id].setContextMenuPolicy(Qt.CustomContextMenu)
        nodes[files_list_id].customContextMenuRequested.connect(self.on_files_context_menu)

        models[files_list_id] = self.create_model(self.window)
        nodes[files_list_id].setModel(models[files_list_id])
        nodes[files_list_id].setMinimumWidth(300)

        files_bottom = QHBoxLayout()
        files_bottom.setContentsMargins(0, 0, 0, 0)
        files_bottom.addWidget(nodes['remote_store.btn.upload.files'])
        files_bottom.addWidget(nodes['remote_store.btn.upload.dir'])
        files_bottom.addWidget(nodes['remote_store.btn.refresh_status'])

        files_panel.addWidget(nodes[files_list_id])
        files_panel.setContentsMargins(0, 0, 0, 5)
        files_panel.addLayout(files_bottom)
        files_widget = QWidget()
        files_widget.setLayout(files_panel)

        # Splitters
        splitters['dialog.remote_store'] = QSplitter(Qt.Horizontal)
        splitters['dialog.remote_store'].addWidget(left_widget)

        splitters['dialog.remote_store.right'] = QSplitter(Qt.Horizontal)
        splitters['dialog.remote_store.right'].addWidget(files_widget)
        splitters['dialog.remote_store.right'].addWidget(area_widget)
        splitters['dialog.remote_store.right'].setStretchFactor(1, 7)
        splitters['dialog.remote_store.right'].setStretchFactor(0, 3)

        splitters['dialog.remote_store'].addWidget(splitters['dialog.remote_store.right'])
        splitters['dialog.remote_store'].setStretchFactor(0, 2)
        splitters['dialog.remote_store'].setStretchFactor(1, 8)
        splitters['dialog.remote_store'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout()
        main_layout.addWidget(splitters['dialog.remote_store'])
        main_layout.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addLayout(footer)
        layout.setMenuBar(self.setup_menu())

        ui.dialog[self.dialog_id] = RemoteStoreDialog(self.window, self.dialog_id) # TODO: change to store dialog
        ui.dialog[self.dialog_id].setLayout(layout)
        ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.remote_store'))

        # Initial sync
        self.sync_hide_threads_checkbox(self._provider_from_cfg())

    # ======================== Menu bar ========================

    def setup_menu(self) -> QMenuBar:
        controller = self.window.controller
        self.actions = {}
        self.menu_bar = QMenuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.menu = {}
        self.menu["current"] = self.menu_bar.addMenu(trans("dialog.remote_store.menu.current"))
        self.menu["all"] = self.menu_bar.addMenu(trans("dialog.remote_store.menu.all"))

        # Current
        self.actions["current.import_files"] = QAction(QIcon(":/icons/download.svg"),
                                                       trans("dialog.remote_store.menu.current.import_files"),
                                                       self.menu_bar)
        self.actions["current.import_files"].triggered.connect(
            lambda: controller.remote_store.import_store_files(controller.remote_store.current)
        )

        self.actions["current.refresh_store"] = QAction(QIcon(":/icons/reload.svg"),
                                                        trans("dialog.remote_store.menu.current.refresh_store"),
                                                        self.menu_bar)
        self.actions["current.refresh_store"].triggered.connect(controller.remote_store.refresh_status)

        self.actions["current.clear_files"] = QAction(QIcon(":/icons/close.svg"),
                                                      trans("dialog.remote_store.menu.current.clear_files"),
                                                      self.menu_bar)
        self.actions["current.clear_files"].triggered.connect(
            lambda: controller.remote_store.clear_store_files(controller.remote_store.current)
        )

        self.actions["current.truncate_files"] = QAction(QIcon(":/icons/delete.svg"),
                                                         trans("dialog.remote_store.menu.current.truncate_files"),
                                                         self.menu_bar)
        self.actions["current.truncate_files"].triggered.connect(
            lambda: controller.remote_store.truncate_store_files(controller.remote_store.current)
        )

        self.actions["current.delete"] = QAction(QIcon(":/icons/delete.svg"),
                                                 trans("dialog.remote_store.menu.current.delete"),
                                                 self.menu_bar)
        self.actions["current.delete"].triggered.connect(
            lambda: controller.remote_store.delete(controller.remote_store.current)
        )

        # All
        self.actions["all.import_all"] = QAction(QIcon(":/icons/download.svg"),
                                                 trans("dialog.remote_store.menu.all.import_all"),
                                                 self.menu_bar)
        self.actions["all.import_all"].triggered.connect(controller.remote_store.import_stores)

        self.actions["all.import_files"] = QAction(QIcon(":/icons/download.svg"),
                                                   trans("dialog.remote_store.menu.all.import_files"),
                                                   self.menu_bar)
        self.actions["all.import_files"].triggered.connect(controller.remote_store.import_files)

        self.actions["all.refresh_stores"] = QAction(QIcon(":/icons/reload.svg"),
                                                     trans("dialog.remote_store.menu.all.refresh_store"),
                                                     self.menu_bar)
        self.actions["all.refresh_stores"].triggered.connect(controller.remote_store.refresh_stores)

        self.actions["all.clear_stores"] = QAction(QIcon(":/icons/close.svg"),
                                                   trans("dialog.remote_store.menu.all.clear_store"),
                                                   self.menu_bar)
        self.actions["all.clear_stores"].triggered.connect(controller.remote_store.clear_stores)

        self.actions["all.clear_files"] = QAction(QIcon(":/icons/close.svg"),
                                                  trans("dialog.remote_store.menu.all.clear_files"),
                                                  self.menu_bar)
        self.actions["all.clear_files"].triggered.connect(controller.remote_store.clear_files)

        self.actions["all.truncate_stores"] = QAction(QIcon(":/icons/delete.svg"),
                                                      trans("dialog.remote_store.menu.all.truncate_store"),
                                                      self.menu_bar)
        self.actions["all.truncate_stores"].triggered.connect(controller.remote_store.truncate_stores)

        self.actions["all.truncate_files"] = QAction(QIcon(":/icons/delete.svg"),
                                                     trans("dialog.remote_store.menu.all.truncate_files"),
                                                     self.menu_bar)
        self.actions["all.truncate_files"].triggered.connect(controller.remote_store.truncate_files)

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

    # ======================== Helpers ========================

    def build_widgets(self, options: dict) -> dict:
        parent = "model"
        widgets = {}
        for key in options:
            option = options[key]
            option['id'] = key
            if option['type'] in ('text', 'int', 'float'):
                if option.get('slider') and option['type'] in ('int', 'float'):
                    widgets[key] = OptionSlider(self.window, parent, key, option)
                else:
                    if option.get('secret'):
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
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def add_urls(self, urls: dict) -> QWidget:
        layout = QVBoxLayout()
        for name in urls:
            url = urls[name]
            label = UrlLabel(name, url)
            layout.addWidget(label)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def add_option(self, widget: QWidget, option: dict) -> QVBoxLayout:
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
            self.window.ui.nodes[desc_key] = DescLabel(desc)
            self.window.ui.nodes[desc_key].setWordWrap(True)
            self.window.ui.nodes[desc_key].setMaximumHeight(40)
            self.window.ui.nodes[desc_key].setStyleSheet("font-size: 10px;")
            layout.addWidget(self.window.ui.nodes[desc_key])

        line = self.add_line()
        layout.addWidget(line)
        return layout

    def create_model(self, parent) -> QStandardItemModel:
        return QStandardItemModel(0, 1, parent)

    def update_list_pairs(self, id: str, pairs: list[tuple[str, str]]):
        models = self.window.ui.models
        if id not in models:
            return
        model = models[id]
        model.setRowCount(len(pairs))
        for i, (_, label) in enumerate(pairs):
            model.setData(model.index(i, 0), label)

    def set_current_row(self, list_id: str, row: int):
        if list_id not in self.window.ui.nodes or list_id not in self.window.ui.models:
            return
        current = self.window.ui.models[list_id].index(row, 0)
        self.window.ui.nodes[list_id].setCurrentIndex(current)

    def set_provider_in_ui(self, provider: str):
        combo = self.window.ui.nodes.get('remote_store.provider.combo')
        if not combo:
            return
        idx = combo.findData(provider)
        if idx >= 0:
            blocked = combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(blocked)

    def sync_provider_dependent_ui(self, provider: str):
        w = self.window.ui.config.get('remote_store', {}).get('expire_days')
        if w:
            w.setVisible(provider == "openai")

    def sync_hide_threads_checkbox(self, provider: str):
        nodes = self.window.ui.nodes
        state = bool(self.window.core.config.get("remote_store.hide_threads"))
        nodes['remote_store.hide_thread'].setChecked(state)

    def _provider_from_cfg(self) -> str:
        key = self.window.core.config.get("remote_store.provider")
        return key if key in self.window.controller.remote_store.get_provider_keys() \
            else self.window.controller.remote_store.DEFAULT_PROVIDER

    def update_title(self, text: str):
        dlg = self.window.ui.dialog.get(self.dialog_id)
        if dlg:
            dlg.setWindowTitle(text)

    # ======================== Context menus ========================

    def on_stores_context_menu(self, pos: QPoint):
        controller = self.window.controller
        view_id = 'remote_store.list'
        if view_id not in self.window.ui.nodes:
            return
        view = self.window.ui.nodes[view_id]
        index = view.indexAt(pos)
        if not index.isValid():
            return

        sel_model = view.selectionModel()
        selected_rows = sorted([ix.row() for ix in sel_model.selectedRows()]) if sel_model else []
        multi = len(selected_rows) > 1

        row = index.row()
        menu = QMenu(view)
        act_refresh = QAction(QIcon(":/icons/reload.svg"), trans("dialog.remote_store.menu.current.refresh_store"), view)
        act_delete = QAction(QIcon(":/icons/delete.svg"), trans("action.delete"), view)
        act_clear = QAction(QIcon(":/icons/close.svg"), trans("dialog.remote_store.menu.current.clear_files"), view)
        act_truncate = QAction(QIcon(":/icons/delete.svg"), trans("dialog.remote_store.menu.current.truncate_files"), view)

        if multi:
            act_refresh.triggered.connect(lambda: controller.remote_store.refresh_by_idx(list(selected_rows)))
            act_delete.triggered.connect(lambda: controller.remote_store.delete_by_idx(list(selected_rows)))
            act_clear.triggered.connect(lambda: controller.remote_store.clear_store_files(
                [controller.remote_store.get_by_tab_idx(r) for r in selected_rows]
            ))
            act_truncate.triggered.connect(lambda: controller.remote_store.truncate_store_files(
                [controller.remote_store.get_by_tab_idx(r) for r in selected_rows]
            ))
        else:
            act_refresh.triggered.connect(lambda: controller.remote_store.refresh_by_idx(row))
            act_delete.triggered.connect(lambda: controller.remote_store.delete_by_idx(row))
            act_clear.triggered.connect(lambda: controller.remote_store.clear_store_files(
                controller.remote_store.get_by_tab_idx(row)
            ))
            act_truncate.triggered.connect(lambda: controller.remote_store.truncate_store_files(
                controller.remote_store.get_by_tab_idx(row)
            ))

        menu.addAction(act_refresh)
        menu.addAction(act_delete)
        menu.addAction(act_clear)
        menu.addAction(act_truncate)
        menu.exec(view.mapToGlobal(pos))

    def on_files_context_menu(self, pos: QPoint):
        controller = self.window.controller
        view_id = 'remote_store.files.list'
        if view_id not in self.window.ui.nodes:
            return
        view = self.window.ui.nodes[view_id]
        index = view.indexAt(pos)
        if not index.isValid():
            return

        sel_model = view.selectionModel()
        selected_rows = sorted([ix.row() for ix in sel_model.selectedRows()]) if sel_model else []
        multi = len(selected_rows) > 1

        row = index.row()
        menu = QMenu(view)
        act_delete = QAction(QIcon(":/icons/delete.svg"),
                             trans("remote_store.menu.file.delete") if hasattr(self.window, 'tr') else "Delete",
                             view)

        if multi:
            act_delete.triggered.connect(
                lambda checked=False, rows=list(selected_rows): controller.remote_store.delete_file_by_idx(rows)
            )
        else:
            act_delete.triggered.connect(
                lambda checked=False, r=row: controller.remote_store.delete_file_by_idx(r)
            )

        menu.addAction(act_delete)
        menu.exec(view.mapToGlobal(pos))