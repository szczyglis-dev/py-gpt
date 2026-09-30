#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.30 08:14:00                  #
# ================================================== #

def setup() -> dict:
    return {
        "openai_compatible": True,
        "settings": {
            "api_key": {
                "type": "str",
                "default": "",
                "secret": True,
                "urls": {"API Keys": "https://www.perplexity.ai/account/api/keys"},
            },
            "api_base": {
                "type": "str",
                "default": "https://api.perplexity.ai",
            },
        }
    }
