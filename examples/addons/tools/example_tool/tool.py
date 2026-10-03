"""Runnable GUI Tool add-on example."""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from pygpt_net.core.events import Event
from pygpt_net.tools.base import BaseTool, ToolMenuAction


class ExampleTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = "example_tool"
        self.allow_tab = False
        self.allow_dialog = True
        self.multi_tab = False
        self.multi_dialog = False
        self.on_menu_click = ToolMenuAction.ALWAYS_DIALOG
        self.dialog_id = "addon.example_tool"
        self._action = None
        self._selected_context_id = None

    def setup_menu(self):
        # setup_menu() is called while the Tools menu is built. Returning an
        # action here is enough to add a real menu item.
        # The locale domain is assigned by the Add-on loader before setup_menu()
        # runs. add_lang_mapping() keeps private Qt objects synchronized when
        # the user changes the application language at runtime.
        self._action = QAction(self.trans("menu.title"), self.window)
        self._action.setToolTip(self.trans("menu.tooltip"))
        self.add_lang_mapping(self._action, "menu.title")
        self.add_lang_mapping(self._action, "menu.tooltip", setter="setToolTip")
        self._action.triggered.connect(self.on_menu_action)
        return {self.id: self._action}

    def handle(self, event):
        # GUI Tools receive the same global event stream before plugins.
        if event.name == Event.CTX_SELECT:
            self._selected_context_id = event.data.get("value")

    def open(self):
        # Guard direct calls as well as policy-aware menu dispatch.
        if not self.can_open_dialog():
            return None
        profile = self.window.core.config.get_user_path()
        message = self.trans("dialog.message").format(
            profile=profile,
            context=self._selected_context_id,
        )
        dialog = self.window.ui.dialog.get(self.dialog_id)
        if dialog is None:
            dialog = QMessageBox(self.window)
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok)
            self.window.ui.dialog[self.dialog_id] = dialog
            self.add_lang_mapping(dialog, "dialog.title", setter="setWindowTitle")
        dialog.setText(message)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog
