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
from pygpt_net.item.assistant import AssistantFileItem


def unpack_file(file: AssistantFileItem, row: dict) -> AssistantFileItem:
    """
    Unpack file item from DB row

    :param file: file item (AssistantStoreItem)
    :param row: DB row
    :return: store item
    """
    file.id = unpack_var(row['id'], "int")
    file.record_id = unpack_var(row['id'], "int")
    file.uuid = row['uuid']
    file.created = unpack_var(row['created_ts'], "int")
    file.updated = unpack_var(row['updated_ts'], "int")
    file.size = unpack_var(row['size'], "int")
    file.name = row['name']
    file.path = row['path']
    file.file_id = row['file_id']
    file.store_id = row['store_id']
    file.thread_id = row['thread_id']
    return file

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