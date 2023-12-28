#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.27 21:00:00                  #
# ================================================== #

import time

from sqlalchemy import text

from pygpt_net.item.notepad import NotepadItem


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

    def get_all(self):
        """
        Return dict with NotepadItem objects, indexed by ID

        :return: dict of NotepadItem objects
        :rtype: dict
        """
        stmt = text("""
            SELECT * FROM notepad
        """)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                notepad = NotepadItem()
                self.unpack(notepad, row._asdict())
                items[notepad.idx] = notepad  # by idx, not id
        return items

    def get_by_idx(self, idx):
        """
        Return NotepadItem by IDx

        :param idx: notepad item IDx
        :return: NotepadItem
        :rtype: NotepadItem
        """
        stmt = text("""
            SELECT * FROM notepad WHERE idx = :idx LIMIT 1
        """).bindparams(idx=idx)
        notepad = NotepadItem()
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                self.unpack(notepad, row._asdict())
        return notepad

    def truncate_all(self):
        """
        Truncate all notepad items

        :return: true if truncated
        :rtype: bool
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM notepad"))
        return True

    def delete_by_idx(self, idx):
        """
        Delete notepad item by IDx

        :param idx: notepad item IDx
        :return: true if deleted
        :rtype: bool
        """
        stmt = text("""
            DELETE FROM notepad WHERE idx = :idx
        """).bindparams(idx=idx)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def save(self, notepad):
        """
        Insert or update notepad item

        :param notepad: NotepadItem object
        """
        idx = int(notepad.idx or 0)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            ts = int(time.time())
            sel_stmt = text("SELECT 1 FROM notepad WHERE idx = :idx").bindparams(idx=idx)
            result = conn.execute(sel_stmt).fetchone()
            if result:
                stmt = text("""
                            UPDATE notepad
                            SET
                                idx = :idx,
                                title = :title,
                                content = :content,
                                updated_ts = :updated_ts
                            WHERE id = :id
                        """).bindparams(
                    id=notepad.id,
                    idx=int(notepad.idx or 0),
                    title=notepad.title,
                    content=notepad.content,
                    updated_ts=ts
                )
            else:
                stmt = text("""
                            INSERT INTO notepad 
                            (
                                idx,
                                uuid,
                                title, 
                                content, 
                                created_ts, 
                                updated_ts,
                                is_deleted
                            )
                            VALUES
                            (
                                :idx,
                                :uuid,
                                :title,
                                :content,
                                :created_ts,
                                :updated_ts,
                                :is_deleted
                            )
                        """).bindparams(
                    idx=notepad.idx,
                    uuid=notepad.uuid,
                    title=notepad.title,
                    content=notepad.content,
                    created_ts=ts,
                    updated_ts=ts,
                    is_deleted=int(notepad.deleted)
                )
            conn.execute(stmt)

    def insert(self, notepad):
        """
        Insert notepad item

        :param notepad: NotepadItem object
        :return: notepad item ID
        """
        db = self.window.core.db.get_db()
        ts = int(time.time())
        stmt = text("""
                INSERT INTO notepad 
                (
                    idx,
                    uuid,
                    title, 
                    content, 
                    created_ts, 
                    updated_ts,
                    is_deleted
                )
                VALUES
                (
                    :idx,
                    :uuid,
                    :title,
                    :content,
                    :created_ts,
                    :updated_ts,
                    :is_deleted
                )
            """).bindparams(
            idx=int(notepad.idx or 0),
            uuid=notepad.uuid,
            title=notepad.title,
            content=notepad.content,
            created_ts=ts,
            updated_ts=ts,
            is_deleted=int(notepad.deleted)
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            notepad.id = result.lastrowid
            return notepad.id

    def unpack(self, notepad, row):
        """
        Unpack notepad item from DB row

        :param notepad: Notepad item (NotepadItem)
        :param row: DB row
        :return: Notepad item
        :rtype: NotepadItem
        """
        notepad.id = int(row['id'])
        notepad.idx = int(row['idx'] or 0)
        notepad.uuid = row['uuid']
        notepad.created = int(row['created_ts'])
        notepad.updated = int(row['updated_ts'])
        notepad.title = row['title']
        notepad.content = row['content']
        notepad.deleted = bool(row['is_deleted'])
        return notepad
