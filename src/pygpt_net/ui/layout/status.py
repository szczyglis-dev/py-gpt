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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QSizePolicy, QPushButton

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.anims.loader import Loader
from pygpt_net.utils import trans


class Status:
    def __init__(self, window=None):
        """
        Input UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QHBoxLayout:
        """
        Setup status bar

        :return: QHBoxLayout
        """
        nodes = self.window.ui.nodes

        nodes['status'] = QLabel(trans('status.started'))
        nodes['status'].setParent(self.window)

        nodes['status.agent'] = HelpLabel("")
        nodes['status.agent'].setParent(self.window)
        nodes['status.agent'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        nodes['global.stop'] = QPushButton("STOP")
        nodes['global.stop'].setParent(self.window)
        nodes['global.stop'].hide()
        nodes['global.stop'].clicked.connect(self.window.controller.ui.on_global_stop)

        nodes['anim.loading.status'] = Loader()
        nodes['anim.loading.status'].setParent(self.window)
        nodes['anim.loading.status'].hide()

        layout = QHBoxLayout()
        layout.addWidget(nodes['anim.loading.status'])
        layout.addWidget(nodes['status.agent'])
        layout.addWidget(nodes['status'])
        layout.addWidget(nodes['global.stop'])
        layout.setAlignment(Qt.AlignLeft)

        return layout