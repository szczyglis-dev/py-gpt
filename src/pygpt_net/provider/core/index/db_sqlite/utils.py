#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from typing import Tuple, Dict, Any

from pygpt_net.utils import unpack_var


def unpack_file_item(row: Dict[str, Any]) -> Tuple[str, dict]:
    """
    Unpack item from DB row

    :param row: DB row
    :return: idx, file data
    """
    data = {}
    idx = row['idx']
    data["db_id"] = unpack_var(row['id'], 'int')
    data["id"] = row['doc_id']
    data["name"] = row['name']
    data["path"] = row['path']
    data["indexed_ts"] = unpack_var(row['updated_ts'], 'int')
    return idx, data
