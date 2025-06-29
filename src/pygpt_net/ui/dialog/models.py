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
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QScrollArea, QWidget, QTabWidget, QFrame, \
    QSplitter, QSizePolicy

from pygpt_net.item.model import ModelItem
from pygpt_net.ui.widget.dialog.model import ModelDialog
from pygpt_net.ui.widget.element.group import CollapsedGroup
from pygpt_net.ui.widget.element.labels import UrlLabel
from pygpt_net.ui.widget.lists.model_editor import ModelEditorList
from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.checkbox_list import OptionCheckboxList
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.textarea import OptionTextarea
from pygpt_net.utils import trans


class Models:
    def __init__(self, window=None):
        """
        Models editor dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "models.editor"

    def setup(self, idx=None):
        """
        Setup editor dialog

        :param idx: current model tab index
        """
        self.window.ui.nodes['models.editor.btn.new'] = \
            QPushButton(trans("dialog.models.editor.btn.new"))
        self.window.ui.nodes['models.editor.btn.defaults.user'] = \
            QPushButton(trans("dialog.models.editor.btn.defaults.user"))
        self.window.ui.nodes['models.editor.btn.defaults.app'] = \
            QPushButton(trans("dialog.models.editor.btn.defaults.app"))
        self.window.ui.nodes['models.editor.btn.save'] = \
            QPushButton(trans("dialog.models.editor.btn.save"))

        self.window.ui.nodes['models.editor.btn.new'].clicked.connect(
            lambda: self.window.controller.model.editor.new())
        self.window.ui.nodes['models.editor.btn.defaults.user'].clicked.connect(
            lambda: self.window.controller.model.editor.load_defaults_user())
        self.window.ui.nodes['models.editor.btn.defaults.app'].clicked.connect(
            lambda: self.window.controller.model.editor.load_defaults_app())
        self.window.ui.nodes['models.editor.btn.save'].clicked.connect(
            lambda: self.window.controller.model.editor.save())

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
            self.window.ui.groups[group_id] = CollapsedGroup(self.window, group_id, None, False, None)
            self.window.ui.groups[group_id].box.setText(trans('settings.advanced.collapse'))
            for key in widgets:
                if key not in advanced_keys:  # ignore non-advanced options
                    continue

                option = self.add_option(widgets[key], options[key])  # build option
                self.window.ui.groups[group_id].add_layout(option)  # add option to group

            # add advanced options group to scroll
            content.addWidget(self.window.ui.groups[group_id])

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

        # update models list
        self.update_list(id, data)

        # set max width to list
        self.window.ui.nodes[id].setMinimumWidth(250)

        # splitter
        self.window.ui.splitters['dialog.models'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['dialog.models'].addWidget(self.window.ui.nodes[id])  # list
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
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
