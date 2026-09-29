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

FORGE_DEFAULT_BASE_URL = "https://api.forge.tensorblock.co/v1"


def setup() -> dict:
    return {
        "settings": {
            "api_key": {
                "type": "str",
                "default": "",
                "secret": True,
                "env": ["FORGE_API_KEY"],
            },
            "api_base": {
                "type": "str",
                "default": FORGE_DEFAULT_BASE_URL,
                "env": ["FORGE_API_BASE"],
            },
        }
    }
