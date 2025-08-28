#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

import json

from pygpt_net.core.types import (
    MODE_COMPUTER,
    OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER,
    OPENAI_REMOTE_TOOL_DISABLE_COMPUTER_USE,
    OPENAI_REMOTE_TOOL_DISABLE_IMAGE,
    OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH,
    OPENAI_REMOTE_TOOL_DISABLE_FILE_SEARCH,
    OPENAI_REMOTE_TOOL_DISABLE_MCP,
)

from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem
from pygpt_net.utils import trans


class RemoteTools:

    REMOTE_TOOLS = [
        "web_search",
        "image",
        "code_interpreter",
        "mcp",
        "file_search",
        "computer_use",
    ]

    def __init__(self, window=None):
        """
        Remote tools

        :param window: Window instance
        """
        self.window = window

    def get_choices(self):
        """
        Return remote tools choices

        :return: List of remote tools
        """
        choices = []
        for tool in self.REMOTE_TOOLS:
            choices.append({
                tool: trans(f"remote_tool.openai.{tool}")
            })
        return choices

    def append_to_tools(
            self,
            mode: str,
            model: ModelItem,
            stream: bool,
            is_expert_call: bool,
            tools: list,
            preset: PresetItem = None
    ) -> list:
        """
        Prepare remote tools for the model

        :param mode: Agent mode
        :param model: Model item
        :param stream: Streaming flag
        :param is_expert_call: Is expert call
        :param tools: List of current tools
        :param preset: Preset item (optional, used for expert calls)
        :return: List of tools
        """
        # disabled by default
        enabled = {
            "web_search": False,
            "image": False,
            "code_interpreter": False,
            "mcp": False,
            "file_search": False,
            "computer_use": False,
        }

        # from global config if not expert call
        if not is_expert_call:
            enabled["web_search"] = self.window.core.config.get("remote_tools.web_search", False)
            enabled["image"] = self.window.core.config.get("remote_tools.image", False)
            enabled["code_interpreter"] = self.window.core.config.get("remote_tools.code_interpreter", False)
            enabled["mcp"] = self.window.core.config.get("remote_tools.mcp", False)
            enabled["file_search"] = self.window.core.config.get("remote_tools.file_search", False)
            enabled["computer_use"] = (mode == MODE_COMPUTER or model.id.startswith("computer-use"))
        else:
            # for expert call, get from preset config
            if preset:
                if preset.remote_tools:
                    tools_list = [preset_remote_tool.strip() for preset_remote_tool in preset.remote_tools.split(",") if preset_remote_tool.strip()]
                    for item in tools_list:
                        if item in enabled:
                            enabled[item] = True

        # o1, o3, models do not support remote tools
        # TODO: check if really not supported
        if model.id.startswith("o1") or model.id.startswith("o3"):
            return tools

        # extend local tools with remote tools
        if enabled["computer_use"]:
            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_COMPUTER_USE:
                tools.append(self.window.core.api.openai.computer.get_tool())
        else:
            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH:
                if enabled["web_search"]:
                    tools.append({"type": "web_search_preview"})

            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER:
                if enabled["code_interpreter"]:
                    tools.append({
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto"
                        }
                    })

            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_IMAGE:
                if enabled["image"]:
                    tool = {"type": "image_generation"}
                    if stream:
                        tool["partial_images"] = 1  # required for streaming
                    tools.append(tool)

            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_FILE_SEARCH:
                if enabled["file_search"]:
                    vector_store_ids = self.window.core.config.get("remote_tools.file_search.args", "")
                    if vector_store_ids:
                        vector_store_ids = [store.strip() for store in vector_store_ids.split(",") if store.strip()]
                        tools.append({
                            "type": "file_search",
                            "vector_store_ids": vector_store_ids,
                        })

            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_MCP:
                if enabled["mcp"]:
                    mcp_tool = self.window.core.config.get("remote_tools.mcp.args", "")
                    if mcp_tool:
                        mcp_tool = json.loads(mcp_tool)
                        tools.append(mcp_tool)

        return tools