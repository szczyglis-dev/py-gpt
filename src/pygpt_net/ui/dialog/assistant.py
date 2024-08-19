#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.20 00:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QHBoxLayout,  QVBoxLayout, QSplitter, QWidget, QSizePolicy

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.utils import trans


class Assistant(BaseConfigDialog):
    def __init__(self, window=None, *args, **kwargs):
        super(Assistant, self).__init__(window, *args, **kwargs)
        """
        Assistant editor dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "assistant"
        self.dialog_id = "assistants"

    def setup(self):
        """Setups assistant editor dialog"""
        self.window.ui.nodes['assistant.btn.save'] = QPushButton(trans("dialog.assistant.btn.save"))
        self.window.ui.nodes['assistant.btn.save'].clicked.connect(
            lambda: self.window.controller.assistant.editor.save()
        )
        self.window.ui.nodes['assistant.btn.close'] = QPushButton(trans("dialog.assistant.btn.close"))
        self.window.ui.nodes['assistant.btn.close'].clicked.connect(
            lambda: self.window.controller.assistant.editor.close()
        )


        # store
        self.window.ui.nodes['assistant.btn.store.editor'] = QPushButton(QIcon(":/icons/db.svg"), "")
        self.window.ui.nodes['assistant.btn.store.editor'].setToolTip(trans('dialog.assistant.store'))
        self.window.ui.nodes['assistant.btn.store.editor'].clicked.connect(
            lambda: self.window.controller.assistant.store.toggle_editor()
        )

        self.window.ui.nodes['assistant.btn.store.editor'].setAutoDefault(False)
        self.window.ui.nodes['assistant.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        #footer.addWidget(self.window.ui.nodes['assistant.btn.import_func'])
        footer.addWidget(self.window.ui.nodes['assistant.btn.close'])
        footer.addWidget(self.window.ui.nodes['assistant.btn.save'])

        # get option fields config
        fields = self.window.controller.assistant.editor.get_options()

        # build settings widgets
        widgets = self.build_widgets(self.id, fields)  # from base config dialog

        # apply settings widgets
        for key in widgets:
            self.window.ui.config[self.id][key] = widgets[key]

        # functions
        self.window.ui.nodes['assistant.btn.import_func'] = QPushButton(trans("dialog.assistant.btn.import_func"))
        self.window.ui.nodes['assistant.btn.import_func'].clicked.connect(
            lambda: self.window.controller.assistant.editor.import_functions()
        )
        self.window.ui.nodes['assistant.btn.clear_func'] = QPushButton(trans("dialog.assistant.btn.clear_func"))
        self.window.ui.nodes['assistant.btn.clear_func'].clicked.connect(
            lambda: self.window.controller.assistant.editor.clear_functions()
        )
        self.window.ui.config[self.id]['tool.function'].buttons.addWidget(self.window.ui.nodes['assistant.btn.import_func'])
        self.window.ui.config[self.id]['tool.function'].buttons.addWidget(self.window.ui.nodes['assistant.btn.clear_func'])
        self.window.ui.config[self.id]['tool.function'].add_btn.setText(trans('assistant.func.add'))
        # Empty params: {"type": "object", "properties": {}}

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if fields[key]["type"] == 'text' or fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                options[key] = self.add_raw_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'dict' or fields[key]["type"] == 'function':
                options[key] = self.add_row_option(widgets[key], fields[key])
                if key == "tool.function":
                    widgets[key].setMinimumHeight(150)
            elif fields[key]["type"] == 'combo':
                options[key] = self.add_option(widgets[key], fields[key])

        self.window.ui.nodes['assistant.tool.function.label'].setVisible(False)  # hide label

        options["tool.code_interpreter"].setAlignment(Qt.AlignLeft)
        options["tool.file_search"].setAlignment(Qt.AlignLeft)

        # base
        rows = QVBoxLayout()
        rows.addLayout(options["id"])
        rows.addLayout(options["name"])
        rows.addLayout(options["description"])
        rows.addLayout(options["model"])

        store_layout = QHBoxLayout()
        store_layout.addLayout(options["vector_store"])
        store_layout.addWidget(self.window.ui.nodes['assistant.btn.store.editor'])
        rows.addLayout(store_layout)
        rows.setContentsMargins(0, 0, 0, 0)

        # tools
        rows_tools = QHBoxLayout()

        rows_tools.addLayout(options["tool.code_interpreter"])
        rows_tools.addLayout(options["tool.file_search"])
        rows_tools.setContentsMargins(0, 0, 0, 0)

        rows.addLayout(rows_tools)
        rows.addStretch()

        widget_base = QWidget()
        widget_base.setLayout(rows)

        widget_base.setMinimumWidth(400)
        widget_base.setMaximumWidth(450)

        # prompt
        widget_prompt = QWidget()
        widget_prompt.setLayout(options["instructions"])
        widget_prompt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        options["instructions"].setContentsMargins(0, 0, 0, 0)
        options["tool.function"].setContentsMargins(0, 0, 0, 0)

        widget_tools = QWidget()
        widget_tools.setLayout(options["tool.function"])
        widget_tools.setMinimumWidth(400)

        main = QHBoxLayout()
        main.addWidget(widget_base)
        main.addWidget(widget_tools)
        main.setContentsMargins(0, 0, 0, 0)

        widget_main = QWidget()
        widget_main.setLayout(main)

        # splitters
        self.window.ui.splitters['editor.assistant'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['editor.assistant'].addWidget(widget_main)
        self.window.ui.splitters['editor.assistant'].addWidget(widget_prompt)
        self.window.ui.splitters['editor.assistant'].setStretchFactor(0, 1)
        self.window.ui.splitters['editor.assistant'].setStretchFactor(1, 2)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.splitters['editor.assistant'])
        layout.addLayout(footer)

        # dialog
        self.window.ui.dialog['editor.' + self.dialog_id] = EditorDialog(self.window, self.dialog_id)
        self.window.ui.dialog['editor.' + self.dialog_id].setLayout(layout)
        self.window.ui.dialog['editor.' + self.dialog_id].setWindowTitle(trans('dialog.assistant'))
