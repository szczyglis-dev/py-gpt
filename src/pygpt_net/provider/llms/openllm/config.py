#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

# Default: local OpenLLM daemon. For the hosted endpoint use
# https://www.openllm.sh/v1 together with an OpenLLM API key.
OPENLLM_DEFAULT_BASE_URL = "http://127.0.0.1:8787/v1"

# The OpenAI SDK rejects an empty key. The local daemon ignores any bearer that
# does not start with "sk-llm-" and uses the saved OpenLLM login instead.
OPENLLM_KEYLESS_PLACEHOLDER = "openllm"


def setup() -> dict:
    return {
        "openai_compatible": True,
        # The local daemon uses the saved OpenLLM login, so the key is optional.
        "require_api_key": False,
        "settings": {
            "api_key": {
                "type": "str",
                "default": "",
                "secret": True,
                "env": ["OPENLLM_API_KEY"],
                "urls": {"API Keys": "https://www.openllm.sh/sign-in"},
            },
            "api_base": {
                "type": "str",
                "default": OPENLLM_DEFAULT_BASE_URL,
            },
        }
    }
