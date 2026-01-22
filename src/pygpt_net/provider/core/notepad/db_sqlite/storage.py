#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 16:00:00                  #
# ================================================== #
import json
import time
from typing import Dict, Any

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

    def get_all(self) -> Dict[int, NotepadItem]:
        """
        Return dict with NotepadItem objects, indexed by ID

        :return: dict of NotepadItem objects
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

    def get_by_idx(self, idx: int) -> NotepadItem:
        """
        Return NotepadItem by IDx

        :param idx: notepad item IDx
        :return: NotepadItem
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

    def truncate_all(self) -> bool:
        """
        Truncate all notepad items

        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM notepad"))
        return True

    def delete_by_idx(self, idx: int) -> bool:
        """
        Delete notepad item by IDx

        :param idx: notepad item IDx
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM notepad WHERE idx = :idx
        """).bindparams(idx=idx)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def save(self, notepad: NotepadItem):
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
                                title = :title,
                                content = :content,
                                is_initialized = :is_initialized,
                                updated_ts = :updated_ts,
                                highlights_json = :highlights_json,
                                scroll_pos = :scroll_pos
                            WHERE idx = :idx
                        """).bindparams(
                    idx=int(notepad.idx or 0),
                    title=notepad.title,
                    content=notepad.content,
                    is_initialized=int(notepad.initialized),
                    updated_ts=ts,
                    highlights_json=self.pack_item_value(notepad.highlights),
                    scroll_pos=int(notepad.scroll_pos)
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
                                is_deleted,
                                is_initialized,
                                highlights_json,
                                scroll_pos
                            )
                            VALUES
                            (
                                :idx,
                                :uuid,
                                :title,
                                :content,
                                :created_ts,
                                :updated_ts,
                                :is_deleted,
                                :is_initialized,
                                :highlights_json,
                                :scroll_pos
                            )
                        """).bindparams(
                    idx=notepad.idx,
                    uuid=notepad.uuid,
                    title=notepad.title,
                    content=notepad.content,
                    created_ts=ts,
                    updated_ts=ts,
                    is_deleted=int(notepad.deleted),
                    is_initialized=int(notepad.initialized),
                    highlights_json=self.pack_item_value(notepad.highlights),
                    scroll_pos=int(notepad.scroll_pos)
                )
            conn.execute(stmt)

    def insert(self, notepad: NotepadItem) -> int:
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
                    is_deleted,
                    is_initialized,
                    highlights_json,
                    scroll_pos
                )
                VALUES
                (
                    :idx,
                    :uuid,
                    :title,
                    :content,
                    :created_ts,
                    :updated_ts,
                    :is_deleted,
                    :is_initialized,
                    :highlights_json,
                    :scroll_pos
                )
            """).bindparams(
            idx=int(notepad.idx or 0),
            uuid=notepad.uuid,
            title=notepad.title,
            content=notepad.content,
            created_ts=ts,
            updated_ts=ts,
            is_deleted=int(notepad.deleted),
            is_initialized=int(notepad.initialized),
            highlights_json=self.pack_item_value(notepad.highlights),
            scroll_pos=int(notepad.scroll_pos)
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            notepad.id = result.lastrowid
            return notepad.id

    def unpack(self, notepad: NotepadItem, row: Dict[str, Any]) -> NotepadItem:
        """
        Unpack notepad item from DB row

        :param notepad: Notepad item (NotepadItem)
        :param row: DB row
        :return: Notepad item
        """
        notepad.id = int(row['id'])
        notepad.idx = int(row['idx'] or 0)
        notepad.uuid = row['uuid']
        notepad.created = int(row['created_ts'])
        notepad.updated = int(row['updated_ts'])
        notepad.title = row['title']
        notepad.content = row['content']
        notepad.deleted = bool(row['is_deleted'])
        notepad.initialized = bool(row['is_initialized'])
        notepad.highlights = self.unpack_item_value(row['highlights_json'])
        notepad.scroll_pos = int(row.get('scroll_pos', -1))
        return notepad

    def pack_item_value(self, value: Any) -> str:
        """
        Pack item value to JSON

        :param value: Value to pack
        :return: JSON string or value itself
        """
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return value

    def unpack_item_value(self, value: Any) -> Any:
        """
        Unpack item value from JSON

        :param value: Value to unpack
        :return: Unpacked value
        """
        if value is None:
            return []
        try:
            return json.loads(value)
        except:
            return value
