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
        "settings": {
            "api_key": {
                "type": "str",
                "default": "",
                "secret": True,
                "urls": {"API Keys": "https://platform.openai.com/account/api-keys"},
            },
            "api_base": {
                "type": "str",
                "default": "https://api.openai.com/v1",
            },
            "extra": {
                "organization": {
                    "type": "str",
                    "default": "",
                    "label": "settings.organization_key",
                    "desc": "settings.organization_key.desc",
                    "use_locale": True,
                    "secret": True,
                },
                "responses_api": {
                    "type": "bool",
                    "default": True,
                    "label": "settings.api_use_responses",
                    "desc": "settings.api_use_responses.desc",
                    "use_locale": True,
                    "advanced": True,
                },
                "responses_api_llama": {
                    "type": "bool",
                    "default": True,
                    "label": "settings.api_use_responses_llama",
                    "desc": "settings.api_use_responses_llama.desc",
                    "use_locale": True,
                    "advanced": True,
                },
            },
        },
        "remote_tools": {
            "web_search": {
                "unsupported_prefixes": ['gpt-3.5-', 'gpt-4-', 'o1', 'o3'],
                "unsupported_models": ['gpt-4', 'codex-mini-latest'],
                "type": "bool",
                "label": "settings.remote_tools.web_search",
                "default": True,
                "desc": "settings.remote_tools.web_search.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.web_search",
                "tool": True,
                "choice_label": "remote_tool.openai.web_search",
            },
            "image": {
                "type": "bool",
                "label": "settings.remote_tools.image",
                "default": False,
                "desc": "settings.remote_tools.image.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.image",
                "tool": True,
                "choice_label": "remote_tool.openai.image",
            },
            "code_interpreter": {
                "type": "bool",
                "label": "settings.remote_tools.code_interpreter",
                "default": False,
                "desc": "settings.remote_tools.code_interpreter.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.code_interpreter",
                "tool": True,
                "choice_label": "remote_tool.openai.code_interpreter",
            },
            "mcp": {
                "type": "bool",
                "label": "settings.remote_tools.mcp",
                "default": False,
                "desc": "settings.remote_tools.mcp.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.mcp",
                "tool": True,
                "choice_label": "remote_tool.openai.mcp",
            },
            "mcp.args": {
                "type": "textarea",
                "label": "settings.remote_tools.mcp.args",
                "urls": {
                    "OpenAI Docs": "https://platform.openai.com/docs/guides/tools-remote-mcp",
                },
                "default": "{\n    \"type\": \"mcp\",\n    \"server_label\": \"deepwiki\",\n    \"server_url\": \"https://mcp.deepwiki.com/mcp\",\n    \"require_approval\": \"never\",\n    \"allowed_tools\": [\"ask_question\"]\n}",
                "desc": "settings.remote_tools.mcp.args.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.mcp.args",
            },
            "file_search": {
                "type": "bool",
                "label": "settings.remote_tools.file_search",
                "default": False,
                "desc": "settings.remote_tools.file_search.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.file_search",
                "tool": True,
                "choice_label": "remote_tool.openai.file_search",
            },
            "file_search.args": {
                "type": "text",
                "label": "settings.remote_tools.file_search.args",
                "urls": {
                    "OpenAI Docs": "https://platform.openai.com/docs/guides/tools-file-search",
                },
                "default": "",
                "desc": "settings.remote_tools.file_search.args.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.file_search.args",
            },
            "computer_use": {
                "type": "bool",
                "label": "settings.remote_tools.computer_use",
                "urls": {
                    "OpenAI Docs": "https://developers.openai.com/api/docs/guides/tools-computer-use",
                },
                "default": False,
                "desc": "settings.remote_tools.computer_use.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.computer_use",
                "tool": True,
                "choice_label": "remote_tool.openai.computer_use",
            },
        },
    }
