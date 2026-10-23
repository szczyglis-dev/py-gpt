#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.22 12:00:00                  #
# ================================================== #

def setup() -> dict:
    return {
        "openai_compatible": True,
        "settings": {
            "api_key": {
                "type": "str",
                "default": "",
                "secret": True,
                "urls": {"API Keys": "https://cheaperinference.com/signup"},
            },
            "api_base": {
                "type": "str",
                "default": "https://api.cheaperinference.com/v1",
            },
        }
    }
