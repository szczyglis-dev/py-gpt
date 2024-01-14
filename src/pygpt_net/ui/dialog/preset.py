#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.14 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSplitter, QWidget

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.editor import EditorDialog
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

        # apply widgets to layouts
        options = {}
        for key in widgets:
            if fields[key]["type"] == 'text' or fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                options[key] = self.add_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'textarea':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'bool':
                options[key] = self.add_raw_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'dict':
                options[key] = self.add_row_option(widgets[key], fields[key])
            elif fields[key]["type"] == 'combo':
                options[key] = self.add_row_option(widgets[key], fields[key])

        rows = QVBoxLayout()

        ignore_keys = ["chat", "completion", "img", "vision", "assistant", "langchain", "prompt"]

        rows1 = QHBoxLayout()
        rows1.addLayout(options["chat"])
        rows1.addLayout(options["completion"])
        rows1.addLayout(options["img"])

        rows2 = QHBoxLayout()
        rows2.addLayout(options["vision"])
        rows2.addLayout(options["assistant"])
        rows2.addLayout(options["langchain"])

        rows_bottom = QWidget()
        rows_bottom.setLayout(options["prompt"])

        # append widgets options layouts to rows
        for key in options:
            if key in ignore_keys:
                continue
            rows.addLayout(options[key])
            if key == "user_name":
                 rows.addLayout(rows1)
                 rows.addLayout(rows2)

        rows.addStretch()
        rows_top = QWidget()
        rows_top.setLayout(rows)

        self.window.ui.splitters['editor.presets'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['editor.presets'].addWidget(rows_top)
        self.window.ui.splitters['editor.presets'].addWidget(rows_bottom)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.splitters['editor.presets'])
        layout.addLayout(footer)

        self.window.ui.dialog['editor.' + self.dialog_id] = EditorDialog(self.window, self.dialog_id)
        self.window.ui.dialog['editor.' + self.dialog_id].setLayout(layout)
        self.window.ui.dialog['editor.' + self.dialog_id].setWindowTitle(trans('dialog.preset'))
