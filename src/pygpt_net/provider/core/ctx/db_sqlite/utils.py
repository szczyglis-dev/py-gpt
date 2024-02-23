#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 01:00:00                  #
# ================================================== #

import json
import re
from datetime import datetime, timedelta, timezone

from pygpt_net.item.ctx import CtxMeta, CtxItem


def search_by_date_string(search_string: str) -> list:
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
            start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            # Add one day and subtract one second to include the end date entirely
            end_ts += (24 * 60 * 60) - 1
            date_ranges.append((start_ts, end_ts))
        elif start_date_str and sep:
            # search from date to infinity
            start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            end_of_day_ts = None
            date_ranges.append((start_ts, end_of_day_ts))
        elif end_date_str and sep:
            # search from beginning of time to date
            end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            # Add one day and subtract one second to include the end date entirely
            end_ts += (24 * 60 * 60) - 1
            date_ranges.append((None, end_ts))
        elif start_date_str:
            # search in exact day
            start_ts = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            # Add one day and subtract one second to include the entire day
            end_of_day_ts = start_ts + (24 * 60 * 60) - 1
            date_ranges.append((start_ts, end_of_day_ts))
        elif end_date_str:
            # search in exact day
            end_ts = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            # Add one day and subtract one second to include the entire day
            end_ts += (24 * 60 * 60) - 1
            date_ranges.append((0, end_ts))

    return date_ranges


def get_month_start_end_timestamps(year: int, month: int) -> (int, int):
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


def get_year_start_end_timestamps(year: int) -> (int, int):
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


def pack_item_value(value: any) -> str:
    """
    Pack item value to JSON

    :param value: Value to pack
    :return: JSON string or value itself
    """
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def unpack_item_value(value: any) -> any:
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


def unpack_item(item: CtxItem, row: dict) -> CtxItem:
    """
    Unpack context item from DB row

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
    item.cmds = unpack_item_value(row['cmds_json'])
    item.results = unpack_item_value(row['results_json'])
    item.urls = unpack_item_value(row['urls_json'])
    item.images = unpack_item_value(row['images_json'])
    item.files = unpack_item_value(row['files_json'])
    item.attachments = unpack_item_value(row['attachments_json'])
    item.extra = unpack_item_value(row['extra'])
    item.input_tokens = int(row['input_tokens'] or 0)
    item.output_tokens = int(row['output_tokens'] or 0)
    item.total_tokens = int(row['total_tokens'] or 0)
    item.internal = bool(row['is_internal'])
    return item


def unpack_meta(meta: CtxMeta, row: dict) -> CtxMeta:
    """
    Unpack context meta data from DB row

    :param meta: Context meta (CtxMeta)
    :param row: DB row
    :return: context meta
    """
    meta.id = int(row['id'])
    meta.external_id = row['external_id']
    meta.uuid = row['uuid']
    meta.created = int(row['created_ts'])
    meta.updated = int(row['updated_ts'])
    meta.indexed = int(row['indexed_ts'])
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
    meta.indexes = unpack_item_value(row['indexes_json'])
    return meta
