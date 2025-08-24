#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QSplitter, QSizePolicy, QRadioButton, QCheckBox, QButtonGroup

from pygpt_net.ui.widget.calendar.select import CalendarSelect
from pygpt_net.ui.widget.element.checkbox import ColorCheckbox
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.calendar_note import CalendarNote
from pygpt_net.utils import trans


class Calendar:
    __slots__ = ('window',)

    def __init__(self, window=None):
        """
        Calendar UI

        :param window: Window instance
        """
        self.window = window

    def init(self):
        """
        Initialize painter

        :return: QWidget
        """
        ui = self.window.ui
        ui.calendar['select'] = CalendarSelect(self.window)
        ui.calendar['select'].setMinimumSize(200, 200)
        ui.calendar['select'].setGridVisible(True)
        ui.calendar['note'] = CalendarNote(self.window)

    def setup(self) -> QWidget:
        """
        Setup calendar

        :return: QWidget
        """
        self.init()
        body = self.window.core.tabs.from_widget(self.setup_calendar())
        body.append(self.window.ui.calendar['note'])
        body.append(self.window.ui.calendar['select'])
        return body

    def _on_filter_id_clicked(self, id_: int) -> None:
        key = "all" if id_ == 0 else ("pinned" if id_ == 1 else "indexed")
        self.window.controller.ctx.common.toggle_display_filter(key)

    def _on_counters_all_toggled(self, checked: bool) -> None:
        self.window.controller.calendar.note.toggle_counters_all(checked)

    def setup_filters(self) -> QWidget:
        """
        Setup calendar filters

        :return: QWidget
        """
        ui = self.window.ui
        nodes = ui.nodes

        label_existing = nodes.get('filter.ctx.label')
        if label_existing is None:
            layout = QHBoxLayout()
            widget = QWidget()
            rows = QVBoxLayout()
            widget.setLayout(rows)

            label = QLabel(trans("filter.ctx.label"), widget)

            radio_all = QRadioButton(trans("filter.ctx.radio.all"), widget)
            radio_pinned = QRadioButton(trans("filter.ctx.radio.pinned"), widget)
            radio_indexed = QRadioButton(trans("filter.ctx.radio.indexed"), widget)

            counters_all = QCheckBox(trans("filter.ctx.counters.all"), widget)

            layout.addWidget(label)
            layout.addWidget(radio_all)
            layout.addWidget(radio_pinned)
            layout.addWidget(radio_indexed)
            layout.addWidget(counters_all)
            layout.addStretch()

            nodes['filter.ctx.labels'] = ColorCheckbox(self.window)

            rows.addLayout(layout)
            rows.addWidget(nodes['filter.ctx.labels'])

            group = QButtonGroup(widget)
            group.setExclusive(True)
            group.addButton(radio_all, 0)
            group.addButton(radio_pinned, 1)
            group.addButton(radio_indexed, 2)
            group.idClicked.connect(self._on_filter_id_clicked)

            counters_all.toggled.connect(self._on_counters_all_toggled)

            nodes['filter.ctx.label'] = label
            nodes['filter.ctx.radio.all'] = radio_all
            nodes['filter.ctx.radio.pinned'] = radio_pinned
            nodes['filter.ctx.radio.indexed'] = radio_indexed
            nodes['filter.ctx.counters.all'] = counters_all
        else:
            widget = nodes['filter.ctx.label'].parentWidget()
            nodes['filter.ctx.label'].setText(trans("filter.ctx.label"))
            nodes['filter.ctx.radio.all'].setText(trans("filter.ctx.radio.all"))
            nodes['filter.ctx.radio.pinned'].setText(trans("filter.ctx.radio.pinned"))
            nodes['filter.ctx.radio.indexed'].setText(trans("filter.ctx.radio.indexed"))
            nodes['filter.ctx.counters.all'].setText(trans("filter.ctx.counters.all"))

        desired = bool(self.window.core.config.get("ctx.counters.all"))
        if nodes['filter.ctx.counters.all'].isChecked() != desired:
            nodes['filter.ctx.counters.all'].setChecked(desired)

        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return widget

    def setup_calendar(self) -> QWidget:
        """
        Setup calendar

        :return: QSplitter
        """
        ui = self.window.ui
        nodes = ui.nodes
        calendar = ui.calendar

        select_layout = QVBoxLayout()
        select_layout.addWidget(calendar['select'])
        select_layout.setContentsMargins(5, 0, 5, 0)

        tip = nodes.get('tip.output.tab.calendar')
        if tip is None:
            tip = HelpLabel(trans('tip.output.tab.calendar'), self.window)
            nodes['tip.output.tab.calendar'] = tip
        else:
            tip.setText(trans('tip.output.tab.calendar'))

        note_label = calendar.get('note.label')
        if note_label is None:
            note_label = QLabel(trans('calendar.note.label'))
            calendar['note.label'] = note_label
        else:
            note_label.setText(trans('calendar.note.label'))

        layout = QVBoxLayout()
        layout.addWidget(note_label)
        layout.addWidget(calendar['note'])
        layout.addWidget(tip)
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)

        filters = self.setup_filters()
        select_layout.addWidget(filters)

        select_widget = QWidget()
        select_widget.setLayout(select_layout)

        ui.splitters['calendar'] = QSplitter(Qt.Horizontal)
        ui.splitters['calendar'].addWidget(select_widget)
        ui.splitters['calendar'].addWidget(widget)
        ui.splitters['calendar'].setStretchFactor(0, 6)
        ui.splitters['calendar'].setStretchFactor(1, 4)

        ui.splitters['calendar'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        filters.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        return self.window.core.tabs.from_widget(ui.splitters['calendar'])