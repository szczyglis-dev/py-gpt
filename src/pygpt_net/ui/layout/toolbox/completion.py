#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 10:25:00                  #
# ================================================== #

from PySide6.QtWidgets import QHBoxLayout, QWidget

from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


class Completion:
    """Completion-mode footer controls."""

    def __init__(self, window=None):
        self.window = window

    def setup(self) -> QWidget:
        """Create the ``As chat`` toggle shown directly above the RAG row."""
        nodes = self.window.ui.nodes

        toggle = ToggleLabel(
            trans("toolbox.completion.as_chat"),
            label_position="left",
            parent=self.window,
        )
        toggle.setChecked(bool(self.window.core.config.get("completion.as_chat", True)))
        toggle.box.toggled.connect(self._on_toggle)
        nodes["completion.as_chat"] = toggle

        widget = QWidget(self.window)
        layout = QHBoxLayout(widget)
        layout.addWidget(toggle)
        layout.addStretch(1)
        layout.setContentsMargins(5, 0, 5, 4)

        nodes["completion.as_chat.widget"] = widget
        return widget

    def _on_toggle(self, value: bool):
        """Persist Completion prompt-building mode immediately."""
        self.window.core.config.set("completion.as_chat", bool(value))
        self.window.core.config.save()
