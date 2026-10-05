#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
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
        self._toolbox_min_width = None

    def home(self):
        return self.window.controller.tabs.open_or_activate(Tab.TAB_CHAT, create=False)

    def toggle_tool(self, tab_type, tool_id=None):
        """Collapse a tool already selected on the right; otherwise reveal it."""
        tabs = self.window.controller.tabs
        current = tabs.get_current_by_column(1)
        if tabs.is_split_screen_enabled() and current is not None and current.type == tab_type and (tool_id is None or current.tool_id == tool_id):
            tabs.disable_split_screen()
            return current
        return tabs.open_or_activate(tab_type, tool_id) if tool_id else tabs.open_or_activate(tab_type)

    def toggle_toolbox(self, checked=False):
        """Slide the toolbox in/out, preserving the conversation list width."""
        from pygpt_net.ui.layout.sidebar import pane_sizes, placement
        splitter = self.window.ui.splitters['main']
        toolbox = self.window.ui.parts['toolbox']
        toolbox_idx = splitter.indexOf(toolbox)
        ctx_idx = splitter.indexOf(self.window.ui.parts['ctx'])
        sizes = splitter.sizes()
        if self._animation is not None:
            self._animation.stop()
        if self._toolbox_min_width is None:
            self._toolbox_min_width = toolbox.minimumWidth()
        toolbox.setMinimumWidth(0)
        opening = not self._toolbox_visible
        self._toolbox_visible = opening
        if not opening and sizes[toolbox_idx] > 0:
            self._toolbox_width = sizes[toolbox_idx]
            self.window.core.config.set('layout.toolbox.width', sizes[toolbox_idx])
        if opening:
            remembered = self.window.core.config.get('layout.toolbox.width', self._toolbox_width)
            if isinstance(remembered, (int, float)) and remembered > 0:
                self._toolbox_width = int(remembered)
            toolbox.show()
        total = sum(sizes)
        ctx_width = sizes[ctx_idx]
        target = min(self._toolbox_width, max(0, total - ctx_width - 200)) if opening else 0
        animation = QVariantAnimation(self.window)
        if self._animation is not None:
            self._animation.deleteLater()
        self._animation = animation
        animation.setDuration(PANEL_ANIMATION_DURATION_MS)
        animation.setEasingCurve(PANEL_ANIMATION_EASING)
        animation.setStartValue(sizes[toolbox_idx])
        animation.setEndValue(target)
        position = placement(self.window.core.config)
        animation.valueChanged.connect(
            lambda width: splitter.setSizes(pane_sizes(
                int(width), ctx_width, max(0, total - ctx_width - int(width)), position,
            ))
        )
        animation.finished.connect(lambda: self._finish_toolbox_animation(opening))
        self.window.ui.nodes['toolbar.toolbox'].setChecked(opening)
        self.window.core.config.set('layout.toolbox.expanded', opening)
        self.window.core.config.save()
        animation.start()

    def restore_toolbox_state(self):
        """Restore the saved visibility and width after main-pane geometry."""
        from pygpt_net.ui.layout.sidebar import pane_sizes, placement
        config = self.window.core.config
        splitter = self.window.ui.splitters['main']
        toolbox = self.window.ui.parts['toolbox']
        if self._animation is not None:
            self._animation.stop()
        if self._toolbox_min_width is not None:
            toolbox.setMinimumWidth(self._toolbox_min_width)
        sizes = splitter.sizes()
        ctx_width = sizes[splitter.indexOf(self.window.ui.parts['ctx'])]
        available = sum(sizes) - ctx_width
        self._toolbox_visible = config.get('layout.toolbox.expanded', False) is True
        remembered = config.get('layout.toolbox.width', self._toolbox_width)
        if isinstance(remembered, (int, float)) and remembered > 0:
            self._toolbox_width = int(remembered)
        width = min(self._toolbox_width, max(0, available - 200)) if self._toolbox_visible else 0
        toolbox.setVisible(self._toolbox_visible)
        splitter.setSizes(pane_sizes(width, ctx_width, available - width, placement(config)))
        self.window.ui.nodes['toolbar.toolbox'].setChecked(self._toolbox_visible)
        self.window.ui.update_toolbox_button()

    def apply_toolbox_placement(self):
        """Reorder existing panes without rebuilding their contents."""
        from pygpt_net.ui.layout.sidebar import pane_order, placement
        splitter = self.window.ui.splitters['main']
        if self._animation is not None:
            self._animation.stop()
        sizes = splitter.sizes()
        widths = {name: sizes[splitter.indexOf(self.window.ui.parts[name])]
                  for name in ('ctx', 'toolbox', 'chat')}
        order = pane_order(placement(self.window.core.config))
        for index, name in enumerate(order):
            splitter.insertWidget(index, self.window.ui.parts[name])
        for index, name in enumerate(order):
            splitter.setStretchFactor(index, int(name == 'chat'))
        if not self._toolbox_visible:
            widths['chat'] += widths['toolbox']
            widths['toolbox'] = 0
            self.window.ui.parts['toolbox'].hide()
        if self._toolbox_min_width is not None:
            self.window.ui.parts['toolbox'].setMinimumWidth(self._toolbox_min_width)
        splitter.setSizes([widths[name] for name in order])
        self.window.ui.update_toolbox_button()

    def _finish_toolbox_animation(self, opening):
        toolbox = self.window.ui.parts['toolbox']
        if not opening:
            toolbox.hide()
        if self._toolbox_min_width is not None:
            toolbox.setMinimumWidth(self._toolbox_min_width)
