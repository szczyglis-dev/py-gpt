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
"""One responsive month grid and its floating day-note editor."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from pygpt_net.ui.widget.element.labels import HelpLabel
from .select import CalendarSelect
from .editor import CalendarNote
from .popup import CalendarNotePopup
from .host import CalendarSquareHost
from .filters import Filters


class CalendarWidget(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.window = session.window
        self.tab = None
        session.widget = self
        widgets = session.widgets
        widgets['select'] = CalendarSelect(session)
        widgets['select'].setMinimumSize(200, 200)
        widgets['note'] = CalendarNote(session)
        widgets['note.popup'] = CalendarNotePopup(self.window, widgets['note'], parent=self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(6)
        layout.addWidget(CalendarSquareHost(widgets['select']), 1)
        self.filters = Filters(session, self)
        self.filters.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.filters)
        self.help_label = HelpLabel('', self)
        session.tool.add_lang_mapping(self.help_label, 'tip.output.tab.calendar')
        self.help_label.setVisible(bool(self.window.core.config.get('layout.tooltips', True)))
        layout.addWidget(self.help_label)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        session.setup()

    def set_tab(self, tab):
        self.tab = tab
        self.session.widgets['select'].set_tab(tab)
        self.session.widgets['note'].set_tab(tab)

    def stop(self):
        self.filters.clock.timer.stop()
        popup = self.session.widgets['note.popup']
        popup.hide()
        popup.deleteLater()
        editor = self.session.widgets['note']
        editor.finder.timer.stop()
        editor.finder.timer.timeout.disconnect()
        editor.finder.textarea = None
        self.window.controller.finder.unset(editor.finder)
        editor.finder.disconnect()
        editor.tab = None
        self.session.widgets['select'].tab = None

    def on_delete(self):
        self.session.close()

    def hideEvent(self, event):
        self.session.close_note_popup()
        super().hideEvent(event)
