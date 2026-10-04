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
"""Day-note editing bound to one selected date and frontend."""
from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QTextCursor
from pygpt_net.item.calendar_note import CalendarNoteItem

class NoteEditor:
    def __init__(self, session):
        self.session = session
        self.window = session.window

    def get_content(
            self,
            year: int,
            month: int,
            day: int
    ) -> str:
        """Return note content for a date without creating a new note."""
        note = self.session.tool.storage.get_or_load(year, month, day)
        if note is None or note.content is None:
            return ""
        return str(note.content)


    def get_preview(
            self,
            year: int,
            month: int,
            day: int,
            limit: int = 20
    ) -> str:
        """Return a compact single-line day-note preview."""
        content = " ".join(self.get_content(year, month, day).split())
        if not content:
            return ""
        if limit > 0 and len(content) > limit:
            return content[:limit] + "..."
        return content


    def update(self):
        """Update on content change"""
        if self.session.closed:
            return
        ctrl_cal = self.session
        year = ctrl_cal.selected_year
        month = ctrl_cal.selected_month
        day = ctrl_cal.selected_day

        if year is None or month is None or day is None:
            return

        ui_note = self.session.widgets['note']
        content = ui_note.toPlainText()
        cal = self.session.tool.storage
        note = cal.get_or_load(year, month, day)

        changed = False
        if note is None:
            if content.strip():
                note = self.create(year, month, day)
                note.content = content
                cal.add(note)
                changed = True
        else:
            if note.content != content:
                note.content = content
                cal.update(note)
                changed = True

        if changed:
            self.session.tool.refresh_notes(origin=self.session)


    def update_content(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        Update content

        :param year: year
        :param month: month
        :param day: day
        """
        ui_note = self.session.widgets['note']
        note = self.session.tool.storage.get_or_load(year, month, day)
        new_text = "" if note is None or note.content is None else str(note.content)
        if ui_note.toPlainText() != new_text:
            blocker = QSignalBlocker(ui_note)
            ui_note.setPlainText(new_text)
            del blocker
        ui_note.on_update()


    def update_label(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        Update label

        :param year: year
        :param month: month
        :param day: day
        """
        popup = self.session.widgets.get('note.popup')
        if popup is not None:
            popup.refresh_translation()


    def update_current(self):
        """Update label to current selected date"""
        if self.session.selected_year is not None:
            self.update_label(self.session.selected_year, self.session.selected_month, self.session.selected_day)


    def update_status(
            self,
            status: str,
            year: int,
            month: int,
            day: int
    ):
        """
        Update status label

        :param status: status
        :param year: year
        :param month: month
        :param day: day
        """
        cal = self.session.tool.storage
        note = cal.get_or_load(year, month, day)
        changed = False
        if note is None:
            note = self.create(year, month, day)
            note.status = status
            cal.add(note)
            changed = True
        else:
            if note.status != status:
                note.status = status
                cal.update(note)
                changed = True

        if changed:
            self.session.tool.refresh_notes(origin=self.session)


    def create(
            self,
            year: int,
            month: int,
            day: int
    ) -> CalendarNoteItem:
        """
        Create empty note

        :param year: year
        :param month: month
        :param day: day
        :return: note instance
        """
        note = self.session.tool.storage.build()
        note.year = year
        note.month = month
        note.day = day
        return note


    def append_text(self, text: str):
        """
        Append text to note

        :param text: text to append
        """
        editor = self.session.widgets['note']
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        if not editor.document().isEmpty():
            cursor.insertText("\n\n")
        cursor.insertText(text.strip())
        editor.setTextCursor(cursor)
        self.update()


    def clear_note(self):
        """Clear note"""
        self.session.widgets['note'].clear()
        self.update()
        self.session.widgets['note'].on_update()


    def get_note_text(self) -> str:
        """
        Get notepad text

        :return: notepad text
        """
        return self.session.widgets['note'].toPlainText()

