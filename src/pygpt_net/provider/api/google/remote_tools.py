#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 16:40:00                  #
# ================================================== #

import json

from google.genai import types as gtypes

from pygpt_net.core.types import MODE_COMPUTER
from pygpt_net.item.model import ModelItem


class RemoteTools:
    # Models supported by the Generate Content Computer Use API used by this adapter.
    COMPUTER_USE_MODELS = {
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
        "gemini-2.5-computer-use-preview-10-2025",
    }

    def __init__(self, window=None):
        """
        Remote Tools helpers for Google GenAI.

        :param window: Window instance
        """
        self.window = window

    def supports_computer_use(self, model: ModelItem = None) -> bool:
        """Return True for known models or models advertising Computer mode."""
        model_id = str(getattr(model, "id", "") or "").lower()
        if model_id.startswith("models/"):
            model_id = model_id[7:]
        if model_id in self.COMPUTER_USE_MODELS:
            return True
        return bool(model and model.has_mode(MODE_COMPUTER))

    def is_computer_use_enabled(self, model: ModelItem = None) -> bool:
        """Return True when Computer Use is enabled as a Google remote tool."""
        return bool(
            self.window.core.config.get("remote_tools.google.computer_use", False)
            and self.supports_computer_use(model)
        )


    def build_interactions_mcp_tools(self, model: ModelItem = None) -> list:
        """
        Build Remote MCP server definitions for the Google Interactions API.

        Google Remote MCP is an Interactions API feature and accepts MCP servers
        as dictionaries with ``type=mcp_server``. Only Streamable HTTP servers
        are supported by the API (SSE endpoints are not supported).

        The config value may contain either one JSON object or a JSON array.
        Invalid entries are ignored so an optional MCP configuration cannot break
        the whole Google request.

        :param model: ModelItem
        :return: list of Interactions API MCP server definitions
        """
        cfg = self.window.core.config
        if not cfg.get("remote_tools.google.mcp", False):
            return []

        # Google currently excludes Gemini 3 family models from Remote MCP in
        # Interactions API. Agent IDs (e.g. Deep Research) are not filtered here.
        model_id = str(getattr(model, "id", "") or "").lower()
        if model_id.startswith("models/"):
            model_id = model_id[7:]
        if model_id.startswith("gemini-3"):
            return []

        raw = cfg.get("remote_tools.google.mcp.args", "")
        if not raw:
            return []

        try:
            parsed = raw if isinstance(raw, (dict, list)) else json.loads(str(raw))
        except Exception as e:
            self.window.core.debug.log(e)
            return []

        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return []

        tools = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            tool = dict(item)
            tool_type = str(tool.get("type", "mcp_server") or "mcp_server")
            if tool_type != "mcp_server":
                continue
            tool["type"] = "mcp_server"

            # The API requires snake_case-like names and rejects '-' in names.
            name = tool.get("name")
            if isinstance(name, str) and "-" in name:
                tool["name"] = name.replace("-", "_")

            # A remote server without an endpoint is not useful to PyGPT.
            url = tool.get("url")
            if not isinstance(url, str) or not url.strip():
                continue
            tool["url"] = url.strip()

            headers = tool.get("headers")
            if headers is not None and not isinstance(headers, dict):
                tool.pop("headers", None)

            allowed_tools = tool.get("allowed_tools")
            if allowed_tools is not None and not isinstance(allowed_tools, list):
                tool.pop("allowed_tools", None)

            tools.append(tool)

        return tools

    def build_remote_tools(self, model: ModelItem = None) -> list:
        """
        Build Google GenAI remote tools based on config flags.
        - remote_tools.google.web_search: enables grounding via Google Search (Gemini 2.x)
          or GoogleSearchRetrieval (Gemini 1.5 fallback).
        - remote_tools.google.code_interpreter: enables code execution tool.

        Returns a list of gtypes.Tool objects (can be empty).

        :param model: ModelItem
        :return: list of gtypes.Tool
        """
        tools: list = []
        cfg = self.window.core.config
        model_id = (model.id if model and getattr(model, "id", None) else "").lower()
        is_web = self.window.controller.chat.remote_tools.enabled(model, "web_search")  # get global config

        # Google Search tool
        if is_web and "image" not in model.id:
            try:
                if not model_id.startswith("gemini-1.5") and not model_id.startswith("models/gemini-1.5"):
                    # Gemini 2.x uses GoogleSearch
                    tools.append(gtypes.Tool(google_search=gtypes.GoogleSearch()))
                else:
                    # Gemini 1.5 fallback uses GoogleSearchRetrieval
                    # Note: Supported only for 1.5 models.
                    tools.append(gtypes.Tool(
                        google_search_retrieval=gtypes.GoogleSearchRetrieval()
                    ))
            except Exception as e:
                # Do not break the request if tool construction fails
                self.window.core.debug.log(e)

        # Code Execution tool
        if cfg.get("remote_tools.google.code_interpreter") and "image" not in model.id:
            try:
                tools.append(gtypes.Tool(code_execution=gtypes.ToolCodeExecution))
            except Exception as e:
                self.window.core.debug.log(e)

        # URL Context tool
        if cfg.get("remote_tools.google.url_ctx") and "image" not in model.id:
            try:
                # Supported on Gemini 2.x+ models (not on 1.5)
                if not model_id.startswith("gemini-1.5") and not model_id.startswith("models/gemini-1.5"):
                    tools.append(gtypes.Tool(url_context=gtypes.UrlContext))
            except Exception as e:
                self.window.core.debug.log(e)

        # Google Maps
        if cfg.get("remote_tools.google.maps") and "image" not in model.id:
            try:
                tools.append(gtypes.Tool(google_maps=gtypes.GoogleMaps()))
            except Exception as e:
                self.window.core.debug.log(e)

        # Computer Use. Chat.send keeps it exclusive because the current GenAI
        # Computer Use flow in PyGPT must not be combined with function declarations.
        if self.is_computer_use_enabled(model) and "image" not in model.id:
            try:
                tools.append(self.window.core.api.google.computer.get_tool())
            except Exception as e:
                self.window.core.debug.log(e)

        # File search
        if cfg.get("remote_tools.google.file_search") and "image" not in model.id:
            store_ids = cfg.get("remote_tools.google.file_search.args", "")
            file_search_store_names = [s.strip() for s in store_ids.split(",") if s.strip()]
            try:
                tools.append(gtypes.Tool(file_search=gtypes.FileSearch(
                    file_search_store_names=file_search_store_names,
                )))
            except Exception as e:
                self.window.core.debug.log(e)

        return tools