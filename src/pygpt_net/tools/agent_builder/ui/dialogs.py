#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 00:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QVBoxLayout, QMenuBar, QSplitter, QSizePolicy, QWidget

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.node_editor.editor import NodeEditor
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

from .list import AgentsWidget


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
        """Setup agent_builder dialog menu"""
        self.menu_bar = QMenuBar(parent)
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))
        t = self.tool

        self.actions["open"] = QAction(QIcon(":/icons/reload.svg"), trans("action.reload"), self.menu_bar)
        self.actions["open"].triggered.connect(lambda checked=False, t=t: t.load())

        self.actions["save"] = QAction(QIcon(":/icons/save.svg"), trans("action.save"), self.menu_bar)
        self.actions["save"].triggered.connect(lambda checked=False, t=t: t.save())

        self.actions["clear"] = QAction(QIcon(":/icons/close.svg"), trans("action.clear"), self.menu_bar)
        self.actions["clear"].triggered.connect(lambda checked=False, t=t: t.clear())

        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["save"])
        self.file_menu.addAction(self.actions["clear"])
        return self.menu_bar

    def setup(self):
        """Setup agent_builder dialog"""
        # Ensure previous deferred deletions are flushed before building a new editor instance
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QApplication.processEvents()
        except Exception:
            pass

        id = 'agent.builder'
        u = self.window.ui

        u.dialog['agent.builder'] = BuilderDialog(self.window)
        dlg = u.dialog['agent.builder']

        registry = self.tool.get_registry()  # node types
        editor = NodeEditor(
            parent=dlg,
            registry=registry
        )  # parent == dialog

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
        editor.on_clear = self.tool.clear
        editor.editing_allowed = self.tool.editing_allowed

        u.editor[id] = editor

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu(dlg))

        agents_list = AgentsWidget(self.window, tool=self.tool, parent=dlg)
        list_widget = agents_list.setup()

        # Left side container: list fills all space, help label stays at the bottom
        left_side = QWidget(dlg)
        left_layout = QVBoxLayout(left_side)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        left_help_label = HelpLabel(trans("node.editor.list.tip"))
        left_help_label.setWordWrap(True)
        left_help_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        left_help_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left_help_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        left_layout.addWidget(list_widget)
        left_layout.addWidget(left_help_label)
        left_layout.setStretch(0, 1)  # list -> fills all vertical space

        # Fix the width of the whole left panel (not only the list)
        left_side.setFixedWidth(250)

        center_splitter = QSplitter(Qt.Horizontal)
        center_splitter.addWidget(left_side)
        center_splitter.addWidget(u.editor[id])
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 8)
        layout.addWidget(center_splitter)
        # Make the splitter take all extra vertical space so the legend stays compact at the bottom
        layout.setStretch(0, 1)

        # Bottom legend as a compact, centered help label
        legend_label = HelpLabel(trans("node.editor.bottom.tip"))
        legend_label.setAlignment(Qt.AlignCenter)
        legend_label.setWordWrap(True)
        legend_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        legend_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        layout.addWidget(legend_label)

        u.nodes["agent.builder.splitter"] = center_splitter
        u.nodes["agent.builder.list"] = agents_list
        u.nodes["agent.builder.legend"] = legend_label
        u.nodes["agent.builder.list.help"] = left_help_label

        dlg.setLayout(layout)
        dlg.setWindowTitle(trans("agent.builder.title"))

    def clear(self):
        """Clear dialog"""
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
        self._cleaned = False

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
            self.close()
        else:
            super(BuilderDialog, self).keyPressEvent(event)

    def cleanup(self):
        """Cleanup on dialog close"""
        if self._cleaned:
            return
        self._cleaned = True

        tool = self.window.tools.get("agent_builder")
        if tool:
            try:
                tool.on_close()  # store current state (layout, nodes positions, etc.)
            except Exception:
                pass

        u = self.window.ui

        try:
            u.nodes["agent.builder.list"].cleanup()
        except Exception as e:
            print("Agents list close failed:", e)

        splitter = u.nodes.get("agent.builder.splitter")
        editor = u.editor.pop('agent.builder', None)

        # Detach editor from splitter before closing/deleting it to avoid dangling pointers in QSplitter
        try:
            if splitter is not None and editor is not None:
                # Ensure the editor actually belongs to this splitter
                idx = splitter.indexOf(editor) if editor.parent() is splitter else -1
                if idx != -1:
                    # Create the replacement without a parent; QSplitter will adopt it.
                    from PySide6.QtWidgets import QWidget as _QW
                    placeholder = _QW()
                    splitter.replaceWidget(idx, placeholder)
        except Exception as e:
            print("Splitter detach failed:", e)

        if editor is not None:
            try:
                editor.setStyleSheet("")
            except Exception:
                pass
            try:
                editor.close()
            except Exception as e:
                print("NodeEditor close failed:", e)
            try:
                editor.setParent(None)
                editor.deleteLater()
            except Exception:
                pass

        # Dispose legend label safely
        legend = u.nodes.pop("agent.builder.legend", None)
        if legend is not None:
            try:
                legend.setParent(None)
                legend.deleteLater()
            except Exception:
                pass

        # Dispose left-side help label safely
        try:
            help_lbl = u.nodes.pop("agent.builder.list.help", None)
            if help_lbl is not None:
                help_lbl.setParent(None)
                help_lbl.deleteLater()
        except Exception:
            pass

        # Drop splitter reference
        try:
            u.nodes.pop("agent.builder.splitter", None)
        except Exception:
            pass

        # Ensure all deferred deletions are processed (do it a few rounds to be safe)
        try:
            from PySide6.QtWidgets import QApplication
            for _ in range(3):
                QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                QApplication.processEvents()
        except Exception:
            pass