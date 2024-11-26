#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 19:00:00                  #
# ================================================== #

import re


def sanitize_name(name: str) -> str:
    """
    Sanitize name

    :param name: name
    :return: sanitized name
    """
    if name is None:
        return ""
    # allowed characters: a-z, A-Z, 0-9, _, and -
    name = name.strip().lower()
    sanitized_name = re.sub(r'[^a-z0-9_-]', '_', name)
    return sanitized_name[:64]  # limit to 64 characters