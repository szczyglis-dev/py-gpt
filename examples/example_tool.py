#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT GUI tool tutorial                            #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLabel, QMenuBar, QPushButton, QVBoxLayout

from pygpt_net.tools.base import BaseTool
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans


class ExampleTool(BaseTool):
    """Example application tool with one Tools-menu action and one dialog.

    A BaseTool is a UI/application extension, not automatically a model-callable
    tool. Model commands belong in plugins (see `example_plugin.py`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_tool"  # must be unique
        self.dialog_id = "example_dialog"
        self.has_tab = False  # set True + implement as_tab() to expose a tab tool
        self.tab_title = "Example Tool"
        self.tab_icon = ":/icons/build.svg"
        self.dialog = None
        self.opened = False

    def setup(self):
        """Called once after the tool is attached to the main window."""
        # Connect signals/load persistent state here. `self.window` is available.
        pass

    def post_setup(self):
        """Called after plugins are also loaded; useful for cross-component wiring."""
        pass

    def on_update(self):
        """Called by the application main-loop timer.

        Keep this method lightweight. Do not print/log every tick in production.
        """
        pass

    def on_post_update(self):
        """Second update hook, called after the regular tool update pass."""
        pass

    def setup_theme(self):
        """Refresh theme-dependent icons/styles when the UI theme changes."""
        pass

    def on_reload(self):
        """Called when the active PyGPT profile/workdir is reloaded."""
        pass

    def on_exit(self):
        """Release external resources here before application shutdown."""
        pass

    def open(self):
        if self.opened:
            return
        self.window.ui.dialogs.open(self.dialog_id, width=800, height=600)
        self.opened = True

    def close(self):
        self.window.ui.dialogs.close(self.dialog_id)
        self.opened = False

    def toggle(self):
        self.close() if self.opened else self.open()

    def on_close(self):
        """Synchronize tool state when the user closes the dialog directly."""
        self.opened = False

    def example_action(self):
        self.window.ui.dialogs.alert("Hello from Example Tool!")

    def setup_menu(self) -> dict:
        """Return actions that the Tools menu manager should insert.

        The manager prefixes returned keys with `tools.` internally. The key
        below therefore becomes `tools.example` in the application's menu map.
        """
        action = QAction(
            QIcon(":/icons/build.svg"),
            "Example Tool",
            self.window,
            checkable=False,
        )
        action.triggered.connect(self.toggle)
        return {"example": action}

    def setup_dialogs(self):
        """Create static dialog instances before normal tool setup runs."""
        self.dialog = DialogBuilder(self.window, self)
        self.dialog.setup()

    def get_lang_mappings(self) -> dict:
        """Optional menu-to-translation mappings.

        This self-contained tutorial uses a literal English menu label and ships
        no locale file, so there is nothing to map. A localized tool can return
        the same mapping shape used by PyGPT's built-in tools.
        """
        return {}


class DialogBuilder:
    """Build widgets/layout and register a static dialog in `window.ui.dialog`."""

    def __init__(self, window, tool: ExampleTool):
        self.window = window
        self.tool = tool
        self.menu_bar = None
        self.actions = {}

    def setup_menu(self) -> QMenuBar:
        self.menu_bar = QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        file_menu = self.menu_bar.addMenu(trans("menu.file"))

        action = QAction(QIcon(":/icons/info.svg"), "Example action", self.menu_bar)
        action.triggered.connect(self.tool.example_action)
        self.actions["example_action"] = action
        file_menu.addAction(action)
        return self.menu_bar

    def setup(self):
        label = QLabel("Hello World!")
        button = QPushButton("Example action")
        button.clicked.connect(self.tool.example_action)

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu())
        layout.addWidget(label, alignment=Qt.AlignCenter)
        layout.addWidget(button)

        dialog = ExampleDialog(self.window, self.tool, id=self.tool.dialog_id)
        dialog.setLayout(layout)
        dialog.setWindowTitle("Example Tool")
        self.window.ui.dialog[self.tool.dialog_id] = dialog


class ExampleDialog(BaseDialog):
    def __init__(self, window, tool: ExampleTool, id: str = None):
        super().__init__(window, id=id)
        self.tool = tool

    def closeEvent(self, event):
        self.tool.on_close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
