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
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QIcon, QAction
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget, QFrame, \
    QSplitter, QSizePolicy, QMenuBar

from pygpt_net.ui.widget.dialog.model import ModelDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.element.labels import UrlLabel, DescLabel
from pygpt_net.ui.widget.lists.model_editor import ModelEditorList
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.ui.widget.textarea.search_input import SearchInput
from pygpt_net.utils import trans


class Models:
    def __init__(self, window=None):
        """
        Models editor dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "models.editor"
        self.menu_bar = None

        # Keep menu objects alive and correctly parented
        self._file_menu = None
        self._menu_actions: Dict[str, QAction] = {}

        # Internal state for filtering/mapping
        self._filter_text: str = ""
        self._filtered_ids: List[str] = []     # current list of model keys displayed in the view (order matters)
        self._index_to_id: List[str] = []      # row index -> model key
        self._id_to_index: Dict[str, int] = {} # model key -> row index
        self._all_data: Dict[str, object] = {} # last known (unfiltered) data snapshot used to render the list

    def setup(self, idx=None):
        """
        Setup editor dialog

        :param idx: current model tab index
        """
        self.window.ui.nodes['models.editor.btn.new'] = \
            QPushButton(QIcon(":/icons/add.svg"), trans("dialog.models.editor.btn.new"))
        self.window.ui.nodes['models.editor.btn.defaults.user'] = \
            QPushButton(trans("dialog.models.editor.btn.defaults.user"))
        self.window.ui.nodes['models.editor.btn.defaults.app'] = \
            QPushButton(trans("dialog.models.editor.btn.defaults.app"))
        self.window.ui.nodes['models.editor.btn.save'] = \
            QPushButton(trans("dialog.models.editor.btn.save"))

        self.window.ui.nodes['models.editor.btn.new'].clicked.connect(
            lambda: self.window.controller.model.editor.new()
        )
        self.window.ui.nodes['models.editor.btn.defaults.user'].clicked.connect(
            lambda: self.window.controller.model.editor.load_defaults_user()
        )
        self.window.ui.nodes['models.editor.btn.defaults.app'].clicked.connect(
            lambda: self.window.controller.model.editor.load_defaults_app()
        )
        self.window.ui.nodes['models.editor.btn.save'].clicked.connect(
            lambda: self.window.controller.model.editor.save()
        )

        # set enter key to save button
        self.window.ui.nodes['models.editor.btn.new'].setAutoDefault(False)
        self.window.ui.nodes['models.editor.btn.defaults.user'].setAutoDefault(False)
        self.window.ui.nodes['models.editor.btn.defaults.app'].setAutoDefault(False)
        self.window.ui.nodes['models.editor.btn.save'].setAutoDefault(True)

        # footer buttons
        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['models.editor.btn.new'])
        footer.addWidget(self.window.ui.nodes['models.editor.btn.defaults.user'])
        footer.addWidget(self.window.ui.nodes['models.editor.btn.defaults.app'])
        footer.addWidget(self.window.ui.nodes['models.editor.btn.save'])

        # editor tabs
        self.window.ui.tabs['models.editor'] = QTabWidget()

        # build settings tabs
        parent_id = "model"

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QVBoxLayout()

        # create config options entry if not exists
        if parent_id not in self.window.ui.config:
            self.window.ui.config[parent_id] = {}

        # get options
        options = copy.deepcopy(self.window.controller.model.editor.get_options())
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
            group_id = 'models.editor.advanced'
            group = CollapsedGroup(self.window, group_id, None, False, None)
            group.box.setText(trans('settings.advanced.collapse'))
            for key in widgets:
                if key not in advanced_keys:  # ignore non-advanced options
                    continue
                group.add_layout(self.add_option(widgets[key], options[key]))  # add option to group

            # add advanced options group to scroll
            content.addWidget(group)
            self.window.ui.groups[group_id] = group

        content.addStretch()

        # scroll widget
        scroll_widget = QWidget()
        scroll_widget.setLayout(content)
        scroll.setWidget(scroll_widget)

        area = QVBoxLayout()
        area.addWidget(scroll)

        area_widget = QWidget()
        area_widget.setLayout(area)

        data = {}
        for model_id in self.window.core.models.items.keys():
            model = self.window.core.models.items[model_id]
            data[model_id] = model

        # models list
        id = 'models.list'
        self.window.ui.nodes[id] = ModelEditorList(self.window, id)
        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])
        self.window.ui.nodes[id].setMinimumWidth(250)  # set max width to list

        # search input (placed above the list)
        self.window.ui.nodes['models.editor.search'] = SearchInput()
        # Connect to provided callback API (callables assigned to attributes)
        self.window.ui.nodes['models.editor.search'].on_search = self._on_search_models
        self.window.ui.nodes['models.editor.search'].on_clear = self._on_clear_models  # clear via "X" button

        # provider select
        option_provider = self.window.controller.model.editor.get_provider_option()
        self.window.ui.config[parent_id]['provider_global'] = OptionCombo(self.window, parent_id, 'provider_global',
                                                                          option_provider)
        provider_keys = self.window.controller.config.placeholder.apply_by_id('llm_providers')
        provider_keys.insert(0, {"-": trans("list.all")})  # add "All" option
        self.window.ui.config[parent_id]['provider_global'].set_keys(provider_keys)

        # container for search + list (left panel)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(self.window.ui.nodes['models.editor.search'])
        left_layout.addWidget(self.window.ui.config[parent_id]['provider_global'])
        left_layout.addWidget(self.window.ui.nodes[id])
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # update models list (initial, unfiltered)
        self.update_list(id, data)

        # splitter
        self.window.ui.splitters['dialog.models'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['dialog.models'].addWidget(left_widget)  # search + list
        self.window.ui.splitters['dialog.models'].addWidget(area_widget)  # tabs
        self.window.ui.splitters['dialog.models'].setStretchFactor(0, 2)
        self.window.ui.splitters['dialog.models'].setStretchFactor(1, 5)
        self.window.ui.splitters['dialog.models'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.window.ui.splitters['dialog.models'])

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list + model tabs
        layout.addLayout(footer)  # bottom buttons (save, defaults)

        self.window.ui.dialog[self.dialog_id] = ModelDialog(self.window, self.dialog_id)
        self.window.ui.dialog[self.dialog_id].setLayout(layout)

        self.menu_bar = QMenuBar(self.window.ui.dialog[self.dialog_id])
        self.menu_bar.setNativeMenuBar(False)
        self._file_menu = self.menu_bar.addMenu(trans("menu.file"))

        # open importer
        self._menu_actions["import"] = QAction(
            QIcon(":/icons/download.svg"),
            trans("action.import"),
            self.window.ui.dialog[self.dialog_id],
        )
        self._menu_actions["import"].triggered.connect(
            lambda checked=False: self.window.controller.model.importer.open()
        )
        self._menu_actions["close"] = QAction(
            QIcon(":/icons/logout.svg"),
            trans("menu.file.exit"),
            self.window.ui.dialog[self.dialog_id],
        )
        self._menu_actions["close"].triggered.connect(
            lambda checked=False: self.window.ui.dialog[self.dialog_id].close()
        )

        # add actions
        self._file_menu.addAction(self._menu_actions["import"])
        self._file_menu.addAction(self._menu_actions["close"])
        layout.setMenuBar(self.menu_bar)

        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.models.editor'))

        # restore current opened tab if idx is set
        if idx is not None:
            try:
                self.window.controller.model.editor.set_by_tab(idx)
            except Exception as e:
                print('Failed restore models editor tab: {}'.format(idx))
        else:
            if self.window.controller.model.editor.current is None:
                self.window.controller.model.editor.set_by_tab(0)

    def _on_search_models(self, text: str):
        """
        Handle SearchInput callback. Filtering is prefix-based on model id or name (case-insensitive).
        """
        # Keep normalized filter text
        self._filter_text = (text or "").strip().casefold()
        # Re-apply list render using the last known dataset
        self.update_list('models.list', self._all_data)
        # Do not force-select rows here to avoid heavy editor re-initialization on each keystroke.

    def _on_clear_models(self):
        """
        Handle SearchInput clear (click on 'X' button).
        """
        if not self._filter_text:
            return
        self._filter_text = ""
        self.update_list('models.list', self._all_data)
        # Try to restore selection for the current model if it is visible again.
        self._restore_selection_for_current()

    def _restore_selection_for_current(self):
        """
        Attempt to restore selection on the list to the current editor model if present in the view.
        """
        current_id = getattr(self.window.controller.model.editor, "current", None)
        if not current_id:
            return
        idx = self.get_row_by_model_id(current_id)
        if idx is None:
            return
        current = self.window.ui.models['models.list'].index(idx, 0)
        self.window.ui.nodes['models.list'].setCurrentIndex(current)

    def _apply_filter(self, data: Dict[str, object]) -> Dict[str, object]:
        """
        Return filtered data view, preserving original order.
        """
        if not self._filter_text:
            return data

        out: Dict[str, object] = {}
        needle = self._filter_text
        for mid, item in data.items():
            # Normalize fields for prefix matching
            model_id = (str(getattr(item, "id", mid)) or "").casefold()
            model_name = (getattr(item, "name", "") or "").casefold()
            if (needle in model_name
                    or needle in model_id):
                out[mid] = item
        return out

    def _refresh_index_mapping(self, ids: List[str]):
        """
        Build fast row<->id mapping for the current filtered list.
        """
        self._filtered_ids = list(ids)
        self._index_to_id = list(ids)
        self._id_to_index = {mid: idx for idx, mid in enumerate(ids)}

    def get_model_id_by_row(self, row: int) -> Optional[str]:
        """
        Map a view row index to the model id currently displayed at that row.
        """
        if 0 <= row < len(self._index_to_id):
            return self._index_to_id[row]
        return None

    def get_row_by_model_id(self, model_id: str) -> Optional[int]:
        """
        Map a model id to its current row index in the filtered view.
        """
        return self._id_to_index.get(model_id)

    def get_filtered_ids(self) -> List[str]:
        """
        Return a copy of currently visible model ids (filtered order).
        """
        return list(self._filtered_ids)

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
                # register dict to editor:
                self.window.ui.dialogs.register_dictionary(
                    key,
                    parent=parent,
                    option=option,
                )
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
            cols.addWidget(self.window.ui.nodes[label_key], 1)  # disable label in bool type
            cols.addWidget(widget, 4)

            cols_widget = QWidget()
            cols_widget.setLayout(cols)

            if option['type'] != 'bool_list':
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
            self.window.ui.nodes[desc_key] = DescLabel(desc)
            self.window.ui.nodes[desc_key].setMaximumHeight(40)
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

    def _get_provider_display_name(self, provider_id: str) -> str:
        """
        Resolve provider display name using app's LLM provider registry.
        """
        if not provider_id:
            return ""
        try:
            name = self.window.core.llm.get_provider_name(provider_id)
            if isinstance(name, str):
                name = name.strip()
            return name or ""
        except Exception:
            # Fail silently to avoid breaking the models list rendering
            return ""

    def update_list(self, id: str, data: dict):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        # Keep latest source data for subsequent filtering cycles
        self._all_data = dict(data)

        # Apply current filter (preserve insertion/sorted order)
        filtered = self._apply_filter(self._all_data)

        # Reset model rows
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())

        # Count occurrences of each model display name to detect duplicates (in filtered view)
        name_counts = {}
        for key in filtered:
            item = filtered[key]
            base_name = getattr(item, "name", "") or ""
            name_counts[base_name] = name_counts.get(base_name, 0) + 1

        # Populate rows with optional provider suffix for duplicate names
        i = 0
        row_ids: List[str] = []
        for n in filtered:
            item = filtered[n]
            base_name = getattr(item, "name", "") or ""
            display_name = base_name
            if name_counts.get(base_name, 0) > 1:
                provider_id = getattr(item, "provider", None)
                provider_name = self._get_provider_display_name(provider_id) if provider_id else ""
                if provider_name:
                    display_name = f"{base_name} ({provider_name})"

            self.window.ui.models[id].insertRow(i)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), display_name)
            # IMPORTANT: map list row to the dictionary key (stable and unique within models.items)
            row_ids.append(n)
            i += 1

        # Refresh index mappings used by Editor
        self._refresh_index_mapping(row_ids)