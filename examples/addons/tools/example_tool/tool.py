"""Runnable GUI Tool add-on example."""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from pygpt_net.core.events import Event
from pygpt_net.tools.base import BaseTool


class ExampleTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = "example_tool"
        self.has_tab = False
        self._action = None
        self._selected_context_id = None

    def setup_menu(self):
        # setup_menu() is called while the Tools menu is built. Returning an
        # action here is enough to add a real menu item.
        self._action = QAction("External add-on example", self.window)
        self._action.setToolTip("Show data read through the PyGPT window API")
        self._action.triggered.connect(self._show_info)
        return {self.id: self._action}

    def handle(self, event):
        # GUI Tools receive the same global event stream before plugins.
        if event.name == Event.CTX_SELECT:
            self._selected_context_id = event.data.get("value")

    def _show_info(self):
        profile = self.window.core.config.get_user_path()
        message = (
            "This dialog comes from an external GUI Tool add-on.\n\n"
            f"Profile workdir: {profile}\n"
            f"Selected context id: {self._selected_context_id}"
        )
        QMessageBox.information(self.window, "Example Tool", message)
