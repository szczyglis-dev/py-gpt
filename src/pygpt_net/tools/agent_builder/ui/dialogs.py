#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QVBoxLayout, QMenuBar, QSplitter

from pygpt_net.tools.agent_builder.ui.list import AgentsWidget
from pygpt_net.ui.widget.builder.editor import NodeEditor
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans


class Builder:

    def __init__(self, window=None, tool=None):
        """
        Builder dialog

        :param window: Window instance
        """
        self.window = window
        self.tool = tool
        self.menu_bar = None
        self.file_menu = None
        self.actions = {}

    def setup_menu(self, parent=None) -> QMenuBar:
        """Setup audio agent_builder dialog menu"""
        self.menu_bar = QMenuBar(parent)
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))
        t = self.tool

        self.actions["open"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open"), self.menu_bar)
        self.actions["open"].triggered.connect(lambda checked=False, t=t: t.load())

        self.actions["save"] = QAction(QIcon(":/icons/save.svg"), trans("action.save"), self.menu_bar)
        self.actions["save"].triggered.connect(lambda checked=False, t=t: t.save())

        self.actions["clear"] = QAction(QIcon(":/icons/clear.svg"), trans("action.clear"), self.menu_bar)
        self.actions["clear"].triggered.connect(lambda checked=False, t=t: t.clear())

        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["save"])
        self.file_menu.addAction(self.actions["clear"])
        return self.menu_bar

    def setup(self):
        """Setup agent_builder dialog"""
        id = 'agent.builder'
        u = self.window.ui

        u.dialog['agent.builder'] = BuilderDialog(self.window)
        dlg = u.dialog['agent.builder']

        editor = NodeEditor(dlg)  # parent == dialog
        editor.setStyleSheet("""
            NodeEditor {
                qproperty-gridBackColor: #242629;
                qproperty-gridPenColor:  #3b3f46;
    
                qproperty-nodeBackgroundColor: #2d2f34;
                qproperty-nodeBorderColor:     #4b4f57;
                qproperty-nodeSelectionColor:  #ff9900;
                qproperty-nodeTitleColor:      #3a3d44;
    
                qproperty-portInputColor:      #66b2ff;
                qproperty-portOutputColor:     #70e070;
                qproperty-portConnectedColor:  #ffd166;
    
                qproperty-edgeColor:           #c0c0c0;
                qproperty-edgeSelectedColor:   #ff8a5c;
            }
            """)

        # Demo: add a couple of nodes
        #editor.add_node("Value/Float", QPointF(100, 120))
        #editor.add_node("Value/Float", QPointF(100, 240))
        #editor.add_node("Math/Add", QPointF(420, 180))
        editor.on_clear = self.tool.clear

        u.editor[id] = editor

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu(dlg))

        agents_list = AgentsWidget(self.window, tool=self.tool)
        list_widget = agents_list.setup()
        list_widget.setFixedWidth(250)
        center_splitter = QSplitter(Qt.Horizontal)
        center_splitter.addWidget(list_widget)
        center_splitter.addWidget(u.editor[id])
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 8)
        layout.addWidget(center_splitter)

        u.nodes["agent.builder.list"] = agents_list

        dlg.setLayout(layout)
        dlg.setWindowTitle(trans("agent.builder.title"))

    def clear(self):
        """Clear transcribe dialog"""
        pass


class BuilderDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        BuilderDialog

        :param window: main window
        :param id: configurator id
        """
        super(BuilderDialog, self).__init__(window, id)
        self.window = window
        self.id = id  # id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(BuilderDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()
        else:
            super(BuilderDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.tools.get("agent_builder").on_close()