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
"""Conversation filter controls owned by one calendar frontend."""
from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QCheckBox, QButtonGroup
from .labels import ColorCheckbox
from .clock import Clock


class Filters(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.window = session.window
        rows = QVBoxLayout(self)
        rows.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.label = QLabel(self)
        self.radios = {key: QRadioButton(self) for key in ('all', 'pinned', 'indexed')}
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        row.addWidget(self.label)
        for index, (key, button) in enumerate(self.radios.items()):
            self.group.addButton(button, index)
            row.addWidget(button)
        self.counters = QCheckBox(self)
        row.addWidget(self.counters)
        row.addStretch()
        self.labels = ColorCheckbox(self.window)
        self.clock_label = QLabel(self)
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        second = QHBoxLayout()
        second.addWidget(self.labels, 1)
        second.addWidget(self.clock_label, 0)
        rows.addLayout(row)
        rows.addLayout(second)
        self.clock = Clock(self.window, self.clock_label)
        self.group.idClicked.connect(lambda index: self.window.controller.ctx.common.toggle_display_filter(
            ('all', 'pinned', 'indexed')[index]))
        self.counters.toggled.connect(session.counters.toggle_counters_all)
        tool = session.tool
        tool.add_lang_mapping(self.label, 'filter.ctx.label')
        for key, button in self.radios.items():
            tool.add_lang_mapping(button, 'filter.ctx.radio.' + key)
        tool.add_lang_mapping(self.counters, 'filter.ctx.counters.all')
        tool.add_lang_mapping(self.labels.label, 'filter.ctx.label.colors')
        self.restore()

    def restore(self):
        config = self.window.core.config
        key = config.get('ctx.records.filter', 'all')
        button = self.radios.get(key, self.radios['all'])
        button.setChecked(True)
        blocker = QSignalBlocker(self.counters)
        self.counters.setChecked(bool(config.get('ctx.counters.all', True)))
        del blocker
        self.labels.restore(config.get('ctx.records.filter.labels') or [])
        self.clock._update_clock()
