#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
# ================================================== #

import json
import re

from datetime import datetime, timedelta
from typing import List, Tuple, Any, Dict

from pygpt_net.item.ctx import CtxMeta, CtxItem, CtxGroup
from pygpt_net.item.ctx_part import CtxItemPart
from pygpt_net.item.ctx_part_task import CtxItemPartTask
from pygpt_net.utils import unpack_var


def search_by_date_string(search_string: str) -> List[Tuple[Any, Any]]:
    """
    Prepare date ranges from search string if @date() syntax is used

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
            # Add one day and subtract one second to include the end date entirely
            end_ts += (24 * 60 * 60) - 1
            date_ranges.append((start_ts, end_ts))
        elif start_date_str and sep:
            # search from date to infinity
            start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').timestamp()
            end_of_day_ts = None
            date_ranges.append((start_ts, end_of_day_ts))
        elif end_date_str and sep:
            # search from beginning of time to date
            end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').timestamp()
            # Add one day and subtract one second to include the end date entirely
            end_ts += (24 * 60 * 60) - 1
            date_ranges.append((None, end_ts))
        elif start_date_str:
            # search in exact day
            start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').timestamp()
            # Add one day and subtract one second to include the entire day
            end_of_day_ts = start_ts + (24 * 60 * 60) - 1
            date_ranges.append((start_ts, end_of_day_ts))
        elif end_date_str:
            # search in exact day
            end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').timestamp()
            # Add one day and subtract one second to include the entire day
            end_ts += (24 * 60 * 60) - 1
            date_ranges.append((0, end_ts))

    return date_ranges


def get_month_start_end_timestamps(year: int, month: int) -> Tuple[int, int]:
    """
    Get start and end timestamps for given month

    :param year: year
    :param month: month
    :return: start and end timestamps
    """
    start_date = datetime(year, month, 1)
    start_timestamp = int(start_date.timestamp())
    if month == 12:
        end_date = datetime(year+1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month+1, 1) - timedelta(seconds=1)
    end_timestamp = int(end_date.timestamp())
    return start_timestamp, end_timestamp


def get_year_start_end_timestamps(year: int) -> Tuple[int, int]:
    """
    Get start and end timestamps for given year

    :param year: year
    :return: start and end timestamps
    """
    start_date = datetime(year, 1, 1)
    start_timestamp = int(start_date.timestamp())
    end_date = datetime(year+1, 1, 1) - timedelta(seconds=1)
    end_timestamp = int(end_date.timestamp())
    return start_timestamp, end_timestamp


def pack_item_value(value: Any) -> str:
    """
    Pack item value to JSON

    :param value: Value to pack
    :return: JSON string or value itself
    """
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def unpack_item_value(value: Any) -> Any:
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


def unpack_item(
        item: CtxItem,
        row: Dict[str, Any]
) -> CtxItem:
    """
    Unpack context item from DB row

    :param item: Context item (CtxItem)
    :param row: DB row
    :return: context item
    """
    item.additional_ctx = unpack_item_value(row['additional_ctx_json'])
    item.attachments = unpack_item_value(row['attachments_json'])
    item.audio_expires_ts = row['audio_expires_ts']
    item.audio_id = row['audio_id']
    item.cmds = unpack_item_value(row['cmds_json'])
    item.doc_ids = unpack_item_value(row['docs_json'])
    item.external_id = row['external_id']
    item.extra = unpack_item_value(row['extra'])
    item.files = unpack_item_value(row['files_json'])
    item.id = unpack_var(row['id'], 'int')
    item.images = unpack_item_value(row['images_json'])
    item.input = row['input']
    item.input_name = row['input_name']
    item.input_timestamp = unpack_var(row['input_ts'], 'int')
    item.input_tokens = unpack_var(row['input_tokens'], 'int')
    item.internal = unpack_var(row['is_internal'], 'bool')
    item.meta_id = unpack_var(row['meta_id'], 'int')
    item.mode = row['mode']
    item.model = row['model']
    item.msg_id = row['msg_id']
    item.output = row['output']
    item.output_name = row['output_name']
    item.output_timestamp = unpack_var(row['output_ts'], 'int')
    item.output_tokens = unpack_var(row['output_tokens'], 'int')
    item.results = unpack_item_value(row['results_json'])
    item.run_id = row['run_id']
    item.thread = row['thread_id']
    item.total_tokens = unpack_var(row['total_tokens'], 'int')
    item.urls = unpack_item_value(row['urls_json'])

    # set defaults
    if item.cmds is None:
        item.cmds = []
    if item.results is None:
        item.results = []
    if item.urls is None:
        item.urls = []
    if item.images is None:
        item.images = []
    if item.files is None:
        item.files = []
    if item.attachments is None:
        item.attachments = []
    if item.additional_ctx is None:
        item.additional_ctx = []
    if item.doc_ids is None:
        item.doc_ids = []
    if item.extra is None:
        item.extra = {}
    return item



def unpack_part(part: CtxItemPart, row: Dict[str, Any], prefix: str = "") -> CtxItemPart:
    """Unpack a ctx_item_partial row. Prefix is used by JOIN queries."""
    get = lambda key, default=None: row.get(prefix + key, default)
    part.id = unpack_var(get('id'), 'int')
    part.uuid = get('uuid') or part.uuid
    part.parent_item_id = unpack_var(get('parent_item_id'), 'int')
    part.agent_id = get('agent_id')
    part.name = get('name')
    part.output = get('output')
    part.extra = unpack_item_value(get('extra_json')) or {}
    part.created_at = unpack_var(get('created_at'), 'int') or 0
    part.updated_at = unpack_var(get('updated_at'), 'int') or 0
    part.tasks = []
    return part


def unpack_part_task(task: CtxItemPartTask, row: Dict[str, Any], prefix: str = "") -> CtxItemPartTask:
    """Unpack a ctx_item_partial_task row. Prefix is used by JOIN queries."""
    get = lambda key, default=None: row.get(prefix + key, default)
    task.id = unpack_var(get('id'), 'int')
    task.uuid = get('uuid') or task.uuid
    task.parent_item_part_id = unpack_var(get('parent_item_part_id'), 'int')
    task.agent_id = get('agent_id')
    task.name = get('name')
    task.task_name = get('task_name')
    task.task_summary = get('task_summary')
    task.input = get('input')
    task.output = get('output')
    task.tool_call_id = get('tool_call_id')
    task.tool_input = unpack_item_value(get('tool_input_json'))
    task.tool_output = unpack_item_value(get('tool_output_json'))
    task.extra = unpack_item_value(get('extra_json')) or {}
    task.created_at = unpack_var(get('created_at'), 'int') or 0
    task.updated_at = unpack_var(get('updated_at'), 'int') or 0
    return task

def unpack_meta(
        meta: CtxMeta,
        row: Dict[str, Any]
) -> CtxMeta:
    """
    Unpack context meta-data from DB row

    :param meta: Context meta (CtxMeta)
    :param row: DB row
    :return: context meta
    """
    meta.additional_ctx = unpack_item_value(row['additional_ctx_json'])
    meta.archived = unpack_var(row['is_archived'], 'bool')
    meta.assistant = row['assistant_id']
    meta.created = unpack_var(row['created_ts'], 'int')
    meta.deleted = unpack_var(row['is_deleted'], 'bool')
    meta.external_id = row['external_id']
    meta.extra = row['extra']
    meta.group_id = unpack_var(row['group_id'], 'int')
    meta.id = unpack_var(row['id'], 'int')
    meta.indexed = unpack_var(row['indexed_ts'], 'int')
    meta.indexes = unpack_item_value(row['indexes_json'])
    meta.initialized = unpack_var(row['is_initialized'], 'bool')
    meta.important = unpack_var(row['is_important'], 'bool')
    meta.label = unpack_var(row['label'], 'int')
    meta.last_mode = row['last_mode']
    meta.last_model = row['last_model']
    meta.mode = row['mode']
    meta.model = row['model']
    meta.name = row['name']
    meta.preset = row['preset_id']
    meta.run = row['run_id']
    meta.status = row['status']
    meta.thread = row['thread_id']
    meta.updated = unpack_var(row['updated_ts'], 'int')
    meta.uuid = row['uuid']

    if meta.additional_ctx is None:
        meta.additional_ctx = []

    # add group if exists
    if meta.group_id:
        group = CtxGroup()
        group.id = meta.group_id
        group.uuid = row['group_uuid']
        group.name = row['group_name']
        group.additional_ctx = unpack_item_value(row['group_additional_ctx_json'])
        group.extra = unpack_item_value(row.get('group_extra_json')) or {}
        if group.additional_ctx is None:
            group.additional_ctx = []
        meta.group = group

    return meta


def unpack_group(
        group: CtxGroup,
        row: Dict[str, Any]
) -> CtxGroup:
    """
    Unpack context group data from DB row

    :param group: Context group (CtxGroup)
    :param row: DB row
    :return: context group
    """
    group.additional_ctx = unpack_item_value(row['additional_ctx_json'])
    group.created = unpack_var(row['created_ts'], 'int')
    group.extra = unpack_item_value(row.get('extra_json'))
    if group.extra is None:
        group.extra = {}
    group.id = unpack_var(row['id'], 'int')
    group.name = row['name']
    group.updated = unpack_var(row['updated_ts'], 'int')
    group.uuid = row['uuid']
    if group.additional_ctx is None:
        group.additional_ctx = []
    return group
