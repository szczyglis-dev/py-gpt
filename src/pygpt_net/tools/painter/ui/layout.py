#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.12 14:45:00
# ================================================== #

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QRadioButton, QComboBox, QScrollArea, QLabel, QSizePolicy
from PySide6.QtCore import QSize, Qt

from pygpt_net.tools.painter.ui.canvas import PainterWidget
from pygpt_net.tools.painter.core.modes import DRAW_MODE_TRANSLATION_KEYS, DRAW_MODE_ICONS
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.option.combo import NoScrollCombo
from pygpt_net.utils import trans


class PainterLayout:
    def __init__(self, tool):
        """
        Painter UI

        :param window: Window instance
        """
        self.tool = tool
        self._initialized = False

    def init(self):
        """
        Initialize painter

        :return: QWidget
        """
        nodes = self.tool.nodes
        common = self.tool.settings

        if self.tool.canvas is None:
            self.tool.canvas = PainterWidget(self.tool)

        key = 'painter.select.draw.mode'
        if nodes.get(key) is None:
            cb = NoScrollCombo(self.window)
            cb.setMinimumContentsLength(10)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            for draw_mode in common.get_draw_modes():
                icon_path = DRAW_MODE_ICONS.get(draw_mode)
                if icon_path:
                    cb.addItem(
                        QIcon(icon_path),
                        trans(DRAW_MODE_TRANSLATION_KEYS[draw_mode]),
                        draw_mode.value,
                    )
                else:
                    cb.addItem(
                        trans(DRAW_MODE_TRANSLATION_KEYS[draw_mode]),
                        draw_mode.value,
                    )
            cb.currentIndexChanged.connect(lambda _idx: common.change_draw_mode(cb.currentData()))
            nodes[key] = cb

        key = 'painter.btn.brush'
        if nodes.get(key) is None:
            rb = QRadioButton(trans('painter.mode.paint'))
            rb.setChecked(True)
            rb.toggled.connect(self.tool.settings.set_brush_mode)
            nodes[key] = rb

        key = 'painter.btn.erase'
        if nodes.get(key) is None:
            rb = QRadioButton(trans('painter.mode.erase'))
            rb.toggled.connect(self.tool.settings.set_erase_mode)
            nodes[key] = rb

        key = 'painter.select.brush.size'
        if nodes.get(key) is None:
            sizes = common.get_sizes()
            cb = NoScrollCombo(self.window)
            cb.addItems(sizes)
            cb.currentTextChanged.connect(common.change_brush_size)
            cb.setMinimumContentsLength(10)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            nodes[key] = cb

        key = 'painter.select.canvas.size'
        if nodes.get(key) is None:
            canvas_sizes = common.get_canvas_sizes()
            cb = NoScrollCombo(self.window)
            cb.addItems(canvas_sizes)
            cb.setMinimumContentsLength(20)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            cb.currentTextChanged.connect(common.change_canvas_size)
            nodes[key] = cb

        key = 'painter.select.brush.color'
        if nodes.get(key) is None:
            cb = NoScrollCombo(self.window)
            cb.setIconSize(QSize(16, 16))
            colors = common.get_colors()
            for color_name, color_value in colors.items():
                pixmap = QPixmap(16, 16)
                pixmap.fill(color_value)
                icon = QIcon(pixmap)
                cb.addItem(icon, color_name, color_value)
            cb.currentTextChanged.connect(common.change_brush_color)
            cb.setMinimumContentsLength(10)
            cb.setMinimumWidth(205)
            cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            nodes[key] = cb

            # Zoom combo (view-only scale) placed to the right of canvas size
            key = 'painter.select.zoom'
            if nodes.get(key) is None:
                cb = NoScrollCombo(self.window)
                cb.setMinimumContentsLength(8)
                cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)

                # Preferred preset steps from widget; fallback to defaults
                steps = []
                if self.tool.canvas is not None:
                    try:
                        steps = self.tool.canvas.viewport.steps()
                    except Exception:
                        steps = []
                if not steps:
                    steps = [10, 25, 50, 75, 100, 150, 200, 500, 1000]

                cb.addItems([f"{p}%" for p in steps])

                # User -> widget
                cb.currentTextChanged.connect(self.tool.canvas.viewport.on_zoom_changed)

                # Widget -> combo (also covers CTRL+wheel and programmatic changes)
                def _sync_zoom_combo_from_widget(z):
                    """Keep zoom combobox in sync with the widget's zoom."""
                    percent = int(round(float(z) * 100))
                    label = f"{percent}%"
                    cb.blockSignals(True)
                    idx = cb.findText(label)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
                    else:
                        # Insert missing value keeping ascending order
                        items = [cb.itemText(i) for i in range(cb.count())]
                        if label not in items:
                            items.append(label)
                            try:
                                items_sorted = sorted(
                                    set(items),
                                    key=lambda s: float(s.replace('%', '').strip())
                                )
                            except Exception:
                                items_sorted = items
                            cb.clear()
                            cb.addItems(items_sorted)
                        cb.setCurrentText(label)
                    cb.blockSignals(False)

                # Keep reference to prevent GC of the inner function
                cb._sync_zoom_combo_from_widget = _sync_zoom_combo_from_widget
                if hasattr(self.tool.canvas, 'zoomChanged'):
                    self.tool.canvas.zoomChanged.connect(cb._sync_zoom_combo_from_widget)

                # Initial label; actual value will be set by load_zoom below
                cb.setCurrentText("100%")
                nodes[key] = cb

        key = 'painter.icon.zoom'
        if nodes.get(key) is None:
            label = QLabel()
            label.setPixmap(QIcon(":/icons/zoom_in.svg").pixmap(QSize(16, 16)))
            label.setFixedSize(QSize(16, 16))
            nodes[key] = label

        self._initialized = True

    @property
    def window(self):
        return self.tool.window

    def build(self):
        self.init()
        body = PainterTab(self.tool)
        body.setLayout(self.setup_painter())
        body.layout().setContentsMargins(15, 0, 15, 0)
        self.tool.canvas.bind_clipboard_shortcuts(body, self.tool.scroll_area)
        for key, translation in {
            'painter.btn.brush': 'painter.mode.paint',
            'painter.btn.erase': 'painter.mode.erase',
            'tip.output.tab.draw': 'tip.output.tab.draw',
        }.items():
            self.tool.add_lang_mapping(self.tool.nodes[key], translation)
        return body

    def setup_painter(self) -> QVBoxLayout:
        """
        Setup painter

        :return: QVBoxLayout
        """
        nodes = self.tool.nodes

        top = QHBoxLayout()
        top.addWidget(nodes['painter.btn.brush'])
        top.addWidget(nodes['painter.btn.erase'])
        top.addWidget(nodes['painter.select.draw.mode'])
        top.addWidget(nodes['painter.select.brush.size'])
        top.addWidget(nodes['painter.select.brush.color'])
        top.addWidget(nodes['painter.select.canvas.size'])
        # Zoom icon + combo placed right after canvas size
        top.addWidget(nodes['painter.icon.zoom'])
        top.addWidget(nodes['painter.select.zoom'])
        top.addStretch(1)

        if self.tool.scroll_area is None:
            self.tool.scroll_area = QScrollArea()
            self.tool.scroll_area.setWidget(self.tool.canvas)
            # Must be False to allow content widget to grow/shrink with zoom and show scrollbars
            self.tool.scroll_area.setWidgetResizable(False)
        else:
            if self.tool.scroll_area.widget() is not self.tool.canvas:
                self.tool.scroll_area.setWidget(self.tool.canvas)
            self.tool.scroll_area.setWidgetResizable(False)

        # The zoomed canvas must not determine the containing tab's size.
        # Keep both scrollbars inside the space allocated to the viewport.
        self.tool.scroll_area.setMinimumSize(0, 0)
        self.tool.scroll_area.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.tool.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tool.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # At high zoom the proportional thumb can become only a few pixels
        # tall. Give it a usable minimum size without changing theme colors.
        self.tool.scroll_area.setStyleSheet("""
            QScrollBar::handle:vertical { min-height: 32px; }
            QScrollBar::handle:horizontal { min-width: 32px; }
        """)

        if nodes.get('tip.output.tab.draw') is None:
            nodes['tip.output.tab.draw'] = HelpLabel(trans('tip.output.tab.draw'), self.window)
        nodes['tip.output.tab.draw'].setMinimumWidth(0)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.tool.scroll_area, 1)
        layout.addWidget(nodes['tip.output.tab.draw'])
        layout.setContentsMargins(0, 0, 0, 0)

        return layout


class PainterTab(QWidget):
    """A single drawing frontend managed through the normal tool tab API."""
    def __init__(self, tool):
        super().__init__()
        self.tool = tool
        self.tab = None

    def set_tab(self, tab):
        self.tab = tab
        self.tool.canvas.set_tab(tab)

    def on_delete(self):
        if self.tool.frontend is not self:
            return
        self.tool.storage.save()
        self.tool.unregister_surface(self.tool)
        self.tool.canvas.viewport.stop_autoscroll()
        self.tool.canvas.cancel_active_drawing()
        self.tool.canvas.text.cancel(self.tool.canvas)
        self.tool.canvas = None
        self.tool.scroll_area = None
        self.tool.frontend = None
        self.tool.nodes.clear()
