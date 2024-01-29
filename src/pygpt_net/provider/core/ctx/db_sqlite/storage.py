#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 23:00:00                  #
# ================================================== #

from datetime import datetime
import json
import re
import time

from sqlalchemy import text

from pygpt_net.item.ctx import CtxMeta, CtxItem
from .utils import search_by_date_string, pack_item_value, unpack_meta, unpack_item, get_month_start_end_timestamps


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
            date_ranges = search_by_date_string(search_string)
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
                unpack_meta(meta, row._asdict())
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
                unpack_item(item, row._asdict())
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
            updated_ts=ts
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
            is_internal=int(item.internal or 0)
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def get_ctx_count_by_day(self, year: int, month: int) -> dict:
        """
        Return ctx count by day for given year and month

        :param year: year
        :param month: month
        :return: dict with day as key and count as value
        """
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            start_timestamp, end_timestamp = get_month_start_end_timestamps(year, month)
            result = conn.execute(text("""
                SELECT
                    date(datetime(updated_ts, 'unixepoch')) as day,
                    COUNT(updated_ts) as count
                FROM ctx_meta
                WHERE updated_ts BETWEEN :start_ts AND :end_ts
                GROUP BY day
            """), {'start_ts': start_timestamp,
               'end_ts': end_timestamp})

            return {row._mapping['day']: row._mapping['count'] for row in result}
