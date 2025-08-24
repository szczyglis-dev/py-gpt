#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy

from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.option.prompt import PromptTextarea
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans

class Prompt:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup system prompt

        :return: QWidget
        """
        w = self.window
        nodes = w.ui.nodes

        nodes['toolbox.prompt.label'] = TitleLabel(trans("toolbox.prompt"))

        nodes['cmd.enabled'] = ToggleLabel(
            trans('cmd.enabled'),
            label_position="left",
            icon=":/icons/build.svg",
            parent=w
        )
        box = nodes['cmd.enabled'].box
        box.toggled.connect(w.controller.chat.common.toggle_cmd)
        box.setToolTip(trans('cmd.tip'))
        box.setIcon(QIcon(":/icons/add.svg"))

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.addWidget(nodes['toolbox.prompt.label'])
        header_layout.addStretch(1)
        header_layout.addWidget(nodes['cmd.enabled'])
        header_layout.setContentsMargins(5, 0, 10, 0)

        option = w.controller.presets.editor.get_option('prompt')
        nodes['preset.prompt'] = PromptTextarea(w, 'preset', 'prompt', option)
        nodes['preset.prompt'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        nodes['tip.toolbox.prompt'] = HelpLabel(trans('tip.toolbox.prompt'), w)
        nodes['tip.toolbox.prompt'].setAlignment(Qt.AlignCenter)

        layout_widget = QWidget()
        layout = QVBoxLayout(layout_widget)
        layout.addWidget(header_widget)
        layout.addWidget(nodes['preset.prompt'])
        layout.addWidget(nodes['tip.toolbox.prompt'])
        layout.setContentsMargins(2, 5, 5, 5)

        layout_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return layout_widget