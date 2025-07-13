#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QSplitter, QWidget, QSizePolicy

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)
from pygpt_net.ui.base.config_dialog import BaseConfigDialog
from pygpt_net.ui.widget.dialog.editor import EditorDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
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
            lambda: self.window.controller.presets.editor.from_current()
        )
        self.window.ui.nodes['preset.btn.save'].clicked.connect(
            lambda: self.window.controller.presets.editor.save()
        )

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
            if fields[key]["type"] in ['text', 'int', 'float']:
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

        for key in options:
            options[key].setContentsMargins(0, 0, 0, 0)

        # modes
        mode_keys = [
            MODE_CHAT,
            MODE_LLAMA_INDEX,            
            MODE_AUDIO,            
            MODE_RESEARCH,
            MODE_COMPLETION,
            MODE_IMAGE,
            MODE_VISION,
            # MODE_LANGCHAIN,
            MODE_AGENT_LLAMA,
            MODE_AGENT,
            MODE_EXPERT,
        ]
        rows_mode = QVBoxLayout()
        rows_mode.addStretch()
        rows_mode.setContentsMargins(0, 0, 0, 0)
        for key in mode_keys:
            rows_mode.addLayout(options[key])

        # modes
        self.window.ui.nodes['preset.editor.modes'] = QWidget()
        self.window.ui.nodes['preset.editor.modes'].setLayout(rows_mode)
        self.window.ui.nodes['preset.editor.modes'].setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes['preset.editor.modes'].setMaximumWidth(300)

        # functions label
        self.window.ui.nodes['preset.tool.function.label.all'] = HelpLabel(
            trans("preset.tool.function.tip.all"))
        self.window.ui.nodes['preset.tool.function.label.all'].setAlignment(Qt.AlignCenter)
        self.window.ui.nodes['preset.tool.function.label.assistant'] = HelpLabel(
            trans("preset.tool.function.tip.assistant"))
        self.window.ui.nodes['preset.tool.function.label.assistant'].setAlignment(Qt.AlignCenter)
        self.window.ui.nodes['preset.tool.function.label.agent_llama'] = HelpLabel(
            trans("preset.tool.function.tip.agent_llama"))
        self.window.ui.nodes['preset.tool.function.label.agent_llama'].setAlignment(Qt.AlignCenter)

        # functions
        self.window.ui.nodes['preset.editor.functions'] = QWidget()
        self.window.ui.nodes['preset.editor.functions'].setLayout(options["tool.function"])

        # experts
        self.window.ui.nodes['preset.editor.experts'] = ExpertsEditor(self.window)

        # agents - llama index
        agent_keys = [
            "agent_provider",
            "idx",
            "assistant_id",
        ]
        agent_layout = QVBoxLayout()
        agent_layout.setContentsMargins(0, 0, 0, 0)
        for key in agent_keys:
            widget = QWidget()
            widget.setLayout(options[key])
            agent_layout.addWidget(widget)
        agent_layout.addStretch()
        self.window.ui.nodes['preset.editor.agent_llama'] = QWidget()
        self.window.ui.nodes['preset.editor.agent_llama'].setLayout(agent_layout)
        self.window.ui.nodes['preset.editor.agent_llama'].setContentsMargins(20, 0, 0, 30)

        # prompt
        widget_prompt = QWidget()
        widget_prompt.setLayout(options["prompt"])
        widget_prompt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # left column
        left_keys = [
            "filename",
            "name",
            "ai_name",
            "user_name",
            "model",
            "temperature",
        ]
        for key in left_keys:
            self.window.ui.nodes['preset.editor.' + key] = QWidget()
            self.window.ui.nodes['preset.editor.' + key].setLayout(options[key])
            self.window.ui.nodes['preset.editor.' + key].setContentsMargins(0, 0, 0, 0)
            rows.addWidget(self.window.ui.nodes['preset.editor.' + key])

        rows.setContentsMargins(0, 0, 0, 0)
        rows.addStretch()

        widget_base = QWidget()
        widget_base.setLayout(rows)

        func_tip_layout = QVBoxLayout()
        func_tip_layout.addWidget(self.window.ui.nodes['preset.tool.function.label.all'])
        func_tip_layout.addWidget(self.window.ui.nodes['preset.tool.function.label.assistant'])
        func_tip_layout.addWidget(self.window.ui.nodes['preset.tool.function.label.agent_llama'])
        func_tip_layout.setContentsMargins(0, 0, 0, 0)
        func_tip_widget = QWidget()
        func_tip_widget.setLayout(func_tip_layout)

        func_rows = QVBoxLayout()
        func_rows.addWidget(self.window.ui.nodes['preset.editor.functions'])
        func_rows.addWidget(self.window.ui.nodes['preset.editor.experts'])
        func_rows.addWidget(self.window.ui.nodes['preset.editor.agent_llama'])
        #func_rows.addStretch()
        func_rows.addWidget(func_tip_widget)

        func_rows.setContentsMargins(0, 0, 0, 0)
        func_widget = QWidget()
        func_widget.setLayout(func_rows)
        func_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.window.ui.nodes['preset.editor.functions'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.window.ui.nodes['preset.editor.experts'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main = QHBoxLayout()
        main.addWidget(widget_base)
        main.addWidget(func_widget)
        main.addWidget(self.window.ui.nodes['preset.editor.modes'])
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
