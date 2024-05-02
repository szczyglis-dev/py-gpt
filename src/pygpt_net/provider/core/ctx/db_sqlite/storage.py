#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

from datetime import datetime
import re
import time

from sqlalchemy import text

from pygpt_net.item.ctx import CtxMeta, CtxItem, CtxGroup
from .utils import \
    search_by_date_string, \
    pack_item_value, \
    unpack_meta, \
    unpack_item, \
    get_month_start_end_timestamps, \
    get_year_start_end_timestamps, unpack_group


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

    def prepare_query(
            self,
            search_string: str = None,
            filters: dict = None,
            search_content: bool = False,
            append_date_ranges: bool = True,
    ):
        """
        Prepare query for search_string and filters

        :param search_string: search string
        :param filters: dict of filters
        :param search_content: search in content (input, output)
        :param append_date_ranges: append date ranges
        :return: where_statement, join_statement, bind_params
        """
        where_clauses = []
        join_clauses = []
        bind_params = {}

        # only base by default
        where_clauses.append("(m.root_id IS NULL OR m.root_id = 0)")

        # search_string
        if search_string:
            date_ranges = search_by_date_string(search_string)
            search_string = re.sub(
                r'@date\((\d{4}-\d{2}-\d{2})?(,)?(\d{4}-\d{2}-\d{2})?\)',
                '',
                search_string.strip(),
            )
            if search_string:
                if search_content:
                    where_clauses.append(
                        "(m.name LIKE :search_string OR i.input LIKE :search_string OR i.output LIKE :search_string)"
                    )
                    join_clauses.append("LEFT JOIN ctx_item i ON m.id = i.meta_id")
                else:
                    where_clauses.append("m.name LIKE :search_string")
                bind_params['search_string'] = f"%{search_string}%"

            if append_date_ranges:
                for start_ts, end_ts in date_ranges:
                    if start_ts and end_ts:
                        where_clauses.append("(m.updated_ts BETWEEN :start_ts AND :end_ts)")
                        bind_params['start_ts'] = start_ts
                        bind_params['end_ts'] = end_ts
                    elif start_ts:
                        where_clauses.append("(m.updated_ts >= :start_ts)")
                        bind_params['start_ts'] = start_ts
                    elif end_ts:
                        where_clauses.append("(m.updated_ts <= :end_ts)")
                        bind_params['end_ts'] = end_ts

        # display filters
        if filters:
            for key, filter in filters.items():
                if key == 'date_range':
                    continue
                mode = filter.get('mode', '=')
                value = filter.get('value', '')
                if isinstance(value, int):
                    where_clauses.append(f"{key} {mode} :{key}")
                    bind_params[key] = value
                elif isinstance(value, str):
                    where_clauses.append(f"{key} {mode} :{key}")
                    bind_params[key] = f"%{value}%"
                elif isinstance(value, list):
                    values = "(" + ",".join([str(x) for x in value]) + ")"
                    where_clauses.append(f"{key} {mode} {values}")

        where_statement = " AND ".join(where_clauses) if where_clauses else "1"
        join_statement = " ".join(join_clauses) if join_clauses else ""

        return where_statement, join_statement, bind_params

    def get_meta(
            self,
            search_string: str = None,
            order_by: str = None,
            order_direction: str = None,
            limit: int = None,
            offset: int = None,
            filters: dict = None,
            search_content: bool = False,
    ) -> dict:
        """
        Return dict with CtxMeta objects, indexed by ID

        :param search_string: search string
        :param order_by: order by
        :param order_direction: order direction (asc, desc)
        :param limit: result limit
        :param offset: result offset
        :param filters: dict of filters
        :param search_content: search in content (input, output)
        :return: dict of CtxMeta
        """
        limit_suffix = ""
        if limit is not None and limit > 0:
            limit_suffix = " LIMIT {}".format(limit)

        where_statement, join_statement, bind_params = self.prepare_query(
            search_string=search_string,
            filters=filters,
            search_content=search_content,
            append_date_ranges=True,
        )
        stmt_text = f"""
            SELECT m.* FROM ctx_meta m {join_statement} WHERE {where_statement}
            ORDER BY m.updated_ts DESC {limit_suffix}
        """
        stmt = text(stmt_text).bindparams(**bind_params)

        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                meta = CtxMeta()
                unpack_meta(meta, row._asdict())
                items[meta.id] = meta

        return items

    def get_meta_indexed(self) -> dict:
        """
        Return dict with indexed CtxMeta objects, indexed by ID

        :return: dict of CtxMeta
        """
        stmt_text = f"""
            SELECT * FROM ctx_meta WHERE indexed_ts > 0
        """
        stmt = text(stmt_text)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                meta = CtxMeta()
                unpack_meta(meta, row._asdict())
                items[meta.id] = meta
        return items

    def get_meta_by_root_id_and_preset_id(self, root_id: int, preset_id: str) -> dict:
        """
        Return dict with indexed CtxMeta objects, indexed by ID

        :return: dict of CtxMeta
        """
        stmt_text = f"""
            SELECT * FROM ctx_meta WHERE root_id = :root_id AND preset_id = :preset_id
        """
        stmt = text(stmt_text).bindparams(
            root_id=root_id,
            preset_id=preset_id,
        )
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                meta = CtxMeta()
                unpack_meta(meta, row._asdict())
                items[meta.id] = meta
        return items

    def get_meta_by_id(self, id: int) -> CtxMeta or None:
        """
        Return ctx meta by ID

        :return: CtxMeta
        """
        stmt = text("""
            SELECT * FROM ctx_meta WHERE id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            if row:
                meta = CtxMeta()
                unpack_meta(meta, row._asdict())
                return meta
        return None

    def get_last_meta_id(self) -> int:
        """
        Return last ctx meta ID

        :return: int
        """
        stmt = text("""
            SELECT id FROM ctx_meta ORDER BY updated_ts DESC LIMIT 1
        """)
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            row = result.fetchone()
            if row:
                return int(row.id)
        return 0

    def get_items(self, id: int) -> list:
        """
        Return ctx items list by ctx meta ID

        :return: list of CtxItem
        """
        stmt = text("""
            SELECT * FROM ctx_item WHERE meta_id = :id ORDER BY id ASC
        """).bindparams(id=id)
        items = []
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                item = CtxItem()
                unpack_item(item, row._asdict())
                items.append(item)
        return items

    def truncate_all(self, reset: bool = True) -> bool:
        """
        Truncate all ctx tables

        :param reset: reset table sequence (autoincrement)
        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM ctx_item"))
            conn.execute(text("DELETE FROM ctx_meta"))
            if reset:  # reset table sequence (autoincrement)
                conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='ctx_item'"))
                conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='ctx_meta'"))
        return True

    def delete_meta_by_id(self, id: int) -> bool:
        """
        Delete ctx meta by ID

        :param id: ctx meta ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM ctx_meta WHERE id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
        self.delete_items_by_meta_id(id)
        return True

    def delete_item_by_id(self, id: int) -> bool:
        """
        Delete ctx item by ID

        :param id: ctx item ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM ctx_item WHERE id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def delete_items_from(self, meta_id: int, item_id: int) -> bool:
        """
        Delete ctx items from ID

        :param meta_id: ctx meta ID
        :param item_id: ctx item ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM ctx_item WHERE id >= :item_id AND meta_id = :meta_id
        """).bindparams(
            meta_id=meta_id,
            item_id=item_id,
        )
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def delete_items_by_meta_id(self, id: int) -> bool:
        """
        Delete ctx items by ctx meta ID

        :param id: ctx meta ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM ctx_item WHERE meta_id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def update_meta(self, meta: CtxMeta) -> bool:
        """
        Update ctx meta

        :param meta: CtxMeta
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                external_id = :external_id,
                name = :name,
                mode = :mode,
                model = :model,
                last_mode = :last_mode,
                last_model = :last_model,
                thread_id = :thread_id,
                assistant_id = :assistant_id,
                preset_id = :preset_id,
                run_id = :run_id,
                status = :status,
                extra = :extra,
                is_initialized = :is_initialized,
                is_deleted = :is_deleted,
                is_important = :is_important,
                is_archived = :is_archived,
                label = :label,
                root_id = :root_id,
                parent_id = :parent_id
            WHERE id = :id
        """).bindparams(
            id=meta.id,
            external_id=meta.external_id,
            name=meta.name,
            mode=meta.mode,
            model=meta.model,
            last_mode=meta.last_mode,
            last_model=meta.last_model,
            thread_id=meta.thread,
            assistant_id=meta.assistant,
            preset_id=meta.preset,
            run_id=meta.run,
            status=meta.status,
            extra=meta.extra,
            is_initialized=int(meta.initialized),
            is_deleted=int(meta.deleted),
            is_important=int(meta.important),
            is_archived=int(meta.archived),
            label=int(meta.label),
            root_id=meta.root_id,
            parent_id=meta.parent_id,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def update_meta_all(self, meta: CtxMeta, items: list) -> bool:
        """
        Update all, meta and items

        :param meta: CtxMeta
        :param items: list of CtxItem
        """
        self.update_meta(meta)
        self.set_meta_ts(meta.id, meta.updated)
        for item in items:
            self.insert_item(meta, item)
        return True

    def set_meta_ts(self, id: int, ts: int) -> bool:
        """
        Update ctx meta updated timestamp

        :param id: ctx meta ID
        :param ts: timestamp
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                updated_ts = :updated_ts
            WHERE id = :id
        """).bindparams(
            id=id,
            updated_ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def set_meta_indexed_by_id(self, id: int, ts: int) -> bool:
        """
        Update ctx meta indexed timestamp

        :param id: ctx meta ID
        :param ts: timestamp
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                indexed_ts = :indexed_ts
            WHERE id = :id
        """).bindparams(
            id=id,
            indexed_ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def update_meta_indexes_by_id(self, id: int, meta: CtxMeta) -> bool:
        """
        Update ctx meta indexed timestamp

        :param id: ctx meta ID
        :param meta: CtxMeta
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                indexes_json = :indexes_json
            WHERE id = :id
        """).bindparams(
            id=id,
            indexes_json=pack_item_value(meta.indexes),
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def update_meta_ts(self, id: int) -> bool:
        """
        Update ctx meta updated timestamp

        :param id: ctx meta ID
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        ts = int(time.time())
        stmt = text("""
            UPDATE ctx_meta 
            SET
                updated_ts = :updated_ts
            WHERE id = :id
        """).bindparams(
            id=id,
            updated_ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def update_meta_indexed_by_id(self, id: int) -> bool:
        """
        Update ctx meta indexed timestamp

        :param id: ctx meta ID
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        ts = int(time.time())
        stmt = text("""
            UPDATE ctx_meta 
            SET
                indexed_ts = indexed_ts
            WHERE id = :id
        """).bindparams(
            id=id,
            indexed_ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def update_meta_indexed_to_ts(self, ts: int) -> bool:
        """
        Update ctx meta updated timestamp

        :param ts: timestamp to update to
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                indexed_ts = :ts
            WHERE updated_ts <= :ts
        """).bindparams(
            ts=ts,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def clear_meta_indexed_by_id(self, id: int) -> bool:
        """
        Clear ctx meta indexed timestamp

        :param id: ctx meta ID
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                indexed_ts = 0
            WHERE id = :id
        """).bindparams(
            id=id,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def clear_meta_indexed_all(self) -> bool:
        """
        Clear all ctx meta indexed timestamps

        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET indexed_ts = 0
        """)
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def insert_meta(self, meta: CtxMeta) -> int:
        """
        Insert ctx meta

        :param meta: CtxMeta
        :return: inserted record ID
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            INSERT INTO ctx_meta 
            (
                uuid,
                external_id,
                created_ts,
                updated_ts,
                name,
                mode,
                model,
                last_mode,
                last_model,
                thread_id,
                assistant_id,
                preset_id,
                run_id,
                status,
                extra,
                is_initialized,
                is_deleted,
                is_important,
                is_archived,
                label,
                group_id,
                root_id,
                parent_id
            )
            VALUES 
            (
                :uuid,
                :external_id,
                :created_ts,
                :updated_ts,
                :name,
                :mode,
                :model,
                :last_mode,
                :last_model,
                :thread_id,
                :assistant_id,
                :preset_id,
                :run_id,
                :status,
                :extra,
                :is_initialized,
                :is_deleted,
                :is_important,
                :is_archived,
                :label,
                :group_id,
                :root_id,
                :parent_id
            )
        """).bindparams(
            uuid=meta.uuid,
            external_id=meta.external_id,
            created_ts=int(meta.created or 0),
            updated_ts=int(meta.updated or 0),
            name=meta.name,
            mode=meta.mode,
            model=meta.model,
            last_mode=meta.last_mode,
            last_model=meta.last_model,
            thread_id=meta.thread,
            assistant_id=meta.assistant,
            preset_id=meta.preset,
            run_id=meta.run,
            status=meta.status,
            extra=meta.extra,
            is_initialized=int(meta.initialized),
            is_deleted=int(meta.deleted),
            is_important=int(meta.important),
            is_archived=int(meta.archived),
            label=int(meta.label),
            group_id=meta.group_id,
            root_id=meta.root_id,
            parent_id=meta.parent_id,
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            meta.id = result.lastrowid
            return meta.id

    def insert_item(self, meta: CtxMeta, item: CtxItem) -> int:
        """
        Insert ctx item

        :param meta: Context meta (CtxMeta)
        :param item: Context item (CtxItem)
        :return: inserted record ID
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            INSERT INTO ctx_item 
            (
                meta_id,
                external_id,
                input,
                output,
                input_name,
                output_name,
                input_ts,
                output_ts,
                mode,
                model,
                thread_id,
                msg_id,
                run_id,
                cmds_json,
                results_json,
                urls_json,
                images_json,
                files_json,
                attachments_json,
                extra,
                input_tokens,
                output_tokens,
                total_tokens,
                is_internal,
                docs_json
            )
            VALUES 
            (
                :meta_id,
                :external_id,
                :input,
                :output,
                :input_name,
                :output_name,
                :input_ts,
                :output_ts,
                :mode,
                :model,
                :thread_id,
                :msg_id,
                :run_id,
                :cmds_json,
                :results_json,
                :urls_json,
                :images_json,
                :files_json,
                :attachments_json,
                :extra,
                :input_tokens,
                :output_tokens,
                :total_tokens,
                :is_internal,
                :docs_json
            )
        """).bindparams(
            meta_id=int(meta.id),
            external_id=item.external_id,
            input=item.input,
            output=item.output,
            input_name=item.input_name,
            output_name=item.output_name,
            input_ts=int(item.input_timestamp or 0),
            output_ts=int(item.output_timestamp or 0),
            mode=item.mode,
            model=item.model,
            thread_id=item.thread,
            msg_id=item.msg_id,
            run_id=item.run_id,
            cmds_json=pack_item_value(item.cmds),
            results_json=pack_item_value(item.results),
            urls_json=pack_item_value(item.urls),
            images_json=pack_item_value(item.images),
            files_json=pack_item_value(item.files),
            attachments_json=pack_item_value(item.attachments),
            extra=pack_item_value(item.extra),
            input_tokens=int(item.input_tokens or 0),
            output_tokens=int(item.output_tokens or 0),
            total_tokens=int(item.total_tokens or 0),
            is_internal=int(item.internal),
            docs_json=pack_item_value(item.doc_ids),
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            item.id = result.lastrowid

        return item.id

    def update_item(self, item: CtxItem) -> bool:
        """
        Update ctx item

        :param item: Context item (CtxItem)
        :return: True if updated
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_item SET
                input = :input,
                output = :output,
                input_name = :input_name,
                output_name = :output_name,
                input_ts = :input_ts,
                output_ts = :output_ts,
                mode = :mode,
                model = :model,
                thread_id = :thread_id,
                msg_id = :msg_id,
                run_id = :run_id,
                cmds_json = :cmds_json,
                results_json = :results_json,
                urls_json = :urls_json,
                images_json = :images_json,
                files_json = :files_json,
                attachments_json = :attachments_json,
                extra = :extra,
                input_tokens = :input_tokens,
                output_tokens = :output_tokens,
                total_tokens = :total_tokens,
                is_internal = :is_internal,
                docs_json = :docs_json
            WHERE id = :id
        """).bindparams(
            id=item.id,
            input=item.input,
            output=item.output,
            input_name=item.input_name,
            output_name=item.output_name,
            input_ts=int(item.input_timestamp or 0),
            output_ts=int(item.output_timestamp or 0),
            mode=item.mode,
            model=item.model,
            thread_id=item.thread,
            msg_id=item.msg_id,
            run_id=item.run_id,
            cmds_json=pack_item_value(item.cmds),
            results_json=pack_item_value(item.results),
            urls_json=pack_item_value(item.urls),
            images_json=pack_item_value(item.images),
            files_json=pack_item_value(item.files),
            attachments_json=pack_item_value(item.attachments),
            extra=pack_item_value(item.extra),
            input_tokens=int(item.input_tokens or 0),
            output_tokens=int(item.output_tokens or 0),
            total_tokens=int(item.total_tokens or 0),
            is_internal=int(item.internal or 0),
            docs_json=pack_item_value(item.doc_ids),
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def get_ctx_count_by_day(
            self,
            year: int,
            month: int = None,
            day: int = None,
            search_string: str = None,
            filters: dict = None,
            search_content: bool = False,
    ) -> dict:
        """
        Return ctx counters by day for given year and month

        :param year: year
        :param month: month
        :param day: day
        :param search_string: search string
        :param filters: dict of filters
        :param search_content: search in content (input, output)
        :return: dict with day as key and count as value
        """
        # prepare query with search filters
        where_statement, join_statement, bind_params = self.prepare_query(
            search_string=search_string,
            filters=filters,
            search_content=search_content,
            append_date_ranges=False,  # without date ranges
        )

        # prepare where statement
        if where_statement == "1":
            where_statement = ""
        else:
            where_statement = f"AND {where_statement}"

        db = self.window.core.db.get_db()
        with db.connect() as conn:
            # by day
            if year and month and day:
                bind_params['start_ts'] = int(datetime(year, month, day, 0, 0, 0).timestamp())
                bind_params['end_ts'] = int(datetime(year, month, day, 23, 59, 59).timestamp())
                stmt_text = f"""
                    SELECT
                        date(datetime(m.updated_ts, 'unixepoch')) as day,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY day
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                return {row._mapping['day']: row._mapping['count'] for row in result}

            # by month
            elif year and month:
                start_timestamp, end_timestamp = get_month_start_end_timestamps(year, month)
                bind_params['start_ts'] = start_timestamp
                bind_params['end_ts'] = end_timestamp
                stmt_text = f"""
                    SELECT
                        date(datetime(m.updated_ts, 'unixepoch')) as day,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY day
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                return {row._mapping['day']: row._mapping['count'] for row in result}

            # by year (return months, not days)
            elif year:
                start_timestamp, end_timestamp = get_year_start_end_timestamps(year)
                bind_params['start_ts'] = start_timestamp
                bind_params['end_ts'] = end_timestamp
                stmt_text = f"""
                    SELECT
                        strftime('%m', datetime(m.updated_ts, 'unixepoch')) as month,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY month
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                return {row._mapping['month']: row._mapping['count'] for row in result}

    def get_groups(self) -> dict:
        """
        Return dict with CtxGroup objects, indexed by ID

        :return: dict of CtxGroup
        """
        stmt_text = f"""
            SELECT * FROM ctx_group g ORDER BY g.name ASC
        """
        stmt = text(stmt_text)

        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                group = CtxGroup()
                unpack_group(group, row._asdict())
                items[group.id] = group

        return items

    def delete_group(self, id: int, all: bool = False) -> bool:
        """
        Delete ctx group by ID

        :param id: ctx group ID
        :param all: remove items
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM ctx_group WHERE id = :id
        """).bindparams(
            id=id,
        )
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)

        # remove items in group
        if all:
            stmt = text("""
                DELETE FROM ctx_meta WHERE group_id = :id
            """).bindparams(
                id=id,
            )
            with db.begin() as conn:
                conn.execute(stmt)
        else:
            # set group_id to NULL (remove group association)
            stmt = text("""
                UPDATE ctx_meta 
                SET group_id = NULL
                WHERE group_id = :group_id
            """).bindparams(
                group_id=id,
            )
            with db.begin() as conn:
                conn.execute(stmt)
        return True

    def truncate_groups(self) -> bool:
        """
        Remove all groups

        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM ctx_group"))
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name='ctx_group'"))
        return True

    def update_group(self, group: CtxGroup) -> bool:
        """
        Update group

        :param group: CtxGroup
        :return: True if updated
        """
        id = group.id
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_group
            SET
                name = :name,
                updated_ts = :updated_ts
            WHERE id = :id
        """).bindparams(
            id=id,
            name=group.name,
            updated_ts=int(group.updated),
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def insert_group(self, group: CtxGroup) -> int:
        """
        Insert ctx group

        :param group: CtxGroup
        :return: inserted record ID
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            INSERT INTO ctx_group 
            (
                uuid,
                created_ts,
                updated_ts,
                name
            )
            VALUES 
            (
                :uuid,
                :created_ts,
                :updated_ts,
                :name
            )
        """).bindparams(
            uuid=group.uuid,
            created_ts=int(group.created or 0),
            updated_ts=int(group.updated or 0),
            name=group.name,
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            group.id = result.lastrowid
            return group.id

    def update_meta_group_id(self, meta_id: int, group_id: int = None):
        """
        Update meta group ID

        :param meta_id: ctx meta ID
        :param group_id: ctx group ID
        """
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_meta 
            SET
                group_id = :group_id
            WHERE id = :id
        """).bindparams(
            id=meta_id,
            group_id=group_id,
        )
        with db.begin() as conn:
            conn.execute(stmt)
            return True