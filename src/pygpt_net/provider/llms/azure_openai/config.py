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
            "api_key": {"type": "str", "default": "", "secret": True},
            "api_base": {"type": "str", "default": "https://<your-resource-name>.openai.azure.com/"},
            "extra": {
                "api_version": {
                    "type": "str",
                    "default": "2023-07-01-preview",
                    "label": "settings.api_azure_version",
                    "desc": "settings.api_azure_version.desc",
                    "use_locale": True,
                },
            },
        }
    }
