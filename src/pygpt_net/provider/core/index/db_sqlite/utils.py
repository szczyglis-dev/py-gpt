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

def unpack_file_item(row: dict) -> (str, dict):
    """
    Unpack item from DB row

    :param row: DB row
    :return: idx, file data
    """
    data = {}
    idx = row['idx']
    data["db_id"] = int(row['id'])
    data["id"] = row['doc_id']
    data["name"] = row['name']
    data["path"] = row['path']
    data["indexed_ts"] = int(row['updated_ts'] or 0)
    return idx, data
