#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
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
        ui = self.window.ui
        controller = self.window.controller
        save_text = trans("dialog.preset.btn.save")
        dismiss_text = trans("dialog.rename.dismiss")
        edit_title = trans('action.edit')

        for dict_id, data in self.dicts.items():
            parent_id = f"{self.id}.{dict_id}"
            option_key = self.keys[dict_id]
            parent = self.parents[dict_id]
            ui.config[parent_id] = {}

            fields = {}
            if data["type"] == 'dict':
                fields = controller.config.dictionary.to_options(
                    parent_id,
                    data,
                )
            elif data["type"] == 'cmd':
                fields = controller.config.cmd.to_options(
                    parent_id,
                    data,
                )

            widgets = self.build_widgets(
                parent_id,
                fields,
                stretch=True,
            )
            ui.config[parent_id] = widgets

            add_option = self.add_option
            add_row_option = self.add_row_option
            add_raw_option = self.add_raw_option

            rows = QVBoxLayout()
            has_textarea = False

            for k, f in fields.items():
                t = f.get("type")
                w = widgets.get(k)
                if t in ('int', 'float'):
                    row = add_option(w, f)
                elif t in ('text', 'textarea', 'dict', 'combo'):
                    row = add_row_option(w, f)
                elif t == 'bool':
                    row = add_raw_option(w, f)
                else:
                    continue
                rows.addLayout(row)
                if t == 'textarea':
                    has_textarea = True

            if not has_textarea:
                rows.addStretch()

            save_key = f"{parent_id}.btn.save"
            dismiss_key = f"{parent_id}.btn.dismiss"

            ui.nodes[save_key] = QPushButton(save_text)
            ui.nodes[save_key].clicked.connect(
                lambda checked=True, option_key=option_key, parent=parent, fields=fields:
                controller.config.dictionary.save_editor(
                    option_key,
                    parent,
                    fields,
                ))
            ui.nodes[save_key].setAutoDefault(True)

            ui.nodes[dismiss_key] = QPushButton(dismiss_text)
            ui.nodes[dismiss_key].clicked.connect(
                lambda checked=True, pid=parent_id: ui.dialogs.close(f'editor.{pid}')
            )
            ui.nodes[dismiss_key].setAutoDefault(False)

            footer = QHBoxLayout()
            footer.addWidget(ui.nodes[dismiss_key])
            footer.addWidget(ui.nodes[save_key])

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            widget = QWidget()
            widget.setLayout(rows)
            scroll.setWidget(widget)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            layout = QVBoxLayout()
            layout.addWidget(scroll)
            layout.addLayout(footer)

            dialog_key = f'editor.{parent_id}'
            ui.dialog[dialog_key] = EditorDialog(self.window, parent_id)
            ui.dialog[dialog_key].setLayout(layout)
            ui.dialog[dialog_key].setWindowTitle(edit_title)