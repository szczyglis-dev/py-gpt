#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

import json

from pygpt_net.utils import unpack_var
from pygpt_net.item.assistant import AssistantStoreItem


def unpack_store(store: AssistantStoreItem, row: dict) -> AssistantStoreItem:
    """
    Unpack store item from DB row

    :param store: store item (AssistantStoreItem)
    :param row: DB row
    :return: store item
    """
    store.id = row['store_id']
    store.record_id = unpack_var(row['id'], "int")
    store.uuid = row['uuid']
    store.created = unpack_var(row['created_ts'], "int")
    store.updated = unpack_var(row['updated_ts'], "int")
    store.last_active = unpack_var(row['last_active_ts'], "int")
    store.last_sync = unpack_var(row['last_sync_ts'], "int")
    store.name = row['name']
    store.description = row['description']
    store.expire_days = unpack_var(row['expire_days'], "int")
    store.usage_bytes = unpack_var(row['usage_bytes'], "int")
    store.num_files = unpack_var(row['num_files'], "int")
    store.last_status = row['status']
    store.status = unpack_item_value(row['status_json'])
    store.is_thread = unpack_var(row['is_thread'], "bool")
    return store

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