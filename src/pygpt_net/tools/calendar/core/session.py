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
"""Selection and navigation for one independent calendar frontend."""
from .editor import NoteEditor
from .counters import Counters

class Session:
    def __init__(self, tool):
        self.tool = tool
        self.window = tool.window
        self.widgets = {}
        self.note = NoteEditor(self)
        self.counters = Counters(self)
        self.selected_year = self.selected_month = self.selected_day = None
        self.widget = None
        self.closed = False

    def setup(self):
        """Setup calendar"""
        self.load()
        self.update()  # update counters and load notes for current month
        self.set_current()  # set to current note at start


    def is_loaded(self) -> bool:
        """
        Check if calendar is loaded

        :return: True if calendar is loaded
        """
        return not self.closed and 'select' in self.widgets


    def update(self, all: bool = True):
        """
        Update counters

        :param all: reload all notes
        """
        if not self.is_loaded():
            return
        year = self.widgets['select'].currentYear
        month = self.widgets['select'].currentMonth
        self.on_page_changed(year, month, all=all)  # load notes for current month


    def update_ctx_counters(self):
        """Update context counters only"""
        year = self.widgets['select'].currentYear
        month = self.widgets['select'].currentMonth
        self.counters.refresh_ctx(year, month)


    def set_current(self):
        """Set to current selected date"""
        date = self.widgets['select'].selectedDate()
        year = self.selected_year if self.selected_year is not None else date.year()
        month = self.selected_month if self.selected_month is not None else date.month()
        day = self.selected_day if self.selected_day is not None else date.day()

        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)

        self.selected_year = year
        self.selected_month = month
        self.selected_day = day


    def load(self):
        """Load notes from current year and month from database"""
        year = self.widgets['select'].currentYear
        month = self.widgets['select'].currentMonth
        self.tool.storage.load_by_month(year, month)


    def on_page_changed(
            self,
            year: int,
            month: int,
            all: bool = True
    ):
        """
        On calendar page changed

        :param year: year
        :param month: month
        :param all: reload all notes
        """
        if all:
            self.load()  # reload notes for current year and month
        self.counters.refresh_ctx(year, month)
        self.counters.refresh_num(year, month)


    def on_day_select(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        On day select

        :param year: year
        :param month: month
        :param day: day
        """
        self.selected_year = year
        self.selected_month = month
        self.selected_day = day
        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)


    def toggle_note_popup(
            self,
            year: int,
            month: int,
            day: int,
            anchor_rect=None
    ):
        """Open, switch or close the floating day-note editor."""
        popup = self.widgets.get('note.popup')
        if popup is None:
            return

        if popup.isVisible() and popup.is_date(year, month, day):
            # Keep the editor open when the same day is selected again.
            # The popup is closed explicitly with its close button only.
            popup.raise_()
            popup.activateWindow()
            if popup.editor is not None:
                popup.editor.setFocus()
            return

        self.selected_year = year
        self.selected_month = month
        self.selected_day = day

        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)
        popup.set_date(year, month, day)

        if anchor_rect is None:
            select = self.widgets.get('select')
            if select is not None:
                anchor_rect = select.get_cell_global_rect(year, month, day)

        popup.show_for(anchor_rect)


    def close_note_popup(self):
        """Close the floating day-note editor."""
        if self.closed:
            return
        popup = self.widgets.get('note.popup')
        if popup is not None:
            popup.hide()


    def on_ctx_select(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        On ctx select

        :param year: year
        :param month: month
        :param day: day
        """
        search_string = '@date({:04d}-{:02d}-{:02d})'.format(year, month, day)
        toggle = self.window.ui.nodes.get('ctx.search.toggle')
        if toggle is not None:
            toggle.setChecked(True)
        self.window.controller.ctx.append_search_string(search_string)


    def close(self):
        if self.closed:
            return
        self.closed = True
        self.widget.stop()
        self.tool.unregister_surface(self)
        if self in self.tool.sessions:
            self.tool.sessions.remove(self)

