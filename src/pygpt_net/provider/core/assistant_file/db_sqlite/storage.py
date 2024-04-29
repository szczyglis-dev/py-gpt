#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 16:00:00                  #
# ================================================== #

import time

from sqlalchemy import text

from pygpt_net.item.assistant import AssistantFileItem
from .utils import pack_item_value, unpack_file


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
        Return dict with AssistantFileItem objects, indexed by ID

        :return: dict of AssistantFileItem objects
        """
        stmt = text("""
            SELECT * FROM remote_file
        """)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                file = AssistantFileItem()
                unpack_file(file, row._asdict())
                items[file.id] = file  # index by ID
        return items

    def get_by_id(self, id: int) -> AssistantFileItem:
        """
        Return AssistantFileItem by ID

        :param id: file item ID
        :return: AssistantFileItem
        """
        stmt = text("""
            SELECT * FROM remote_file WHERE id = :id LIMIT 1
        """).bindparams(idx=id)
        file = AssistantFileItem()
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                unpack_file(file, row._asdict())
        return file

    def get_by_store_or_thread(self, store_id: str, thread_id: str) -> dict:
        """
        Return dict with AssistantFileItem objects, indexed by ID

        :return: dict of AssistantFileItem objects
        """
        if (store_id is None or store_id == "") and (thread_id is None or thread_id == ""):
            return {}

        if store_id is not None and store_id != "" and thread_id is not None and thread_id != "":
            stmt = text("""
                SELECT * FROM remote_file WHERE thread_id = :thread OR store_id = :store
            """).bindparams(
                thread=thread_id,
                store=store_id
            )
        elif store_id is not None and store_id != "":
            stmt = text("""
                SELECT * FROM remote_file WHERE store_id = :store
            """).bindparams(
                store=store_id
            )
        elif thread_id is not None and thread_id != "":
            stmt = text("""
                SELECT * FROM remote_file WHERE thread_id = :thread
            """).bindparams(
                thread=thread_id
            )
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                file = AssistantFileItem()
                unpack_file(file, row._asdict())
                items[file.id] = file  # index by record ID
        return items

    def count_by_store_or_thread(self, store_id: str, thread_id: str) -> int:
        """
        Count AssistantFileItem objects

        :return: num of files
        """
        if (store_id is None or store_id == "") and (thread_id is None or thread_id == ""):
            return 0

        if store_id is not None and store_id != "" and thread_id is not None and thread_id != "":
            stmt = text("""
                SELECT COUNT(*) FROM remote_file WHERE thread_id = :thread OR store_id = :store
            """).bindparams(
                thread=thread_id,
                store=store_id
            )
        elif store_id is not None and store_id != "":
            stmt = text("""
                SELECT COUNT(*) FROM remote_file WHERE store_id = :store
            """).bindparams(
                store=store_id
            )
        elif thread_id is not None and thread_id != "":
            stmt = text("""
                SELECT COUNT(*) FROM remote_file WHERE thread_id = :thread
            """).bindparams(
                thread=thread_id
            )
        num = 0
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                num = row[0]
        return num

    def get_all_by_file_id(self, file_id: str) -> dict:
        """
        Get all files by file ID

        :param file_id: file ID
        :return: files dict
        """
        stmt = text("""
            SELECT * FROM remote_file WHERE file_id = :file_id
        """).bindparams(file_id=file_id)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                file = AssistantFileItem()
                unpack_file(file, row._asdict())
                items[file.id] = file
        return items

    def truncate_all(self) -> bool:
        """
        Truncate all files items

        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM remote_file"))
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name='remote_file'"))
        return True

    def truncate_by_store(self, store_id: str) -> bool:
        """
        Truncate all files items by store ID

        :param store_id: store ID
        :return: True if truncated
        """
        stmt = text("""
            DELETE FROM remote_file WHERE store_id = :store_id
        """).bindparams(store_id=store_id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def delete_by_id(self, id: int) -> bool:
        """
        Delete file item by record ID

        :param id: record ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM remote_file WHERE id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def delete_by_file_id(self, file_id: str) -> bool:
        """
        Delete file item by record ID

        :param file_id: file ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM remote_file WHERE file_id = :id
        """).bindparams(id=file_id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def clear_store_from_files(self, store_id: str) -> bool:
        """
        Clear store from files

        :param store_id: store ID
        :return: True if cleared
        """
        stmt = text("""
            DELETE FROM remote_file WHERE store_id = :store_id
        """).bindparams(store_id=store_id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def clear_all_stores_from_files(self) -> bool:
        """
        Clear all stores from files

        :return: True if cleared
        """
        stmt = text("""
            DELETE FROM remote_file WHERE store_id IS NOT NULL
        """)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def rename_file(self, record_id: int, name: str) -> bool:
        """
        Rename file

        :param record_id: record ID
        :param name: new name
        :return: True if renamed
        """
        stmt = text("""
            UPDATE remote_file SET name = :name WHERE id = :id
        """).bindparams(
            id=record_id,
            name=name
        )
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def save(self, file: AssistantFileItem):
        """
        Insert or update file item

        :param file: AssistantFileItem object
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            ts = int(time.time())
            stmt = text("""
                UPDATE remote_file
                SET
                    name = :name,
                    path = :path,
                    file_id = :file_id,
                    store_id = :store_id,
                    thread_id = :thread_id,
                    updated_ts = :updated_ts
                WHERE id = :id
                """).bindparams(
                id=file.record_id,
                name=file.name,
                path=file.path,
                file_id=file.file_id,
                store_id=file.store_id,
                thread_id=file.thread_id,
                updated_ts=int(ts or 0)
            )
            conn.execute(stmt)

    def insert(self, file: AssistantFileItem) -> int:
        """
        Insert file item

        :param file: AssistantFileItem object
        :return: file item ID
        """
        db = self.window.core.db.get_db()
        ts = int(time.time())
        stmt = text("""
                INSERT INTO remote_file
                (
                    uuid,
                    name,
                    path,
                    size,
                    file_id,
                    store_id,
                    thread_id,
                    created_ts,
                    updated_ts
                )
                VALUES
                (
                    :uuid,
                    :name,
                    :path,
                    :size,
                    :file_id,
                    :store_id,
                    :thread_id,
                    :created_ts,
                    :updated_ts
                )
            """).bindparams(
            uuid=file.uuid,
            name=file.name,
            path=file.path,
            size=int(file.size or 0),
            file_id=file.file_id,
            store_id=file.store_id,
            thread_id=file.thread_id,
            created_ts=int(ts or 0),
            updated_ts=int(ts or 0)
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            file.record_id = result.lastrowid
            return file.record_id
