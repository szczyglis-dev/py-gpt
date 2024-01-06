#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 04:00:00                  #
# ================================================== #

import time

from sqlalchemy import text

from pygpt_net.item.calendar_note import CalendarNoteItem


class Storage:
    def __init__(self, window=None):
        """
        Initialize storage instance

        :param window: Window instance
        """
        self.window = window

    def attach(self, window):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window

    def get_all(self) -> dict:
        """
        Return dict with CalendarNoteItem objects, indexed by YYYY-MM-DD

        :return: dict of CalendarNoteItem objects
        """
        stmt = text("""
            SELECT * FROM calendar_note
        """)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                note = CalendarNoteItem()
                self.unpack(note, row._asdict())
                dt = note.get_dt()
                items[dt] = note
        return items

    def get_by_month(self, year: int, month: int) -> dict:
        """
        Return dict with CalendarNoteItem objects, indexed by YYYY-MM-DD

        :return: dict of CalendarNoteItem objects
        """
        stmt = text("""
            SELECT * FROM calendar_note WHERE year = :year AND month = :month
        """).bindparams(year=year, month=month)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                note = CalendarNoteItem()
                self.unpack(note, row._asdict())
                dt = note.get_dt()
                items[dt] = note
        return items

    def get_by_date(self, year: int, month: int, day: int) -> CalendarNoteItem:
        """
        Return CalendarNoteItem by date

        :param year: year
        :param month: month
        :param day: day
        :return: CalendarNoteItem
        """
        stmt = text("""
            SELECT * FROM calendar_note WHERE year = :year AND month = :month AND day = :day LIMIT 1
        """).bindparams(year=year, month=month, day=day)
        notepad = CalendarNoteItem()
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                self.unpack(notepad, row._asdict())
        return notepad

    def get_notes_existence_by_day(self, year, month):
        """Return a dict of days with the count of notes for the given year and month."""
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(text("""
                    SELECT
                        year || '-' || printf('%02d', month) || '-' || printf('%02d', day) as day,
                        COUNT(id) as note_count
                    FROM calendar_note
                    WHERE year = :year
                      AND month = :month
                      AND is_deleted = 0
                      AND content != ''
                    GROUP BY day
                """), {'year': year, 'month': month})

            days_with_notes = {row._mapping['day']: row._mapping['note_count'] for row in result if
                               row._mapping['note_count'] > 0}
            return days_with_notes

    def truncate_all(self) -> bool:
        """
        Truncate all notes from database

        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM calendar_note"))
        return True

    def delete_by_date(self, year: int, month: int, day: int) -> bool:
        """
        Delete note item by date

        :param year: year
        :param month: month
        :param day: day
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM calendar_note WHERE year = :year AND month = :month AND day = :day
        """).bindparams(year=year, month=month, day=day)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def save(self, note: CalendarNoteItem):
        """
        Insert or update note item

        :param note: CalendarNoteItem object
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            ts = int(time.time())
            sel_stmt = text("SELECT 1 FROM calendar_note WHERE year = :year AND month = :month AND day = :day LIMIT 1").bindparams(
                year=note.year,
                month=note.month,
                day=note.day
            )
            result = conn.execute(sel_stmt).fetchone()
            if result:
                stmt = text("""
                            UPDATE calendar_note
                            SET
                                title = :title,
                                status = :status,
                                content = :content,
                                is_important = :is_important,
                                updated_ts = :updated_ts
                            WHERE year = :year AND month = :month AND day = :day
                        """).bindparams(
                    title=note.title,
                    year=int(note.year),
                    month=int(note.month),
                    day=int(note.day),
                    status=note.status,
                    content=note.content,
                    is_important=int(note.important),
                    updated_ts=ts
                )
            else:
                stmt = text("""
                            INSERT INTO calendar_note 
                            (
                                idx,
                                uuid,
                                status,
                                year,
                                month,
                                day,
                                title, 
                                content, 
                                created_ts, 
                                updated_ts,
                                is_important,
                                is_deleted
                            )
                            VALUES
                            (
                                :idx,
                                :uuid,
                                :status,
                                :year,
                                :month,
                                :day,
                                :title,
                                :content,
                                :created_ts,
                                :updated_ts,
                                :is_important,
                                :is_deleted
                            )
                        """).bindparams(
                    idx=note.idx,
                    uuid=note.uuid,
                    status=int(note.status),
                    year=int(note.year),
                    month=int(note.month),
                    day=int(note.day),
                    title=note.title,
                    content=note.content,
                    created_ts=ts,
                    updated_ts=ts,
                    is_important=int(note.important),
                    is_deleted=int(note.deleted)
                )
            conn.execute(stmt)

    def insert(self, note: CalendarNoteItem) -> int:
        """
        Insert note item

        :param note: CalendarNoteItem object
        :return: note item ID
        """
        db = self.window.core.db.get_db()
        ts = int(time.time())
        stmt = text("""
                INSERT INTO calendar_note 
                (
                    idx,
                    uuid,
                    status,
                    year,
                    month,
                    day,
                    title, 
                    content, 
                    created_ts, 
                    updated_ts,
                    is_important,
                    is_deleted
                )
                VALUES
                (
                    :idx,
                    :uuid,
                    :status,
                    :year,
                    :month,
                    :day,
                    :title,
                    :content,
                    :created_ts,
                    :updated_ts,
                    :is_important,
                    :is_deleted
                )
            """).bindparams(
            idx=int(note.idx or 0),
            uuid=note.uuid,
            status=int(note.status or 0),
            year=int(note.year or 0),
            month=int(note.month or 0),
            day=int(note.day or 0),
            title=note.title,
            content=note.content,
            created_ts=ts,
            updated_ts=ts,
            is_important=int(note.important),
            is_deleted=int(note.deleted)
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            note.id = result.lastrowid
            return note.id

    def unpack(self, note: CalendarNoteItem, row: dict) -> CalendarNoteItem:
        """
        Unpack note item from DB row

        :param note: CalendarNoteItem item
        :param row: DB row
        :return: Notepad item
        """
        note.id = int(row['id'])
        note.idx = int(row['idx'] or 0)
        note.uuid = row['uuid']
        note.status = int(row['status'] or 0)
        note.year = int(row['year'] or 0)
        note.month = int(row['month'] or 0)
        note.day = int(row['day'] or 0)
        note.created = int(row['created_ts'])
        note.updated = int(row['updated_ts'])
        note.title = row['title']
        note.content = row['content']
        note.important = bool(row['is_important'])
        note.deleted = bool(row['is_deleted'])
        return note
