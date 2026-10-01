#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 14:42:00                  #
# ================================================== #

def setup() -> dict:
    return {
        "require_api_key": False,
        "settings": {
            "api_key": {"type": "str", "default": "", "secret": True},
            "api_base": {"type": "str", "default": ""},
        },
    }
