#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from pygpt_net.provider.llms.base import BaseLLM


class JevConfigLLM(BaseLLM):
    """Configuration-only provider for Jev / System One credentials."""

    def __init__(self, *args, **kwargs):
        super(JevConfigLLM, self).__init__(*args, **kwargs)
        self.id = "jev"
        self.name = "Jev / System One"
        self.type = []

    def setup(self) -> dict:
        return {
            "settings": {
                "api_key": {
                    "type": "str",
                    "default": "",
                    "secret": True,
                    "urls": {"API Keys": "https://console.typesafe.ai/keys"},
                },
                "api_base": {
                    "type": "str",
                    "default": "https://api.typesafe.ai",
                },
            }
        }
