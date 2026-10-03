"""Painter tool: lifecycle, frontend ownership and image entry points."""
import os

from PySide6.QtGui import QAction, QIcon

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.base import BaseTool, ToolMenuAction
from pygpt_net.utils import trans
from .core.capture import Capture
from .core.settings import Settings
from .core.storage import Storage
from .ui.layout import PainterLayout


class Painter(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = 'painter'
        self.allow_tab = True
        self.allow_dialog = False
        self.multi_tab = False
        self.on_menu_click = ToolMenuAction.ALWAYS_TAB
        self.tab_title = 'output.tab.painter'
        self.tab_icon = ':/icons/brush.svg'
        self.canvas = None
        self.scroll_area = None
        self.frontend = None
        self.nodes = {}
        self.settings = Settings(self)
        self.capture = Capture(self)
        self.storage = Storage(self)
        self.layout = PainterLayout(self)

    def ensure_canvas(self):
        """Create the drawing frontend only when Painter is first used."""
        if self.canvas is None:
            self.frontend = self.layout.build()
            self.on_reload()
        return self.canvas

    def as_tab(self, tab):
        self.ensure_canvas()
        self.frontend.set_tab(tab)
        self.register_surface(self, self.frontend, tab=tab)
        return self.frontend

    def create_surface(self):
        self.open_tab()
        return self

    def open(self, path=None):
        """Reveal Painter, optionally loading an image."""
        self.open_tab()
        if path is not None:
            self.canvas.document.open(path)
            self.window.update_status('Image loaded: ' + os.path.basename(path))
        return self.canvas

    def is_active(self):
        tab = self.window.controller.tabs.get_current_tab()
        return tab is not None and tab.type == Tab.TAB_TOOL and tab.tool_id == self.id

    def on_selected(self, tab):
        if self.window.core.config.get('vision.capture.enabled'):
            self.window.controller.camera.enable_capture()

    def on_reload(self):
        if self.canvas is None:
            return
        self.storage.restore()
        config = self.window.core.config
        size = config.get('painter.canvas.size') if config.has('painter.canvas.size') else '800x600'
        self.settings.change_canvas_size(size)
        self.settings.restore_brush_settings()
        self.canvas.history.undo_stack.clear()
        self.canvas.history.redo_stack.clear()

    def on_exit(self):
        self.storage.save()

    def apply_lang_mappings(self):
        super().apply_lang_mappings()
        if self.canvas is not None:
            self.settings.retranslate_draw_modes()

    def setup_menu(self):
        action = QAction(QIcon(self.tab_icon), trans(self.tab_title), self.window)
        action.triggered.connect(self.on_menu_action)
        self.add_lang_mapping(action, self.tab_title)
        return {self.id: action}
