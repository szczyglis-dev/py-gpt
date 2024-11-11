#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.11 23:00:00                  #
# ================================================== #

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QCheckBox, QMenuBar

from pygpt_net.tools.html_canvas.ui.widgets import CanvasOutput, CanvasEdit
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.html import CustomWebEnginePage
from pygpt_net.utils import trans

class Canvas:
    def __init__(self, window=None):
        """
        HTML/JS canvas dialog

        :param window: Window instance
        """
        self.window = window
        self.menu_bar = None
        self.menu = {}
        self.actions = {}  # menu actions

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        # create menu bar
        self.menu_bar = QMenuBar()
        self.menu["file"] = self.menu_bar.addMenu(trans("menu.file"))

        self.actions["file.open"] = QAction(QIcon(":/icons/folder.svg"), trans("tool.html_canvas.menu.file.open"))
        self.actions["file.open"].triggered.connect(
            lambda: self.window.tools.get("html_canvas").open_file()
        )
        self.actions["file.save_as"] = QAction(QIcon(":/icons/save.svg"), trans("tool.html_canvas.menu.file.save_as"))
        self.actions["file.save_as"].triggered.connect(
            lambda: self.window.ui.nodes['html_canvas.output'].signals.save_as.emit(
                re.sub(r'\n{2,}', '\n\n', self.window.ui.nodes['html_canvas.output'].html_content), 'html')
        )
        self.actions["file.reload"] = QAction(QIcon(":/icons/reload.svg"), trans("tool.html_canvas.menu.file.reload"))
        self.actions["file.reload"].triggered.connect(
            lambda: self.window.tools.get("html_canvas").reload_output()
        )
        self.actions["file.clear"] = QAction(QIcon(":/icons/close.svg"), trans("tool.html_canvas.menu.file.clear"))
        self.actions["file.clear"].triggered.connect(
            lambda: self.window.tools.get("html_canvas").clear()
        )

        # add actions
        self.menu["file"].addAction(self.actions["file.open"])
        self.menu["file"].addAction(self.actions["file.save_as"])
        self.menu["file"].addAction(self.actions["file.reload"])
        self.menu["file"].addAction(self.actions["file.clear"])
        return self.menu_bar

    def setup(self):
        """Setup canvas dialog"""
        self.window.ui.nodes['html_canvas.output'] = CanvasOutput(self.window)
        self.window.ui.nodes['html_canvas.output'].setPage(
            CustomWebEnginePage(self.window, self.window.ui.nodes['html_canvas.output'])
        )
        self.window.ui.nodes['html_canvas.edit'] = CanvasEdit(self.window)
        self.window.ui.nodes['html_canvas.edit'].setVisible(False)
        self.window.ui.nodes['html_canvas.edit'].textChanged.connect(
            lambda: self.window.tools.get("html_canvas").save_output()
        )

        # edit checkbox
        self.window.ui.nodes['html_canvas.btn.edit'] = QCheckBox(trans("html_canvas.btn.edit"))
        self.window.ui.nodes['html_canvas.btn.edit'].stateChanged.connect(
            lambda: self.window.tools.get("html_canvas").toggle_edit()
        )

        path = self.window.tools.get("html_canvas").get_current_path()
        path_label = HelpLabel(path)
        path_label.setMaximumHeight(30)
        path_label.setAlignment(Qt.AlignRight)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['html_canvas.btn.edit'])
        bottom_layout.addWidget(path_label)

        output_layout = QVBoxLayout()
        output_layout.addWidget(self.window.ui.nodes['html_canvas.output'])
        output_layout.addWidget(self.window.ui.nodes['html_canvas.edit'])
        output_layout.setContentsMargins(0, 0, 0, 0)

        # connect signals
        self.window.ui.nodes['html_canvas.output'].signals.save_as.connect(self.window.tools.get("html_canvas").handle_save_as)
        self.window.ui.nodes['html_canvas.output'].signals.audio_read.connect(self.window.controller.chat.render.handle_audio_read)

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu())  # add menu bar
        layout.addLayout(output_layout)
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['html_canvas'] = CanvasDialog(self.window)
        self.window.ui.dialog['html_canvas'].setLayout(layout)
        self.window.ui.dialog['html_canvas'].setWindowTitle(trans("dialog.html_canvas.title"))
        self.window.ui.dialog['html_canvas'].resize(800, 500)


class CanvasDialog(BaseDialog):
    def __init__(self, window=None, id="html_canvas"):
        """
        HTML canvas dialog

        :param window: main window
        :param id: logger id
        """
        super(CanvasDialog, self).__init__(window, id)
        self.window = window

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(CanvasDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(CanvasDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        if self.window is None:
            return
        self.window.tools.get("html_canvas").opened = False
        self.window.tools.get("html_canvas").close()
        self.window.tools.get("html_canvas").update()
