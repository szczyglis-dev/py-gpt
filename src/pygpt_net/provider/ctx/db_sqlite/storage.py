#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 03:00:00                  #
# ================================================== #

from datetime import datetime
import json
import re
import time

from sqlalchemy import text

from pygpt_net.item.ctx import CtxMeta, CtxItem


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

    def search_by_date_string(self, search_string):
        """
        Prepare date ranges from search string if @date() syntax is used in search

        Examples of @date() syntax in search string:

        @date(YYYY-MM-DD) -- search in exact day
        @date(YYYY-MM-DD,YYYY-MM-DD) -- search in date range
        @date(,YYYY-MM-DD) -- search in date range from beginning of time
        @date(YYYY-MM-DD,) -- search in date range to end of time

        :param search_string: search string
        :return: list of date ranges
        """
        date_pattern = re.compile(r'@date\((\d{4}-\d{2}-\d{2})?(,)?(\d{4}-\d{2}-\d{2})?\)')
        matches = date_pattern.findall(search_string)
        date_ranges = []
        for match in matches:
            start_date_str, sep, end_date_str = match
            if start_date_str and end_date_str:
                # search between dates
                start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').timestamp()
                end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').timestamp()
                date_ranges.append((start_ts, end_ts))
            elif start_date_str and sep:
                # search from date to infinity
                start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').timestamp()
                end_of_day_ts = None
                date_ranges.append((start_ts, end_of_day_ts))
            elif end_date_str and sep:
                # search from beginning of time to date
                end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').timestamp()
                date_ranges.append((None, end_ts))
            elif start_date_str:
                # search in exact day
                start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').timestamp()
                end_of_day_ts = start_ts + (24 * 60 * 60) - 1
                date_ranges.append((start_ts, end_of_day_ts))
            elif end_date_str:
                # search in exact day
                end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').timestamp()
                date_ranges.append((0, end_ts))

        return date_ranges

    def get_meta(self, search_string: str = None, order_by: str = None, order_direction: str = None,
                 limit: int = None, offset: int = None) -> dict:
        """
        Return dict with CtxMeta objects, indexed by ID

        :return: dict of CtxMeta
        """
        limit_suffix = ""
        if limit is not None and limit > 0:
            limit_suffix = " LIMIT {}".format(limit)

        if search_string is None or search_string == "":
            stmt = text("""
                SELECT * FROM ctx_meta ORDER BY updated_ts DESC {}
            """.format(limit_suffix))
        else:
            # now we can search by search string or with date ranges
            # 1) first check if search string contains @date() syntax
            date_ranges = self.search_by_date_string(search_string)
            if len(date_ranges) > 0:
                # if yes, then remove @date() syntax from search string
                search_string = re.sub(r'@date\((\d{4}-\d{2}-\d{2})?(,)?(\d{4}-\d{2}-\d{2})?\)', '', search_string.strip())

                # prepare query
                date_ranges_query = []
                bind_params = {}

                # add string search to date ranges
                if search_string:
                    date_ranges_query.append("(name LIKE :search_string)".format(search_string))
                    bind_params['search_string'] = '%'+search_string+'%'

                # and add date ranges to query
                for date_range in date_ranges:
                    start_ts, end_ts = date_range
                    if start_ts is not None and end_ts is not None:
                        date_ranges_query.append("(updated_ts BETWEEN :start_ts AND :end_ts)")
                        bind_params['start_ts'] = start_ts
                        bind_params['end_ts'] = end_ts
                    elif start_ts is not None:
                        date_ranges_query.append("(updated_ts >= :start_ts)")
                        bind_params['start_ts'] = start_ts
                    elif end_ts is not None:
                        date_ranges_query.append("(updated_ts <= :end_ts)")
                        bind_params['end_ts'] = end_ts
                    break  # TODO: remove this break when multiple date ranges will be supported
                date_ranges_query = " AND ".join(date_ranges_query)
                stmt = text("""
                    SELECT * FROM ctx_meta WHERE {} ORDER BY updated_ts DESC {}
                """.format(date_ranges_query, limit_suffix)).bindparams(**bind_params)

            else:
                # 2) if no, then search by search string only
                stmt = text("""
                    SELECT * FROM ctx_meta WHERE name LIKE :search_string ORDER BY updated_ts DESC {}
                """.format(limit_suffix)).bindparams(search_string=f"%{search_string}%")

        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                meta = CtxMeta()
                self.unpack_meta(meta, row._asdict())
                items[meta.id] = meta
        return items

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
                self.unpack_item(item, row._asdict())
                items.append(item)
        return items

    def truncate_all(self) -> bool:
        """
        Truncate all ctx tables

        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM ctx_item"))
            conn.execute(text("DELETE FROM ctx_meta"))
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
                label = :label
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
            updated_ts=ts
        )
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
                label
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
                :label
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
            label=int(meta.label)
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
                is_internal
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
                :is_internal
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
            cmds_json=self.pack_item_value(item.cmds),
            results_json=self.pack_item_value(item.results),
            urls_json=self.pack_item_value(item.urls),
            images_json=self.pack_item_value(item.images),
            files_json=self.pack_item_value(item.files),
            attachments_json=self.pack_item_value(item.attachments),
            extra=self.pack_item_value(item.extra),
            input_tokens=int(item.input_tokens or 0),
            output_tokens=int(item.output_tokens or 0),
            total_tokens=int(item.total_tokens or 0),
            is_internal=int(item.internal)
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
                is_internal = :is_internal
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
            cmds_json=self.pack_item_value(item.cmds),
            results_json=self.pack_item_value(item.results),
            urls_json=self.pack_item_value(item.urls),
            images_json=self.pack_item_value(item.images),
            files_json=self.pack_item_value(item.files),
            attachments_json=self.pack_item_value(item.attachments),
            extra=self.pack_item_value(item.extra),
            input_tokens=int(item.input_tokens or 0),
            output_tokens=int(item.output_tokens or 0),
            total_tokens=int(item.total_tokens or 0),
            is_internal=int(item.internal or 0)
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def get_ctx_count_by_day(self, year, month):
        """Return ctx count by day for given year and month"""
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    strftime('%Y-%m-%d', datetime(updated_ts, 'unixepoch')) as day,
                    COUNT(*) as count
                FROM ctx_meta
                WHERE strftime('%Y', datetime(updated_ts, 'unixepoch')) = :year 
                  AND strftime('%m', datetime(updated_ts, 'unixepoch')) = :month
                GROUP BY day
            """), {'year': str(year),
                   'month': f'{month:02}'})

            return {row._mapping['day']: row._mapping['count'] for row in result}

    def pack_item_value(self, value: any) -> str:
        """
        Pack item value to JSON

        :param value: Value to pack
        :return: JSON string or value itself
        """
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return value

    def unpack_item_value(self, value: any) -> any:
        """
        Unpack item value from JSON

        :param value: Value to unpack
        :return: Unpacked value
        """
        if value is None:
            return None
        try:
            return json.loads(value)
        except:
            return value

    def unpack_item(self, item: CtxItem, row: dict) -> CtxItem:
        """
        Unpack item from DB row

        :param item: Context item (CtxItem)
        :param row: DB row
        :return: context item
        """
        item.id = int(row['id'])
        item.meta_id = int(row['meta_id'])
        item.external_id = row['external_id']
        item.input = row['input']
        item.output = row['output']
        item.input_name = row['input_name']
        item.output_name = row['output_name']
        item.input_timestamp = int(row['input_ts'] or 0)
        item.output_timestamp = int(row['output_ts'] or 0)
        item.mode = row['mode']
        item.model = row['model']
        item.thread = row['thread_id']
        item.msg_id = row['msg_id']
        item.run_id = row['run_id']
        item.cmds = self.unpack_item_value(row['cmds_json'])
        item.results = self.unpack_item_value(row['results_json'])
        item.urls = self.unpack_item_value(row['urls_json'])
        item.images = self.unpack_item_value(row['images_json'])
        item.files = self.unpack_item_value(row['files_json'])
        item.attachments = self.unpack_item_value(row['attachments_json'])
        item.extra = self.unpack_item_value(row['extra'])
        item.input_tokens = int(row['input_tokens'] or 0)
        item.output_tokens = int(row['output_tokens'] or 0)
        item.total_tokens = int(row['total_tokens'] or 0)
        item.internal = bool(row['is_internal'])
        return item

    def unpack_meta(self, meta: CtxMeta, row: dict) -> CtxMeta:
        """
        Unpack meta from DB row

        :param meta: Context meta (CtxMeta)
        :param row: DB row
        :return: context meta
        """
        meta.id = int(row['id'])
        meta.external_id = row['external_id']
        meta.uuid = row['uuid']
        meta.created = int(row['created_ts'])
        meta.updated = int(row['updated_ts'])
        meta.name = row['name']
        meta.mode = row['mode']
        meta.model = row['model']
        meta.last_mode = row['last_mode']
        meta.last_model = row['last_model']
        meta.thread = row['thread_id']
        meta.assistant = row['assistant_id']
        meta.preset = row['preset_id']
        meta.run = row['run_id']
        meta.status = row['status']
        meta.extra = row['extra']
        meta.initialized = bool(row['is_initialized'])
        meta.deleted = bool(row['is_deleted'])
        meta.important = bool(row['is_important'])
        meta.archived = bool(row['is_archived'])
        meta.label = int(row['label'] or 0)
        return meta
