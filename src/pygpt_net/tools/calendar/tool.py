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
"""Calendar tool lifecycle and frontend ownership."""
from PySide6.QtGui import QAction, QIcon
from pygpt_net.tools.base import BaseTool, ToolMenuAction
from pygpt_net.core.tabs.tab import Tab
from .core.storage import Storage
from .core.notes import Notes
from .core.session import Session
from .ui.widget import CalendarWidget
from .ui.dialog import CalendarDialog


class Calendar(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = 'calendar'
        self.allow_tab = True
        self.allow_dialog = True
        self.multi_tab = False
        self.multi_dialog = False
        self.on_menu_click = ToolMenuAction.ALWAYS_DIALOG
        self.dialog_id = 'calendar'
        self.tab_title = 'output.tab.calendar'
        self.tab_icon = ':/icons/calendar.svg'
        self.storage = None
        self.notes = Notes(self)
        self.sessions = []
        self.dialog = None

    def attach(self, window):
        super().attach(window)
        self.storage = Storage(window)

    def setup_menu(self):
        action = QAction(QIcon(self.tab_icon), '', self.window)
        self.add_lang_mapping(action, self.tab_title)
        action.triggered.connect(self.on_menu_action)
        return {self.id: action}

    def new_frontend(self, parent=None):
        session = Session(self)
        widget = CalendarWidget(session, parent)
        self.sessions.append(session)
        return widget

    def as_tab(self, tab):
        widget = self.new_frontend()
        widget.set_tab(tab)
        self.register_surface(widget.session, widget, tab=tab)
        return widget

    def open(self):
        if self.dialog is None:
            self.dialog = CalendarDialog(self)
            self.window.ui.dialog[self.dialog_id] = self.dialog
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
        self.mark_surface_used(self.dialog.widget.session)
        return self.dialog

    def create_surface(self):
        return self.open().widget.session

    def is_active(self):
        tab = self.window.controller.tabs.get_current_tab()
        return any(session.widgets['note.popup'].isActiveWindow() for session in self.sessions) or (
            self.dialog is not None and self.dialog.isActiveWindow()) or (
            tab is not None and tab.type == Tab.TAB_TOOL and tab.tool_id == self.id)

    def refresh(self):
        for session in tuple(self.sessions):
            if not session.closed:
                session.update(all=False)
                session.widget.filters.restore()

    def refresh_notes(self, origin=None):
        for session in tuple(self.sessions):
            if session.closed:
                continue
            select = session.widgets['select']
            session.counters.refresh_num(select.currentYear, select.currentMonth)
            if session is not origin:
                session.set_current()

    def on_selected(self, tab):
        self.refresh()

    def on_reload(self):
        self.storage.reset()
        for session in tuple(self.sessions):
            session.setup()
            session.widget.filters.restore()

    def on_exit(self):
        self.storage.save_all()

    def setup_theme(self):
        for session in tuple(self.sessions):
            editor = session.widgets['note']
            editor.setStyleSheet(self.window.controller.theme.style('font.chat.output'))
            editor.value = self.window.core.config.get('font_size')
            session.widget.help_label.setVisible(bool(self.window.core.config.get('layout.tooltips', True)))

    def apply_lang_mappings(self):
        super().apply_lang_mappings()
        for session in tuple(self.sessions):
            session.note.update_current()
            session.widget.filters.clock._update_clock()
