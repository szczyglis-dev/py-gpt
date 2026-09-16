#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.16 14:35:00                  #
# ================================================== #

from datetime import datetime
import copy
import json
import re
import time
from typing import Dict, Optional, Tuple, List

from sqlalchemy import text

from pygpt_net.utils import get_tz_offset
from pygpt_net.core.types import CTX_TOOL_HISTORY_EXTRA_KEY, should_persist_ctx_partials
from pygpt_net.item.ctx import CtxMeta, CtxItem, CtxGroup
from pygpt_net.item.ctx_part import CtxItemPart
from pygpt_net.item.ctx_part_task import CtxItemPartTask
from .utils import \
    search_by_date_string, \
    pack_item_value, \
    unpack_meta, \
    unpack_item, \
    unpack_part, \
    unpack_part_task, \
    get_month_start_end_timestamps, \
    get_year_start_end_timestamps, \
    unpack_group


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

    def _pack_ctx_images(self, item: CtxItem) -> str:
        """Pack ctx images while defensively excluding transport-only attachments."""
        images = list(item.images or []) if isinstance(item.images, list) else item.images
        attachments = getattr(getattr(self.window, "core", None), "attachments", None)
        if isinstance(images, list) and attachments is not None and hasattr(attachments, "is_ctx_excluded_path"):
            images = [value for value in images if not attachments.is_ctx_excluded_path(value)]
        return pack_item_value(images)

    @staticmethod
    def _match_ctx_tool_history_response(call: dict, outputs: list, used: set):
        """Return the best legacy ctx.extra tool output for one stored call."""
        if not isinstance(call, dict):
            return None, None
        function = call.get("function") if isinstance(call.get("function"), dict) else {}
        name = str(function.get("name") or "")
        call_id = str(call.get("call_id") or call.get("id") or "")

        for index, output in enumerate(outputs or []):
            if index in used or not isinstance(output, dict):
                continue
            output_call_id = str(output.get("call_id") or output.get("tool_call_id") or "")
            if call_id and output_call_id and output_call_id == call_id:
                return index, output
        for index, output in enumerate(outputs or []):
            if index in used or not isinstance(output, dict):
                continue
            output_name = str(output.get("cmd") or "")
            request = output.get("request") if isinstance(output.get("request"), dict) else {}
            if not output_name:
                output_name = str(request.get("cmd") or "")
            if name and output_name == name:
                return index, output
        for index, output in enumerate(outputs or []):
            if index not in used:
                return index, output
        return None, None

    def _restore_transient_tool_part(self, item: CtxItem) -> None:
        """Rehydrate runtime partial/tasks from compact ctx_item tool metadata.

        Non-workflow modes intentionally do not have durable partial rows. When a
        conversation is loaded, reconstruct the same in-memory task graph from the
        compact ctx_item.extra transcript so existing render/history code keeps
        working without writing anything back to ctx_item_partial tables.
        """
        if item is None or item.parts or should_persist_ctx_partials(item.mode):
            return
        extra = item.extra if isinstance(item.extra, dict) else {}
        history = extra.get(CTX_TOOL_HISTORY_EXTRA_KEY)

        # Backward compatibility for ctx_item rows created before the compact
        # transcript was introduced. Such rows can still carry the last stored
        # call/result pair in the old compatibility keys.
        if not isinstance(history, list) or not history:
            calls = extra.get("tool_calls") if isinstance(extra.get("tool_calls"), list) else []
            outputs = extra.get("tool_output") if isinstance(extra.get("tool_output"), list) else []
            if not calls:
                return
            history = []
            used_outputs = set()
            for call in calls:
                if not isinstance(call, dict):
                    continue
                index, response = self._match_ctx_tool_history_response(call, outputs, used_outputs)
                if index is not None:
                    used_outputs.add(index)
                history.append({
                    "call": copy.deepcopy(call),
                    "response": copy.deepcopy(response),
                    "completed": response is not None,
                    "tool_round": 1,
                    "ui_visible": True,
                    "ui_ready": response is not None,
                    "provider_history": True,
                })

        outputs = extra.get("tool_output") if isinstance(extra.get("tool_output"), list) else []
        used_outputs = set()
        part = CtxItemPart(parent_item_id=item.id, output=item.output)
        part.extra = {"runtime_restored": True}
        max_round = 0
        for entry in history:
            if not isinstance(entry, dict):
                continue
            call = entry.get("call")
            if not isinstance(call, dict):
                continue
            function = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = str(function.get("name") or "").strip()
            if not name:
                continue
            args = copy.deepcopy(function.get("arguments", {}))
            call_id = str(call.get("call_id") or call.get("id") or "")
            item_id = str(call.get("id") or call_id)
            try:
                tool_round = max(1, int(entry.get("tool_round") or 1))
            except (TypeError, ValueError):
                tool_round = 1
            max_round = max(max_round, tool_round)
            response = copy.deepcopy(entry.get("response")) if entry.get("response") is not None else None
            if response is None:
                response_index, matched = self._match_ctx_tool_history_response(call, outputs, used_outputs)
                if response_index is not None:
                    used_outputs.add(response_index)
                    response = copy.deepcopy(matched)
            completed = bool(entry.get("completed") or response is not None)
            if isinstance(response, dict) and "result" in response:
                output = response.get("result")
            else:
                output = response
            if output is not None and not isinstance(output, str):
                output = json.dumps(output, ensure_ascii=False, default=str)

            task = CtxItemPartTask(
                parent_item_part_id=None,
                task_name=name,
                input=json.dumps(
                    {"cmd": name, "params": args},
                    ensure_ascii=False,
                    default=str,
                ),
                output=output,
                tool_call_id=call_id or item_id,
                tool_input=args,
                tool_output=response,
                extra={
                    "status": "completed" if completed else "pending",
                    "ui_ready": bool(entry.get("ui_ready", completed)),
                    "tool_name": name,
                    "tool_item_id": item_id,
                    "tool_type": str(call.get("type") or "function"),
                    "tool_round": tool_round,
                    "ui_visible": bool(entry.get("ui_visible", True)),
                    "provider_history": bool(entry.get("provider_history", True)),
                    "runtime_restored": True,
                },
            )
            part.tasks.append(task)

        if not part.tasks:
            return
        # The compact ctx_item representation stores the final visible assistant
        # text, so on reconstruction place it after all restored tool rounds.
        part.extra["text_after_tool_round"] = max_round
        item.parts = [part]
        item.active_part = part

    def prepare_query(
            self,
            search_string: Optional[str] = None,
            filters: Optional[dict] = None,
            search_content: bool = False,
            append_date_ranges: bool = True,
    ) -> Tuple[str, str, dict]:
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

        # join group
        join_clauses.append("LEFT JOIN ctx_group g ON m.group_id = g.id")

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

                # handle special case for "ungrouped" (group_id IS NULL OR = 0)
                if key == 'group_id' and str(mode).upper() == 'NULL_OR_ZERO':
                    where_clauses.append("(m.group_id IS NULL OR m.group_id = 0)")
                    continue

                key_name = 'm.' + key
                if isinstance(value, int):
                    where_clauses.append(f"{key_name} {mode} :{key}")
                    bind_params[key] = value
                elif isinstance(value, str):
                    where_clauses.append(f"{key_name} {mode} :{key}")
                    bind_params[key] = f"%{value}%"
                elif isinstance(value, list) and len(value) > 0:
                    values = "(" + ",".join([str(x) for x in value]) + ")"
                    where_clauses.append(f"{key_name} {mode} {values}")

        where_statement = " AND ".join(where_clauses) if where_clauses else "1"
        join_statement = " ".join(join_clauses) if join_clauses else ""

        return where_statement, join_statement, bind_params

    def get_meta(
            self,
            search_string: Optional[str] = None,
            order_by: Optional[str] = None,
            order_direction: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            filters: Optional[dict] = None,
            search_content: bool = False,
    ) -> Dict[int, CtxMeta]:
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
        where_statement, join_statement, bind_params = self.prepare_query(
            search_string=search_string,
            filters=filters,
            search_content=search_content,
            append_date_ranges=True,
        )

        # Build LIMIT/OFFSET only when limit > 0; LIMIT 0 would mean "no rows"
        if limit is not None and int(limit) > 0:
            limit_suffix = " LIMIT :limit"
            bind_params['limit'] = int(limit)
            if offset is not None and int(offset) > 0:
                limit_suffix += " OFFSET :offset"
                bind_params['offset'] = int(offset)

        stmt_text = f"""
            SELECT 
                m.*,
                g.name as group_name,
                g.uuid as group_uuid,
                g.additional_ctx_json as group_additional_ctx_json,
                g.extra_json as group_extra_json
            FROM 
                ctx_meta m 
                {join_statement} 
            WHERE 
                {where_statement}
            GROUP BY 
                m.id
            ORDER BY 
                m.updated_ts DESC {limit_suffix}
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

    def count_meta(
            self,
            search_string: Optional[str] = None,
            filters: Optional[dict] = None,
            search_content: bool = False,
    ) -> int:
        """
        Count distinct context metadata rows matching search/filter criteria.

        This mirrors get_meta() filtering without materializing all CtxMeta
        objects, which is important for the paginated Recent section counter.

        :param search_string: search string
        :param filters: dict of filters
        :param search_content: search in content (input, output)
        :return: number of matching contexts
        """
        where_statement, join_statement, bind_params = self.prepare_query(
            search_string=search_string,
            filters=filters,
            search_content=search_content,
            append_date_ranges=True,
        )

        stmt = text(f"""
            SELECT COUNT(DISTINCT m.id) AS total
            FROM ctx_meta m
            {join_statement}
            WHERE {where_statement}
        """).bindparams(**bind_params)

        db = self.window.core.db.get_db()
        with db.connect() as conn:
            row = conn.execute(stmt).fetchone()
            if row is None:
                return 0
            return int(row.total or 0)

    def get_meta_indexed(self) -> Dict[int, CtxMeta]:
        """
        Return dict with indexed CtxMeta objects, indexed by ID

        :return: dict of CtxMeta
        """
        stmt_text = f"""
            SELECT 
                m.*, 
                g.name as group_name,
                g.uuid as group_uuid,
                g.additional_ctx_json as group_additional_ctx_json,
                g.extra_json as group_extra_json 
            FROM 
                ctx_meta m 
            LEFT JOIN 
                ctx_group g ON m.group_id = g.id
            WHERE 
                indexed_ts > 0
                OR COALESCE(indexes_json, '{{}}') != '{{}}'
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

    def _get_items_with_parts(self, where: str, params: dict) -> List[CtxItem]:
        """Load items, partial items and tasks in one JOIN and compose outputs."""
        stmt = text(f"""
            SELECT
                i.*,
                p.id AS p_id, p.uuid AS p_uuid, p.parent_item_id AS p_parent_item_id,
                p.agent_id AS p_agent_id, p.name AS p_name, p.output AS p_output,
                p.extra_json AS p_extra_json, p.created_at AS p_created_at, p.updated_at AS p_updated_at,
                t.id AS t_id, t.uuid AS t_uuid, t.parent_item_part_id AS t_parent_item_part_id,
                t.agent_id AS t_agent_id, t.name AS t_name, t.task_name AS t_task_name,
                t.task_summary AS t_task_summary, t.input AS t_input, t.output AS t_output,
                t.tool_call_id AS t_tool_call_id, t.tool_input_json AS t_tool_input_json,
                t.tool_output_json AS t_tool_output_json, t.extra_json AS t_extra_json,
                t.created_at AS t_created_at, t.updated_at AS t_updated_at
            FROM ctx_item i
            LEFT JOIN ctx_item_partial p ON p.parent_item_id = i.id
            LEFT JOIN ctx_item_partial_task t ON t.parent_item_part_id = p.id
            WHERE {where}
            ORDER BY i.id ASC, p.id ASC, t.id ASC
        """).bindparams(**params)
        db = self.window.core.db.get_db()
        items = {}
        parts = {}
        with db.connect() as conn:
            for row in conn.execute(stmt):
                data = row._asdict()
                item_id = int(data['id'])
                item = items.get(item_id)
                if item is None:
                    item = CtxItem()
                    unpack_item(item, data)
                    item.parts = []
                    item.active_part = None
                    items[item_id] = item

                part_id = data.get('p_id')
                if part_id is None:
                    continue
                part_id = int(part_id)
                part = parts.get(part_id)
                if part is None:
                    part = CtxItemPart()
                    unpack_part(part, data, prefix='p_')
                    parts[part_id] = part
                    item.parts.append(part)
                    item.active_part = part

                task_id = data.get('t_id')
                if task_id is not None and not any(t.id == int(task_id) for t in part.tasks):
                    task = CtxItemPartTask()
                    unpack_part_task(task, data, prefix='t_')
                    part.tasks.append(task)

        result = list(items.values())
        for item in result:
            self._restore_transient_tool_part(item)
            if item.parts:
                item.sync_output_from_parts()
        return result

    def get_item_by_id(self, id: int) -> Optional[CtxItem]:
        """Return ctx item by ID with partial items/tasks eagerly loaded."""
        items = self._get_items_with_parts("i.id = :id", {"id": id})
        if not items:
            return None
        item = items[0]
        item.meta = self.get_meta_by_id(item.meta_id)
        return item

    def get_meta_by_root_id_and_preset_id(
            self,
            root_id: int,
            preset_id: str
    ) -> Dict[int, CtxMeta]:
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

    def get_meta_by_id(self, id: int) -> Optional[CtxMeta]:
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

    def get_items(self, id: int) -> List[CtxItem]:
        """Return ctx items with partial items/tasks eagerly loaded."""
        return self._get_items_with_parts("i.meta_id = :id", {"id": id})

    def truncate_all(self, reset: bool = True) -> bool:
        """
        Truncate all ctx tables

        :param reset: reset table sequence (autoincrement)
        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM ctx_item_partial_task"))
            conn.execute(text("DELETE FROM ctx_item_partial"))
            conn.execute(text("DELETE FROM ctx_item"))
            # SQLite foreign-key enforcement is not guaranteed in legacy user
            # databases, so clean per-conversation continuation memory explicitly.
            conn.execute(text("DELETE FROM memory_ctx"))
            conn.execute(text("DELETE FROM ctx_meta"))
            if reset:  # reset table sequence (autoincrement)
                conn.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('ctx_item_partial_task','ctx_item_partial','ctx_item','memory_ctx','ctx_meta')"))
        return True

    def delete_meta_by_id(self, id: int) -> bool:
        """
        Delete ctx meta and all of its items.

        Items are deleted first so cleanup is deterministic even if SQLite
        foreign-key enforcement is enabled (legacy schema uses SET NULL).
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM ctx_item_partial_task WHERE parent_item_part_id IN (SELECT p.id FROM ctx_item_partial p JOIN ctx_item i ON i.id=p.parent_item_id WHERE i.meta_id=:id)").bindparams(id=id))
            conn.execute(text("DELETE FROM ctx_item_partial WHERE parent_item_id IN (SELECT id FROM ctx_item WHERE meta_id=:id)").bindparams(id=id))
            conn.execute(text("DELETE FROM ctx_item WHERE meta_id = :id").bindparams(id=id))
            conn.execute(text("DELETE FROM memory_ctx WHERE meta_id = :id").bindparams(id=id))
            conn.execute(text("DELETE FROM ctx_meta WHERE id = :id").bindparams(id=id))
        return True

    def delete_item_by_id(self, id: int) -> bool:
        """
        Delete ctx item by ID

        :param id: ctx item ID
        :return: True if deleted
        """
        stmt = text("DELETE FROM ctx_item WHERE id = :id").bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            meta_row = conn.execute(
                text("SELECT meta_id FROM ctx_item WHERE id = :id LIMIT 1").bindparams(id=id)
            ).fetchone()
            conn.execute(text("DELETE FROM ctx_item_partial_task WHERE parent_item_part_id IN (SELECT id FROM ctx_item_partial WHERE parent_item_id=:id)").bindparams(id=id))
            conn.execute(text("DELETE FROM ctx_item_partial WHERE parent_item_id=:id").bindparams(id=id))
            conn.execute(stmt)
            if meta_row and meta_row[0] is not None:
                # If the removed turn had already been rolled into continuation
                # notes, those notes are no longer a faithful projection. Drop
                # the checkpoint so the next request rebuilds from raw history.
                conn.execute(text(
                    "DELETE FROM memory_ctx WHERE meta_id = :meta_id AND last_item_id >= :item_id"
                ).bindparams(meta_id=int(meta_row[0]), item_id=id))
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
            conn.execute(text("DELETE FROM ctx_item_partial_task WHERE parent_item_part_id IN (SELECT p.id FROM ctx_item_partial p JOIN ctx_item i ON i.id=p.parent_item_id WHERE i.id>=:item_id AND i.meta_id=:meta_id)").bindparams(item_id=item_id, meta_id=meta_id))
            conn.execute(text("DELETE FROM ctx_item_partial WHERE parent_item_id IN (SELECT id FROM ctx_item WHERE id>=:item_id AND meta_id=:meta_id)").bindparams(item_id=item_id, meta_id=meta_id))
            conn.execute(stmt)
            conn.execute(text(
                "DELETE FROM memory_ctx WHERE meta_id = :meta_id AND last_item_id >= :item_id"
            ).bindparams(meta_id=meta_id, item_id=item_id))
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
            conn.execute(text("DELETE FROM ctx_item_partial_task WHERE parent_item_part_id IN (SELECT p.id FROM ctx_item_partial p JOIN ctx_item i ON i.id=p.parent_item_id WHERE i.meta_id=:id)").bindparams(id=id))
            conn.execute(text("DELETE FROM ctx_item_partial WHERE parent_item_id IN (SELECT id FROM ctx_item WHERE meta_id=:id)").bindparams(id=id))
            conn.execute(stmt)
            conn.execute(text("DELETE FROM memory_ctx WHERE meta_id = :id").bindparams(id=id))
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
                parent_id = :parent_id,
                additional_ctx_json = :additional_ctx_json
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
            additional_ctx_json=pack_item_value(meta.additional_ctx),
        )
        with db.begin() as conn:
            conn.execute(stmt)

        # update group
        if meta.group:
            stmt = text("""
                UPDATE ctx_group
                SET
                    name = :name,
                    additional_ctx_json = :additional_ctx_json,
                    extra_json = :extra_json,
                    updated_ts = :updated_ts
                WHERE id = :id
            """).bindparams(
                id=meta.group.id,
                name=meta.group.name,
                additional_ctx_json=pack_item_value(meta.group.additional_ctx),
                extra_json=pack_item_value(meta.group.extra),
                updated_ts=int(time.time()),
            )
            with db.begin() as conn:
                conn.execute(stmt)

        return True

    def update_meta_all(
            self,
            meta: CtxMeta,
            items: List[CtxItem]
    ) -> bool:
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
                parent_id,
                additional_ctx_json
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
                :parent_id,
                :additional_ctx_json
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
            additional_ctx_json=pack_item_value(meta.additional_ctx),
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            meta.id = result.lastrowid
            return meta.id

    def insert_part(self, part: CtxItemPart) -> int:
        db = self.window.core.db.get_db()
        now = int(time.time())
        if not part.created_at:
            part.created_at = now
        part.updated_at = now
        stmt = text("""
            INSERT INTO ctx_item_partial
            (uuid, parent_item_id, agent_id, name, output, extra_json, created_at, updated_at)
            VALUES (:uuid, :parent_item_id, :agent_id, :name, :output, :extra_json, :created_at, :updated_at)
        """).bindparams(
            uuid=part.uuid, parent_item_id=part.parent_item_id, agent_id=part.agent_id,
            name=part.name, output=self.window.core.command.output_for_storage(part.output),
            extra_json=pack_item_value(self.window.core.command.extra_for_storage(part.extra)),
            created_at=int(part.created_at or now), updated_at=int(part.updated_at or now),
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            part.id = result.lastrowid
        return part.id

    def update_part(self, part: CtxItemPart) -> bool:
        if part.id is None:
            return False
        part.updated_at = int(time.time())
        db = self.window.core.db.get_db()
        stmt = text("""
            UPDATE ctx_item_partial SET agent_id=:agent_id, name=:name, output=:output,
                extra_json=:extra_json, updated_at=:updated_at WHERE id=:id
        """).bindparams(
            id=part.id, agent_id=part.agent_id, name=part.name,
            output=self.window.core.command.output_for_storage(part.output),
            extra_json=pack_item_value(self.window.core.command.extra_for_storage(part.extra)),
            updated_at=part.updated_at,
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def insert_part_task(self, task: CtxItemPartTask) -> Optional[int]:
        # Tool calls are runtime objects first. The user may choose not to keep
        # them in durable history at all; in that mode leave the task in memory
        # with ``id=None`` so the active provider/tool loop can still complete.
        command = self.window.core.command
        if not command.should_store_tool_task(task):
            return None

        db = self.window.core.db.get_db()
        now = int(time.time())
        if not task.created_at:
            task.created_at = now
        task.updated_at = now
        stored = command.tool_task_values_for_storage(task)
        stmt = text("""
            INSERT INTO ctx_item_partial_task
            (uuid, parent_item_part_id, agent_id, name, task_name, task_summary, input, output,
             tool_call_id, tool_input_json, tool_output_json, extra_json, created_at, updated_at)
            VALUES (:uuid, :parent, :agent_id, :name, :task_name, :task_summary, :input, :output,
                    :tool_call_id, :tool_input, :tool_output, :extra, :created_at, :updated_at)
        """).bindparams(
            uuid=task.uuid, parent=task.parent_item_part_id, agent_id=task.agent_id, name=task.name,
            task_name=task.task_name, task_summary=task.task_summary,
            input=stored["input"], output=stored["output"],
            tool_call_id=task.tool_call_id, tool_input=pack_item_value(stored["tool_input"]),
            tool_output=pack_item_value(stored["tool_output"]), extra=pack_item_value(stored["extra"]),
            created_at=int(task.created_at or now), updated_at=int(task.updated_at or now),
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            task.id = result.lastrowid
        return task.id

    def update_part_task(self, task: CtxItemPartTask) -> bool:
        if task.id is None:
            return False
        task.updated_at = int(time.time())
        db = self.window.core.db.get_db()
        command = self.window.core.command
        if not command.should_store_tool_task(task):
            # The policy can be changed while a tool is still running. If a row
            # was created before switching to "Do not store", remove it on the
            # next write rather than leaving a half-persisted call in history.
            stmt = text("DELETE FROM ctx_item_partial_task WHERE id=:id").bindparams(id=task.id)
            with db.begin() as conn:
                conn.execute(stmt)
            task.id = None
            return True

        stored = command.tool_task_values_for_storage(task)
        stmt = text("""
            UPDATE ctx_item_partial_task SET agent_id=:agent_id, name=:name, task_name=:task_name,
                task_summary=:task_summary, input=:input, output=:output, tool_call_id=:tool_call_id,
                tool_input_json=:tool_input, tool_output_json=:tool_output, extra_json=:extra,
                updated_at=:updated_at WHERE id=:id
        """).bindparams(
            id=task.id, agent_id=task.agent_id, name=task.name, task_name=task.task_name,
            task_summary=task.task_summary, input=stored["input"], output=stored["output"],
            tool_call_id=task.tool_call_id,
            tool_input=pack_item_value(stored["tool_input"]), tool_output=pack_item_value(stored["tool_output"]),
            extra=pack_item_value(stored["extra"]), updated_at=task.updated_at,
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

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
                hidden_input,
                hidden_output,
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
                additional_ctx_json,
                extra,
                input_tokens,
                output_tokens,
                total_tokens,
                is_internal,
                docs_json,
                audio_id,
                audio_expires_ts
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
                :hidden_input,
                :hidden_output,
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
                :additional_ctx_json,
                :extra,
                :input_tokens,
                :output_tokens,
                :total_tokens,
                :is_internal,
                :docs_json,
                :audio_id,
                :audio_expires_ts
            )
        """).bindparams(
            meta_id=int(meta.id),
            external_id=item.external_id,
            input=item.input,
            output=self.window.core.command.output_for_storage(item.output),
            input_name=item.input_name,
            output_name=item.output_name,
            input_ts=int(item.input_timestamp or 0),
            output_ts=int(item.output_timestamp or 0),
            hidden_input=item.hidden_input,
            hidden_output=item.hidden_output,
            mode=item.mode,
            model=item.model,
            thread_id=item.thread,
            msg_id=item.msg_id,
            run_id=item.run_id,
            cmds_json=pack_item_value(self.window.core.command.commands_for_storage(item.cmds)),
            results_json=pack_item_value(self.window.core.command.tool_results_for_storage(item.results)),
            urls_json=pack_item_value(item.urls),
            images_json=self._pack_ctx_images(item),
            files_json=pack_item_value(item.files),
            attachments_json=pack_item_value(item.attachments),
            additional_ctx_json=pack_item_value(item.additional_ctx),
            extra=pack_item_value(self.window.core.command.extra_for_storage(item.extra)),
            input_tokens=int(item.input_tokens or 0),
            output_tokens=int(item.output_tokens or 0),
            total_tokens=int(item.total_tokens or 0),
            is_internal=int(item.internal),
            docs_json=pack_item_value(item.doc_ids),
            audio_id=item.audio_id,
            audio_expires_ts=int(item.audio_expires_ts or 0)
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            item.id = result.lastrowid

        # Persist the rich partial/task graph only for workflow modes. Ordinary
        # Chat/Chat with Files/etc. keep ctx_item as the durable format and may
        # allocate CtxItemPart objects later purely for the live tool loop.
        if should_persist_ctx_partials(item.mode):
            if not item.parts:
                part = CtxItemPart(parent_item_id=item.id, output=item.output)
                self.insert_part(part)
                item.parts.append(part)
                item.active_part = part
            else:
                for part in item.parts:
                    tasks = list(part.tasks or [])
                    part.id = None
                    part.parent_item_id = item.id
                    self.insert_part(part)
                    for task in tasks:
                        task.id = None
                        task.parent_item_part_id = part.id
                        self.insert_part_task(task)
                item.active_part = item.parts[-1]
                item.sync_output_from_parts()
                self.update_item(item)
        else:
            # A duplicated/imported legacy Chat item can still arrive with old
            # persisted part IDs. Keep its in-memory graph usable, but detach it
            # from those DB rows so later runtime updates cannot modify the source
            # conversation or create new partial/task records.
            for part in item.parts or []:
                part.id = None
                part.parent_item_id = item.id
                for task in part.tasks or []:
                    task.id = None
                    task.parent_item_part_id = None
            item.active_part = item.parts[-1] if item.parts else None
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
                hidden_input = :hidden_input,
                hidden_output = :hidden_output,
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
                additional_ctx_json = :additional_ctx_json,
                extra = :extra,
                input_tokens = :input_tokens,
                output_tokens = :output_tokens,
                total_tokens = :total_tokens,
                is_internal = :is_internal,
                docs_json = :docs_json,
                audio_id = :audio_id,
                audio_expires_ts = :audio_expires_ts
            WHERE id = :id
        """).bindparams(
            id=item.id,
            input=item.input,
            output=self.window.core.command.output_for_storage(item.output),
            input_name=item.input_name,
            output_name=item.output_name,
            input_ts=int(item.input_timestamp or 0),
            output_ts=int(item.output_timestamp or 0),
            hidden_input=item.hidden_input,
            hidden_output=item.hidden_output,
            mode=item.mode,
            model=item.model,
            thread_id=item.thread,
            msg_id=item.msg_id,
            run_id=item.run_id,
            cmds_json=pack_item_value(self.window.core.command.commands_for_storage(item.cmds)),
            results_json=pack_item_value(self.window.core.command.tool_results_for_storage(item.results)),
            urls_json=pack_item_value(item.urls),
            images_json=self._pack_ctx_images(item),
            files_json=pack_item_value(item.files),
            attachments_json=pack_item_value(item.attachments),
            additional_ctx_json=pack_item_value(item.additional_ctx),
            extra=pack_item_value(self.window.core.command.extra_for_storage(item.extra)),
            input_tokens=int(item.input_tokens or 0),
            output_tokens=int(item.output_tokens or 0),
            total_tokens=int(item.total_tokens or 0),
            is_internal=int(item.internal or 0),
            docs_json=pack_item_value(item.doc_ids),
            audio_id=item.audio_id,
            audio_expires_ts=int(item.audio_expires_ts or 0)
        )
        with db.begin() as conn:
            conn.execute(stmt)
        return True

    def get_ctx_count_by_day(
            self,
            year: int,
            month: Optional[int] = None,
            day: Optional[int] = None,
            search_string: Optional[str] = None,
            filters: Optional[dict] = None,
            search_content: bool = False,
    ) -> Dict[str, int]:
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

        offset_seconds = get_tz_offset()
        offset_suffix = ""
        if offset_seconds > 0:
            offset_suffix = f" + {offset_seconds}"
        elif offset_seconds < 0:
            offset_suffix = f" - {abs(offset_seconds)}"

        db = self.window.core.db.get_db()
        with db.connect() as conn:
            # by day
            if year and month and day:
                bind_params['start_ts'] = int(datetime(year, month, day, 0, 0, 0).timestamp()) + offset_seconds
                bind_params['end_ts'] = int(datetime(year, month, day, 23, 59, 59).timestamp()) + offset_seconds
                stmt_text = f"""
                    SELECT
                        date(datetime(m.updated_ts{offset_suffix}, 'unixepoch')) as day,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.parent_id IS NULL AND m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY day
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                return {row._mapping['day']: row._mapping['count'] for row in result}

            # by year and month
            elif year and month:
                start_timestamp, end_timestamp = get_month_start_end_timestamps(year, month)
                bind_params['start_ts'] = start_timestamp
                bind_params['end_ts'] = end_timestamp
                stmt_text = f"""
                    SELECT
                        date(datetime(m.updated_ts{offset_suffix}, 'unixepoch')) as day,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.parent_id IS NULL AND m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY day
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                return {row._mapping['day']: row._mapping['count'] for row in result}

            # by year (return months, not days)
            elif year:
                start_timestamp, end_timestamp = get_year_start_end_timestamps(year)
                bind_params['start_ts'] = start_timestamp + offset_seconds
                bind_params['end_ts'] = end_timestamp + offset_seconds
                stmt_text = f"""
                    SELECT
                        strftime('%m', datetime(m.updated_ts{offset_suffix}, 'unixepoch')) as month,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.parent_id IS NULL AND m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY month
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                return {row._mapping['month']: row._mapping['count'] for row in result}

    def get_ctx_labels_count_by_day(
            self,
            year: int,
            month: Optional[int] = None,
            day: Optional[int] = None,
            search_string: Optional[str] = None,
            filters: Optional[dict] = None,
            search_content: bool = False,
    ) -> Dict[str, Dict[int, int]]:
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

        offset_seconds = get_tz_offset()
        offset_suffix = ""
        if offset_seconds > 0:
            offset_suffix = f" + {offset_seconds}"
        elif offset_seconds < 0:
            offset_suffix = f" - {abs(offset_seconds)}"

        db = self.window.core.db.get_db()
        with db.connect() as conn:
            # by day
            if year and month and day:
                bind_params['start_ts'] = int(datetime(year, month, day, 0, 0, 0).timestamp()) + offset_seconds
                bind_params['end_ts'] = int(datetime(year, month, day, 23, 59, 59).timestamp()) + offset_seconds
                stmt_text = f"""
                    SELECT
                        date(datetime(m.updated_ts{offset_suffix}, 'unixepoch')) as day,
                        label,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.parent_id IS NULL AND m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY day, label
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                result_dict = {}
                for row in result:
                    day = row._mapping['day']
                    label = row._mapping['label']
                    count = row._mapping['count']

                    if day not in result_dict:
                        result_dict[day] = {}

                    result_dict[day][label] = count

                return result_dict

            # by year and month
            elif year and month:
                start_timestamp, end_timestamp = get_month_start_end_timestamps(year, month)
                bind_params['start_ts'] = start_timestamp
                bind_params['end_ts'] = end_timestamp
                stmt_text = f"""
                    SELECT
                        date(datetime(m.updated_ts{offset_suffix}, 'unixepoch')) as day,
                        label,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.parent_id IS NULL AND m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY day, label
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                result_dict = {}
                for row in result:
                    day = row._mapping['day']
                    label = row._mapping['label']
                    count = row._mapping['count']

                    if day not in result_dict:
                        result_dict[day] = {}

                    result_dict[day][label] = count

                return result_dict

            # by year (return months, not days)
            elif year:
                start_timestamp, end_timestamp = get_year_start_end_timestamps(year)
                bind_params['start_ts'] = start_timestamp + offset_seconds
                bind_params['end_ts'] = end_timestamp + offset_seconds
                stmt_text = f"""
                    SELECT
                        strftime('%m', datetime(m.updated_ts{offset_suffix}, 'unixepoch')) as month,
                        label,
                        COUNT(m.updated_ts) as count
                    FROM ctx_meta m
                    {join_statement}
                    WHERE (m.parent_id IS NULL AND m.updated_ts BETWEEN :start_ts AND :end_ts) {where_statement}
                    GROUP BY month, label
                """
                stmt = text(stmt_text).bindparams(**bind_params)
                result = conn.execute(stmt)
                result_dict = {}
                for row in result:
                    day = row._mapping['month']
                    label = row._mapping['label']
                    count = row._mapping['count']

                    if day not in result_dict:
                        result_dict[day] = {}

                    result_dict[day][label] = count

                return result_dict

    def get_groups(self) -> Dict[int, CtxGroup]:
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
        Delete ctx group by ID.

        When ``all`` is True, remove every ctx_item belonging to the group's
        contexts before deleting ctx_meta rows. This avoids orphaned message
        rows regardless of SQLite foreign-key mode.
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            if all:
                conn.execute(text("""
                    DELETE FROM ctx_item
                    WHERE meta_id IN (
                        SELECT id FROM ctx_meta WHERE group_id = :id
                    )
                """).bindparams(id=id))
                conn.execute(text("""
                    DELETE FROM memory_ctx
                    WHERE meta_id IN (
                        SELECT id FROM ctx_meta WHERE group_id = :id
                    )
                """).bindparams(id=id))
                conn.execute(text("DELETE FROM ctx_meta WHERE group_id = :id").bindparams(id=id))
            else:
                conn.execute(text("""
                    UPDATE ctx_meta
                    SET group_id = NULL
                    WHERE group_id = :id
                """).bindparams(id=id))
            conn.execute(text("DELETE FROM ctx_group WHERE id = :id").bindparams(id=id))
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

    def clear_meta(self, meta_id: int) -> bool:
        """
        Delete all items with meta ID

        :param meta_id: meta ID
        :return: True if cleared
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM ctx_item WHERE meta_id = :meta_id").bindparams(meta_id=meta_id))
            # Clearing a conversation must also clear its compact continuation
            # state; otherwise the next message in the empty chat would inherit
            # facts from content the user explicitly removed.
            conn.execute(text("DELETE FROM memory_ctx WHERE meta_id = :meta_id").bindparams(meta_id=meta_id))
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
                extra_json = :extra_json,
                updated_ts = :updated_ts
            WHERE id = :id
        """).bindparams(
            id=id,
            name=group.name,
            extra_json=pack_item_value(group.extra),
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
                name,
                extra_json
            )
            VALUES 
            (
                :uuid,
                :created_ts,
                :updated_ts,
                :name,
                :extra_json
            )
        """).bindparams(
            uuid=group.uuid,
            created_ts=int(group.created or 0),
            updated_ts=int(group.updated or 0),
            name=group.name,
            extra_json=pack_item_value(group.extra),
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            group.id = result.lastrowid
            return group.id

    def update_meta_group_id(self, meta_id: int, group_id: int = None) -> bool:
        """
        Update meta group ID

        :param meta_id: ctx meta ID
        :param group_id: ctx group ID
        :return: True if updated
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
