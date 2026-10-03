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

from pygpt_net.ui.widget.draw.painter import PainterWidget
from pygpt_net.ui.widget.draw.modes import DRAW_MODE_TRANSLATION_KEYS, DRAW_MODE_ICONS
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.option.combo import NoScrollCombo
from pygpt_net.utils import trans


class Painter:
    def __init__(self, window=None):
        """
        Painter UI

        :param window: Window instance
        """
        self.window = window
        self._initialized = False

    def init(self):
        """
        Initialize painter

        :return: QWidget
        """
        ui = self.window.ui
        nodes = ui.nodes
        common = self.window.controller.painter.common

        if getattr(ui, 'painter', None) is None:
            ui.painter = PainterWidget(self.window)

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
            rb.toggled.connect(self.window.controller.painter.common.set_brush_mode)
            nodes[key] = rb

        key = 'painter.btn.erase'
        if nodes.get(key) is None:
            rb = QRadioButton(trans('painter.mode.erase'))
            rb.toggled.connect(self.window.controller.painter.common.set_erase_mode)
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
                if hasattr(ui.painter, 'get_zoom_steps_percent'):
                    try:
                        steps = ui.painter.get_zoom_steps_percent()
                    except Exception:
                        steps = []
                if not steps:
                    steps = [10, 25, 50, 75, 100, 150, 200, 500, 1000]

                cb.addItems([f"{p}%" for p in steps])

                # User -> widget
                cb.currentTextChanged.connect(ui.painter.on_zoom_combo_changed)

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
                if hasattr(ui.painter, 'zoomChanged'):
                    ui.painter.zoomChanged.connect(cb._sync_zoom_combo_from_widget)

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

    def setup(self) -> QWidget:
        """
        Setup painter

        :return: QWidget
        """
        self.init()
        body = self.window.core.tabs.from_layout(self.setup_painter())
        # from_layout resets margins; apply the painter's spacing afterwards.
        body.layout().setContentsMargins(15, 0, 15, 0)
        self.window.ui.painter.bind_clipboard_shortcuts(body, self.window.ui.painter_scroll)
        body.append(self.window.ui.painter)
        return body

    def setup_painter(self) -> QVBoxLayout:
        """
        Setup painter

        :return: QVBoxLayout
        """
        ui = self.window.ui
        nodes = ui.nodes

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

        if getattr(ui, 'painter_scroll', None) is None:
            ui.painter_scroll = QScrollArea()
            ui.painter_scroll.setWidget(ui.painter)
            # Must be False to allow content widget to grow/shrink with zoom and show scrollbars
            ui.painter_scroll.setWidgetResizable(False)
        else:
            if ui.painter_scroll.widget() is not ui.painter:
                ui.painter_scroll.setWidget(ui.painter)
            ui.painter_scroll.setWidgetResizable(False)

        # The zoomed canvas must not determine the containing tab's size.
        # Keep both scrollbars inside the space allocated to the viewport.
        ui.painter_scroll.setMinimumSize(0, 0)
        ui.painter_scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        ui.painter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        ui.painter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # At high zoom the proportional thumb can become only a few pixels
        # tall. Give it a usable minimum size without changing theme colors.
        ui.painter_scroll.setStyleSheet("""
            QScrollBar:vertical { width: 12px; }
            QScrollBar:horizontal { height: 12px; }
            QScrollBar::handle:vertical { min-height: 32px; }
            QScrollBar::handle:horizontal { min-width: 32px; }
        """)

        if nodes.get('tip.output.tab.draw') is None:
            nodes['tip.output.tab.draw'] = HelpLabel(trans('tip.output.tab.draw'), self.window)
        nodes['tip.output.tab.draw'].setMinimumWidth(0)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(ui.painter_scroll, 1)
        layout.addWidget(nodes['tip.output.tab.draw'])
        layout.setContentsMargins(0, 0, 0, 0)

        return layout
