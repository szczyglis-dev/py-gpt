#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from pygpt_net.provider.llms.base import BaseLLM


def setup() -> dict:
    return {
        "settings": {
            "api_key": {
                "type": "str",
                "default": "",
                "secret": True,
                "urls": {"API Keys": "https://dashboard.voyageai.com/organization/api-keys"},
            },
        }
    }


class VoyageConfigLLM(BaseLLM):
    """Configuration-only provider for Voyage embedding credentials."""

    def __init__(self, *args, **kwargs):
        super(VoyageConfigLLM, self).__init__(*args, **kwargs)
        self.id = "voyage"
        self.name = "Voyage"
        self.type = []

    def setup(self) -> dict:
        return setup()
