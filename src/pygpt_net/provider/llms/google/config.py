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
                "type": "str", "default": "", "secret": True,
                "urls": {"API Keys": "https://aistudio.google.com/app/apikey"},
            },
            "api_base": {"type": "str", "default": "https://generativelanguage.googleapis.com/v1beta/openai"},
            "extra": {
                "native": {
                    "type": "bool", "default": True,
                    "label": "settings.api_native_google",
                    "desc": "settings.api_native_google.desc",
                    "use_locale": True,
                },
                "use_vertex": {
                    "type": "bool", "default": False,
                    "label": "settings.api_native_google.use_vertex",
                    "desc": "settings.api_native_google.use_vertex.desc",
                    "use_locale": True, "advanced": True,
                },
                "cloud_project": {
                    "type": "str", "default": "",
                    "label": "settings.api_native_google.cloud_project",
                    "desc": "settings.api_native_google.cloud_project.desc",
                    "use_locale": True, "advanced": True,
                },
                "cloud_location": {
                    "type": "str", "default": "us-central1",
                    "label": "settings.api_native_google.cloud_location",
                    "desc": "settings.api_native_google.cloud_location.desc",
                    "use_locale": True, "advanced": True,
                },
                "app_credentials": {
                    "type": "str", "default": "",
                    "label": "settings.api_native_google.app_credentials",
                    "desc": "settings.api_native_google.app_credentials.desc",
                    "use_locale": True, "advanced": True,
                },
            },
        },
        "remote_tools": {
            "web_search": {
                "unsupported_prefixes": ['gemini-1.0', 'models/gemini-1.0'],
                "unsupported_models": [],
                "type": "bool",
                "label": "settings.remote_tools.google.web_search",
                "default": True,
                "desc": "settings.remote_tools.google.web_search.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.web_search",
                "tool": True,
            },
            "maps": {
                "type": "bool",
                "label": "settings.remote_tools.google.maps",
                "default": False,
                "desc": "settings.remote_tools.google.maps.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.maps",
                "tool": True,
            },
            "code_interpreter": {
                "type": "bool",
                "label": "settings.remote_tools.google.code_interpreter",
                "default": False,
                "desc": "settings.remote_tools.google.code_interpreter.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.code_interpreter",
                "tool": True,
            },
            "url_ctx": {
                "type": "bool",
                "label": "settings.remote_tools.google.url_ctx",
                "default": False,
                "desc": "settings.remote_tools.google.url_ctx.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.url_ctx",
                "tool": True,
            },
            "file_search": {
                "type": "bool",
                "label": "settings.remote_tools.google.file_search",
                "default": False,
                "desc": "settings.remote_tools.google.file_search.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.file_search",
                "tool": True,
            },
            "file_search.args": {
                "type": "text",
                "label": "settings.remote_tools.google.file_search.args",
                "urls": {
                    "Google Docs": "https://ai.google.dev/gemini-api/docs/file-search",
                },
                "default": "",
                "desc": "settings.remote_tools.google.file_search.args.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.file_search.args",
            },
            "mcp": {
                "type": "bool",
                "label": "settings.remote_tools.google.mcp",
                "default": False,
                "desc": "settings.remote_tools.google.mcp.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.mcp",
                "tool": True,
            },
            "mcp.args": {
                "type": "textarea",
                "label": "settings.remote_tools.google.mcp.args",
                "urls": {
                    "Google Docs": "https://ai.google.dev/gemini-api/docs/function-calling#remote_mcp",
                },
                "default": "[\n    {\n        \"type\": \"mcp_server\",\n        \"name\": \"deepwiki\",\n        \"url\": \"https://mcp.deepwiki.com/mcp\",\n        \"headers\": {},\n        \"allowed_tools\": [\"ask_question\"]\n    }\n]",
                "desc": "settings.remote_tools.google.mcp.args.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.mcp.args",
            },
            "computer_use": {
                "type": "bool",
                "label": "settings.remote_tools.google.computer_use",
                "urls": {
                    "Google Docs": "https://ai.google.dev/gemini-api/docs/computer-use",
                },
                "default": False,
                "desc": "settings.remote_tools.google.computer_use.desc",
                "use_locale": True,
                "legacy_key": "remote_tools.google.computer_use",
                "tool": True,
            },
        },
    }
