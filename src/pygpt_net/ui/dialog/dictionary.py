#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QScrollArea, QWidget, QSizePolicy

from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.utils import trans


class Dictionary(BaseConfigDialog):
    def __init__(self, window=None, *args, **kwargs):
        super(Dictionary, self).__init__(window, *args, **kwargs)
        """
        Dictionary list item editor dialog

        :param window: Window instance
        """
        self.window = window
        self.id = "dictionary"
        self.dialog_id = "dictionary"
        self.dicts = {}
        self.keys = {}
        self.parents = {}
        self.current_idx = None

    def register(self, id: str, key: str, parent: str, option: dict):
        """
        Register dictionary editor options

        :param id: Dictionary ID
        :param key: Option key
        :param parent: Parent ID
        :param option: Dictionary keys
        """
        self.dicts[id] = option
        self.keys[id] = key
        self.parents[id] = parent

    def setup(self):
        """Setup dictionary editor dialogs"""
        for dict_id in self.dicts:
            parent_id = self.id + "." + dict_id
            option_key = self.keys[dict_id]
            parent = self.parents[dict_id]
            data = self.dicts[dict_id]
            self.window.ui.config[parent_id] = {}

            # widgets
            fields = {}

            # option type: dict
            if data["type"] == 'dict':
                fields = self.window.controller.config.dictionary.to_options(
                    parent_id,
                    data,
                )  # item to options

            # option type: cmd
            elif data["type"] == 'cmd':
                fields = self.window.controller.config.cmd.to_options(
                    parent_id,
                    data,
                )  # item to options

            widgets = self.build_widgets(
                parent_id,
                fields,
                stretch=True,
            )  # from base config dialog

            for key in widgets:
                self.window.ui.config[parent_id][key] = widgets[key]

            # apply widgets to layouts
            options = {}
            is_stretch = False
            for key in widgets:
                if fields[key]["type"] == 'int' or fields[key]["type"] == 'float':
                    options[key] = self.add_option(widgets[key], fields[key])
                elif fields[key]["type"] == 'text' or fields[key]["type"] == 'textarea':
                    options[key] = self.add_row_option(widgets[key], fields[key])
                elif fields[key]["type"] == 'bool':
                    options[key] = self.add_raw_option(widgets[key], fields[key])
                elif fields[key]["type"] == 'dict':
                    options[key] = self.add_row_option(widgets[key], fields[key])
                elif fields[key]["type"] == 'combo':
                    options[key] = self.add_row_option(widgets[key], fields[key])

                # stretch all only if textarea is present
                if fields[key]["type"] == 'textarea':
                    is_stretch = True

            rows = QVBoxLayout()
            for key in options:
                rows.addLayout(options[key])

            if not is_stretch:
                rows.addStretch()

            # footer
            self.window.ui.nodes[parent_id + '.btn.save'] = QPushButton(trans("dialog.preset.btn.save"))
            self.window.ui.nodes[parent_id + '.btn.save'].clicked.connect(
                lambda checked=True, option_key=option_key, parent=parent, fields=fields:
                self.window.controller.config.dictionary.save_editor(
                    option_key,
                    parent,
                    fields,
                ))
            self.window.ui.nodes[parent_id + '.btn.save'].setAutoDefault(True)

            self.window.ui.nodes[parent_id + '.btn.dismiss'] = QPushButton(trans("dialog.rename.dismiss"))
            self.window.ui.nodes[parent_id + '.btn.dismiss'].clicked.connect(
                lambda checked=True, parent_id=parent_id: self.window.ui.dialogs.close('editor.' + parent_id)
            )
            self.window.ui.nodes[parent_id + '.btn.dismiss'].setAutoDefault(False)

            footer = QHBoxLayout()
            footer.addWidget(self.window.ui.nodes[parent_id + '.btn.dismiss'])
            footer.addWidget(self.window.ui.nodes[parent_id + '.btn.save'])

            # scroll area
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            widget = QWidget()
            widget.setLayout(rows)
            scroll.setWidget(widget)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            layout = QVBoxLayout()
            layout.addWidget(scroll)  # options
            layout.addLayout(footer)  # footer

            # dialog
            self.window.ui.dialog['editor.' + parent_id] = EditorDialog(self.window, parent_id)  # current idx here
            self.window.ui.dialog['editor.' + parent_id].setLayout(layout)
            self.window.ui.dialog['editor.' + parent_id].setWindowTitle(trans('action.edit'))
