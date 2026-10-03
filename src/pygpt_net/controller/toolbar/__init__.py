"""Navigation actions for the persistent left toolbar."""
from PySide6.QtCore import QVariantAnimation
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.types.animation import PANEL_ANIMATION_DURATION_MS, PANEL_ANIMATION_EASING


class Toolbar:
    def __init__(self, window=None):
        self.window = window
        self._toolbox_visible = False
        self._toolbox_width = 260
        self._animation = None

    def home(self):
        return self.window.controller.tabs.open_or_activate(Tab.TAB_CHAT, create=False)

    def files(self):
        return self.toggle_tool(Tab.TAB_FILES)

    def painter(self):
        return self.toggle_tool(Tab.TAB_TOOL_PAINTER)

    def toggle_tool(self, tab_type):
        """Collapse a tool already selected on the right; otherwise reveal it."""
        tabs = self.window.controller.tabs
        current = tabs.get_current_by_column(1)
        if tabs.is_split_screen_enabled() and current is not None and current.type == tab_type:
            tabs.disable_split_screen()
            return current
        return tabs.open_or_activate(tab_type)

    def toggle_toolbox(self, checked=False):
        """Slide the toolbox in/out, preserving the conversation list width."""
        splitter = self.window.ui.splitters['main']
        toolbox = self.window.ui.parts['toolbox']
        sizes = splitter.sizes()
        if self._animation is not None:
            self._animation.stop()
        opening = not self._toolbox_visible
        self._toolbox_visible = opening
        if not opening and sizes[0] > 0:
            self._toolbox_width = sizes[0]
            self.window.core.config.set('layout.toolbox.width', sizes[0])
        if opening:
            remembered = self.window.core.config.get('layout.toolbox.width', self._toolbox_width)
            if isinstance(remembered, (int, float)) and remembered > 0:
                self._toolbox_width = int(remembered)
            toolbox.show()
        total = sum(sizes)
        ctx_width = sizes[1]
        target = min(self._toolbox_width, max(0, total - ctx_width - 200)) if opening else 0
        animation = QVariantAnimation(self.window)
        if self._animation is not None:
            self._animation.deleteLater()
        self._animation = animation
        animation.setDuration(PANEL_ANIMATION_DURATION_MS)
        animation.setEasingCurve(PANEL_ANIMATION_EASING)
        animation.setStartValue(sizes[0])
        animation.setEndValue(target)
        animation.valueChanged.connect(
            lambda width: splitter.setSizes([int(width), ctx_width, max(0, total - ctx_width - int(width))])
        )
        animation.finished.connect(lambda: self._finish_toolbox_animation(opening))
        self.window.ui.nodes['toolbar.toolbox'].setChecked(opening)
        animation.start()

    def _finish_toolbox_animation(self, opening):
        if not opening:
            self.window.ui.parts['toolbox'].hide()
