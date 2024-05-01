#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSplitter, QWidget, QSizePolicy

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.ui.widget.lists.experts import ExpertsEditor
from pygpt_net.utils import trans


class Preset(BaseConfigDialog):
    def __init__(self, window=None, *args, **kwargs):
        super(Preset, self).__init__(window, *args, **kwargs)
        """
        Preset editor dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "preset"
        self.dialog_id = "preset.presets"

    def setup(self):
        """Setup preset editor dialog"""
        self.window.ui.nodes['preset.btn.current'] = QPushButton(trans("dialog.preset.btn.current"))
        self.window.ui.nodes['preset.btn.save'] = QPushButton(trans("dialog.preset.btn.save"))
        self.window.ui.nodes['preset.btn.current'].clicked.connect(
            lambda: self.window.controller.presets.editor.from_current())
        self.window.ui.nodes['preset.btn.save'].clicked.connect(
            lambda: self.window.controller.presets.editor.save())

        self.window.ui.nodes['preset.btn.current'].setAutoDefault(False)
        self.window.ui.nodes['preset.btn.save'].setAutoDefault(True)

        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['preset.btn.current'])
        footer.addWidget(self.window.ui.nodes['preset.btn.save'])

        # fields
        self.window.ui.paths[self.id] = QLabel(str(self.window.core.config.path))

        # get option fields config
        fields = self.window.controller.presets.editor.get_options()

        # build settings widgets
        widgets = self.build_widgets(self.id, fields)  # from base config dialog

        # apply settings widgets
        for key in widgets:
            self.window.ui.config[self.id][key] = widgets[key]

        # btn: add function
        self.window.ui.config[self.id]['tool.function'].add_btn.setText(trans('assistant.func.add'))

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if fields[key]["type"] == 'text' or fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                widgets[key].setMaximumHeight(38)
                options[key] = self.add_raw_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'dict':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'combo':
                options[key] = self.add_option(widgets[key], fields[key])

        self.window.ui.nodes['preset.tool.function.label'].setVisible(False)  # hide label

        rows = QVBoxLayout()

        ignore_keys = [
            "chat",
            "completion",
            "img", "vision",
            "llama_index",
            "langchain",
            "agent",
            "expert",
            "prompt",
            "tool.function",
        ]

        options["chat"].setContentsMargins(0, 0, 0, 0)
        options["completion"].setContentsMargins(0, 0, 0, 0)
        options["img"].setContentsMargins(0, 0, 0, 0)
        options["vision"].setContentsMargins(0, 0, 0, 0)
        options["langchain"].setContentsMargins(0, 0, 0, 0)
        options["llama_index"].setContentsMargins(0, 0, 0, 0)
        options["agent"].setContentsMargins(0, 0, 0, 0)
        options["expert"].setContentsMargins(0, 0, 0, 0)
        options["prompt"].setContentsMargins(0, 0, 0, 0)
        options["tool.function"].setContentsMargins(0, 0, 0, 0)

        rows_mode = QVBoxLayout()
        rows_mode.addLayout(options["chat"])
        rows_mode.addLayout(options["completion"])
        rows_mode.addLayout(options["img"])
        rows_mode.addLayout(options["vision"])
        # rows_mode.addLayout(options["assistant"])
        rows_mode.addLayout(options["langchain"])
        rows_mode.addLayout(options["llama_index"])
        rows_mode.addLayout(options["agent"])
        rows_mode.addLayout(options["expert"])


        rows_mode.addStretch()
        rows_mode.setContentsMargins(0, 0, 0, 0)

        self.window.ui.nodes['preset.editor.modes'] = QWidget()
        self.window.ui.nodes['preset.editor.modes'].setLayout(rows_mode)
        self.window.ui.nodes['preset.editor.modes'].setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes['preset.editor.modes'].setMaximumWidth(300)

        self.window.ui.nodes['preset.editor.functions'] = QWidget()
        self.window.ui.nodes['preset.editor.functions'].setLayout(options["tool.function"])
        self.window.ui.nodes['preset.editor.functions'].setMinimumWidth(400)

        self.window.ui.nodes['preset.editor.experts'] = ExpertsEditor(self.window)

        widget_prompt = QWidget()
        widget_prompt.setLayout(options["prompt"])
        widget_prompt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # append widgets options layouts to rows
        for key in options:
            if key in ignore_keys:
                continue
            options[key].setContentsMargins(0, 0, 0, 0)
            rows.addLayout(options[key])

        rows.setContentsMargins(0, 0, 0, 0)

        rows.addStretch()
        widget_base = QWidget()
        widget_base.setLayout(rows)

        # set max width to options
        widget_base.setMinimumWidth(400)
        widget_base.setMaximumWidth(450)

        main = QHBoxLayout()
        main.addWidget(widget_base)
        main.addWidget(self.window.ui.nodes['preset.editor.functions'])
        main.addWidget(self.window.ui.nodes['preset.editor.modes'])
        main.addWidget(self.window.ui.nodes['preset.editor.experts'])
        main.setContentsMargins(0, 0, 0, 0)

        widget_main = QWidget()
        widget_main.setLayout(main)

        self.window.ui.splitters['editor.presets'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['editor.presets'].addWidget(widget_main)
        self.window.ui.splitters['editor.presets'].addWidget(widget_prompt)
        self.window.ui.splitters['editor.presets'].setStretchFactor(0, 1)
        self.window.ui.splitters['editor.presets'].setStretchFactor(1, 2)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.splitters['editor.presets'])
        layout.addLayout(footer)

        self.window.ui.dialog['editor.' + self.dialog_id] = EditorDialog(self.window, self.dialog_id)
        self.window.ui.dialog['editor.' + self.dialog_id].setLayout(layout)
        self.window.ui.dialog['editor.' + self.dialog_id].setWindowTitle(trans('dialog.preset'))
