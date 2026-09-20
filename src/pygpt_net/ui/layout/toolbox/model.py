#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 16:17:00                  #
# ================================================== #
from PySide6.QtWidgets import QVBoxLayout, QWidget, QSizePolicy


class Model:

    def __init__(self, window=None):
        """
        Toolbox UI

        Model selection now lives entirely in the chat input controls row.
        Keep this lightweight section object only for toolbox layout/API
        compatibility; it renders no label, selector or settings button.

        :param window: Window instance
        """
        self.window = window
        self.id = 'prompt.model'
        self.label_key = f'{self.id}.label'

    def setup(self) -> QWidget:
        """Return an empty hidden toolbox section for compatibility."""
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        widget.setMinimumWidth(0)
        widget.setLayout(self.setup_list())
        widget.setVisible(False)
        return widget

    def setup_list(self) -> QVBoxLayout:
        """Return an empty layout; model controls are rendered in chat input."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        return layout
