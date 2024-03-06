#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
# ================================================== #

import uuid
import time

from sqlalchemy import text

from pygpt_net.item.index import IndexItem
from .utils import unpack_file_item


class Storage:
    def __init__(self, window=None):
        """
        DB storage for index items

        :param window: Window instance
        """
        self.window = window

    def attach(self, window):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window

    def get_items(self, store_id: str) -> dict:
        """
        Return idx items by store ID

        :return: dict of indexes and files in index
        """
        stmt = text("""
            SELECT * FROM idx_file WHERE store = :store_id ORDER BY id ASC
        """).bindparams(store_id=store_id)
        db = self.window.core.db.get_db()
        items = {}
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                idx, data = unpack_file_item(row._asdict())
                if idx not in items:
                    items[idx] = {}
                file_id = data['name']  # use file name as ID
                items[idx][file_id] = data

        indexes = {}
        for idx, files in items.items():
            index = IndexItem()
            index.id = idx
            index.store = store_id
            index.items = files
            indexes[idx] = index

        return indexes

    def insert_file(self, store_id: str, idx: str, data: dict) -> int:
        """
        Insert file to index

        :param store_id: store ID
        :param idx: index
        :param data: dictionary with file data
        """
        id = None
        db = self.window.core.db.get_db()
        stmt = text("""
            INSERT INTO idx_file
            (
                uuid,
                doc_id,
                created_ts,
                updated_ts,
                name,
                path,
                store,
                idx
            )
            VALUES 
            (
                :uuid,
                :doc_id,
                :created_ts,
                :updated_ts,
                :name,
                :path,
                :store,
                :idx
            )
        """).bindparams(
            uuid=str(uuid.uuid4()),
            doc_id=data['id'],
            created_ts=int(data["indexed_ts"]),
            updated_ts=int(data["indexed_ts"]),
            name=data['name'],
            path=data['path'],
            store=store_id,
            idx=idx,
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            id = result.lastrowid

        return id

    def insert_ctx_meta(self, store_id: str, idx: str, meta_id: int, doc_id: str) -> int:
        """
        Insert ctx meta to index

        :param store_id: store ID
        :param idx: index
        :param meta_id: meta ID
        :param doc_id: document ID
        """
        id = None
        ts = int(time.time())
        db = self.window.core.db.get_db()
        stmt = text("""
            INSERT INTO idx_ctx
            (
                uuid,
                meta_id,
                doc_id,
                created_ts,
                updated_ts,
                store,
                idx
            )
            VALUES 
            (
                :uuid,
                :meta_id,
                :doc_id,
                :created_ts,
                :updated_ts,
                :store,
                :idx
            )
        """).bindparams(
            uuid=str(uuid.uuid4()),
            meta_id=meta_id,
            doc_id=doc_id,
            created_ts=ts,
            updated_ts=ts,
            store=store_id,
            idx=idx,
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            id = result.lastrowid

        return id

    def insert_external(self, store_id: str, idx: str, data: dict) -> int:
        """
        Insert external data to index

        :param store_id: store ID
        :param idx: index
        :param data: dictionary with external data
        """
        id = None
        db = self.window.core.db.get_db()
        stmt = text("""
            INSERT INTO idx_external
            (
                uuid,
                doc_id,
                created_ts,
                updated_ts,
                content,
                type,
                store,
                idx
            )
            VALUES 
            (
                :uuid,
                :doc_id,
                :created_ts,
                :updated_ts,
                :content,
                :type,
                :store,
                :idx
            )
        """).bindparams(
            uuid=str(uuid.uuid4()),
            doc_id=data['id'],
            created_ts=int(data["indexed_ts"]),
            updated_ts=int(data["indexed_ts"]),
            content=data['content'],
            type=data['type'],
            store=store_id,
            idx=idx,
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            id = result.lastrowid

        return id

    def is_meta_indexed(self, store_id: str, idx: str, meta_id: int) -> bool:
        """
        Check if context meta is indexed

        :param: store_id: store ID
        :param: idx: index
        :param: meta_id: context meta ID
        :return: True if indexed
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            SELECT COUNT(*) as count
            FROM idx_ctx
            WHERE store = :store_id
            AND idx = :idx
            AND meta_id = :meta_id
        """).bindparams(
            store_id=store_id,
            idx=idx,
            meta_id=meta_id,
        )
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            data = row._asdict()
            return int(data['count']) > 0

    def is_file_indexed(self, store_id: str, idx: str, file_id: str) -> bool:
        """
        Check if file is indexed

        :param: store_id: store ID
        :param: idx: index
        :param: file_id: file ID
        :return: True if indexed
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            SELECT COUNT(*) as count
            FROM idx_file
            WHERE store = :store_id
            AND idx = :idx
            AND name = :file_id
        """).bindparams(
            store_id=store_id,
            idx=idx,
            file_id=file_id,
        )
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            data = row._asdict()
            return int(data['count']) > 0

    def is_external_indexed(self, store_id: str, idx: str, content: str, type: str) -> bool:
        """
        Check if external is indexed

        :param: store_id: store ID
        :param: idx: index
        :param: content: content
        :param: type: type
        :return: True if indexed
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            SELECT COUNT(*) as count
            FROM idx_external
            WHERE store = :store_id
            AND idx = :idx
            AND content = :content
            AND type = :type
        """).bindparams(
            store_id=store_id,
            idx=idx,
            content=content,
            type=type,
        )
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            data = row._asdict()
            return int(data['count']) > 0

    def get_meta_doc_id(self, store_id: str, idx: str, meta_id: int) -> str:
        """
        Get indexed document id by meta id

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :return: document id
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            SELECT doc_id
            FROM idx_ctx
            WHERE store = :store_id
            AND idx = :idx
            AND meta_id = :meta_id
        """).bindparams(
            store_id=store_id,
            idx=idx,
            meta_id=meta_id,
        )
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            data = row._asdict()
            return data['doc_id']

    def get_file_doc_id(self, store_id: str, idx: str, file_id: str) -> str:
        """
        Get indexed document id by file id

        :param store_id: store id
        :param idx: index name
        :param file_id
        :return: document id
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            SELECT doc_id
            FROM idx_file
            WHERE store = :store_id
            AND idx = :idx
            AND name = :file_id
        """).bindparams(
            store_id=store_id,
            idx=idx,
            file_id=file_id,
        )
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            data = row._asdict()
            return data['doc_id']

    def get_external_doc_id(self, store_id: str, idx: str, content: str, type: str) -> str:
        """
        Get indexed document id by external

        :param store_id: store id
        :param idx: index name
        :param content: content
        :param type: type
        :return: document id
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            SELECT doc_id
            FROM idx_external
            WHERE store = :store_id
            AND idx = :idx
            AND content = :content
            AND type = :type
        """).bindparams(
            store_id=store_id,
            idx=idx,
            content=content,
            type=type,
        )
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            data = row._asdict()
            return data['doc_id']

    def update_file(self, id: int, doc_id: str, ts: int) -> bool:
        """
        Update timestamp of file in index

        :param id: db record ID
        :param doc_id: document ID
        :param ts: timestamp
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE idx_file
            SET 
            updated_ts = :updated_ts,
            doc_id = :doc_id
            WHERE id = :id
        """).bindparams(
            id=id,
            doc_id=doc_id,
            updated_ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def update_ctx_meta(self, meta_id: int, doc_id: str) -> bool:
        """
        Update timestamp of ctx meta in index

        :param meta_id: ctx meta ID
        :param doc_id: document ID
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE 
                idx_ctx
            SET 
                updated_ts = :updated_ts,
                doc_id = :doc_id
            WHERE meta_id = :id
        """).bindparams(
            id=meta_id,
            doc_id=doc_id,
            updated_ts=int(time.time()),
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def update_external(self, content: str, type: str, doc_id: str, ts: int) -> bool:
        """
        Update timestamp of external data in index

        :param content: content
        :param type: type
        :param doc_id: document ID
        :param ts: timestamp
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE idx_external
            SET 
            updated_ts = :updated_ts,
            doc_id = :doc_id
            WHERE 
            content = :content AND type = :type
        """).bindparams(
            content=content,
            type=type,
            doc_id=doc_id,
            updated_ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def remove_file(self, store_id: str, idx: str, doc_id: str):
        """
        Remove file from index

        :param store_id: store ID
        :param idx: index
        :param doc_id: document ID
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(
                text("DELETE FROM idx_file WHERE store = :store_id AND idx = :idx AND doc_id = :doc_id").bindparams(
                    store_id=store_id,
                    idx=idx,
                    doc_id=doc_id,
                ))

    def remove_ctx_meta(self, store_id: str, idx: str, meta_id: str):
        """
        Remove file from index

        :param store_id: store ID
        :param idx: index
        :param meta_id: ctx meta ID
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(
                text("DELETE FROM idx_ctx WHERE store = :store_id AND idx = :idx AND meta_id = :meta_id").bindparams(
                    store_id=store_id,
                    idx=idx,
                    meta_id=meta_id,
                ))

    def remove_external(self, store_id: str, idx: str, doc_id: str):
        """
        Remove file from index

        :param store_id: store ID
        :param idx: index
        :param doc_id: document ID
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(
                text("DELETE FROM idx_external WHERE store = :store_id AND idx = :idx AND doc_id = :doc_id").bindparams(
                    store_id=store_id,
                    idx=idx,
                    doc_id=doc_id,
                ))

    def truncate_all(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate all idx tables in database (all stores)

        :param store_id: store ID
        :param idx: index ID
        :return: True if truncated
        """
        self.truncate_files(store_id, idx)
        self.truncate_ctx(store_id, idx)
        self.truncate_external(store_id, idx)
        return True

    def truncate_files(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate files table in database

        :param store_id: store ID
        :param idx: index ID
        :return: True if truncated
        """
        return self.truncate_by_db_table("idx_file", store_id, idx)

    def truncate_ctx(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate context table in database

        :param store_id: store ID
        :param idx: index ID
        :return: True if truncated
        """
        return self.truncate_by_db_table("idx_ctx", store_id, idx)

    def truncate_external(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate external table in database

        :param store_id: store ID
        :param idx: index ID
        :return: True if truncated
        """
        return self.truncate_by_db_table("idx_external", store_id, idx)

    def truncate_by_db_table(self, tbl: str, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate external table in database

        :param tbl: table name
        :param store_id: store ID
        :param idx: index ID
        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        query = "DELETE FROM " + tbl
        params = {}
        if store_id and idx:
            query += " WHERE store = :store_id AND idx = :idx"
            params = {"store_id": store_id, "idx": idx}
        elif store_id:
            query += " WHERE store = :store_id"
            params = {"store_id": store_id}
        elif idx:
            query += " WHERE idx = :idx"
            params = {"idx": idx}
        with db.begin() as conn:
            conn.execute(
                text(query).bindparams(**params))
        return True

    def get_counters(self, type: str) -> dict:
        """
        Get counters (stats, count items by type [file, ctx, external])

        :param type: type of counter (file, ctx, external)
        :return: dict of counters
        """
        db_name = "idx_" + type
        db = self.window.core.db.get_db()
        counters = {}

        # count items, grouped by store and idx fields
        stmt = text("""
            SELECT store, idx, COUNT(*) as count
            FROM """ + db_name + """
            GROUP BY store, idx
        """)
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                data = row._asdict()
                store = data['store']
                idx = data['idx']
                count = data['count']
                if store not in counters:
                    counters[store] = {}
                counters[store][idx] = count
        return counters

