#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 19:00:00                  #
# ================================================== #

from google.genai import types as gtypes

from pygpt_net.item.model import ModelItem


class RemoteTools:
    def __init__(self, window=None):
        """
        Remote Tools helpers for Google GenAI.

        :param window: Window instance
        """
        self.window = window

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