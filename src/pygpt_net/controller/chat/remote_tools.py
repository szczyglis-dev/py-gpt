#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.04 19:00:00                  #
# ================================================== #

from typing import Union

from pygpt_net.item.model import ModelItem


class RemoteTools:
    def __init__(self, window=None):
        """
        Remote tools controller

        :param window: Window instance
        """
        self.window = window
        self.enabled_global = {
            "web_search": False,
        }

    def setup(self):
        """
        Setup remote tools

        :return: None
        """
        cfg_get = self.window.core.config.get
        self.enabled_global["web_search"] = cfg_get("remote_tools.global.web_search", False)
        self.update_icons()

    def enabled(self, model: Union[ModelItem, str], tool_name: str) -> bool:
        """
        Check if remote tool is enabled

        :param model: ModelItem or model name
        :param tool_name: Tool name
        :return: True if enabled, False otherwise
        """
        if isinstance(model, str):
            model = self.window.core.models.get(model)
        if not model:
            return False
        if tool_name == "web_search":
            return self.is_web(model)
        return False

    def is_web(self, model: ModelItem) -> bool:
        """
        Check if web search is enabled for the given provider

        :param model: ModelItem
        :return: True if web search is enabled, False otherwise
        """
        # at first, check provider-specific config
        cfg_get = self.window.core.config.get
        state = False
        if model.provider == "openai":  # native SDK, responses API
            state = cfg_get("remote_tools.web_search", False)
        elif model.provider == "google":  # native SDK
            state = cfg_get("remote_tools.google.web_search", False)
        elif model.provider == "anthropic":  # native SDK
            state = cfg_get("remote_tools.anthropic.web_search", False)
        elif model.provider == "x_ai":  # native SDK
            state = cfg_get("remote_tools.xai.web_search", False)

        # if not enabled by default or other provider, then use global config
        if not state:
            state = self.enabled_global["web_search"]

        return state

    def update_icons(self):
        """
        Update remote tools icons in chat tabs
        """
        state = self.enabled_global["web_search"]
        if state:
            self.window.ui.nodes['input'].set_icon_state("web", True)
            # self.window.ui.nodes['icon.remote_tool.web'].set_icon(":/icons/web_on.svg")
        else:
            self.window.ui.nodes['input'].set_icon_state("web", False)
            # self.window.ui.nodes['icon.remote_tool.web'].set_icon(":/icons/web_off.svg")

    def toggle(self, tool_name: str):
        """
        Toggle remote tool (for global toggle button)

        :param tool_name: Tool name
        """
        cfg_set = self.window.core.config.set

        # tool: web search
        if tool_name == "web_search":
            state = not self.enabled_global["web_search"]
            self.enabled_global["web_search"] = state
            cfg_set("remote_tools.global.web_search", state)
            cfg_set("remote_tools.web_search", state)
            cfg_set("remote_tools.google.web_search", state)
            cfg_set("remote_tools.anthropic.web_search", state)
            cfg_set("remote_tools.xai.web_search", state)

        # save config
        self.window.core.config.save()
        self.update_icons()
