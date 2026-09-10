#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 17:58:00                  #
# ================================================== #

import json

from agents import (
    WebSearchTool,
    CodeInterpreterTool,
    ImageGenerationTool,
    FileSearchTool,
    ComputerTool,
    HostedMCPTool,
    ModelSettings,
)

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

from pygpt_net.provider.llms.agent_computer import build_openai_agent_computer_tool

from .computer import LocalComputer


def is_computer_tool(
        window,
        model: ModelItem,
        preset: PresetItem,
        is_expert_call: bool,
):
    if not model.is_gpt():
        return False

    if not is_expert_call:
        # from global config if not expert call
        return (
            model.id.startswith("computer-use")
            or (
                window.core.config.get("remote_tools.computer_use", False)
                and model.has_mode(MODE_COMPUTER)
            )
        )
    else:
        # for expert call, get from preset config
        if preset and preset.remote_tools:
            tools_list = [preset_remote_tool.strip() for preset_remote_tool in preset.remote_tools.split(",") if
                          preset_remote_tool.strip()]
            return "computer_use" in tools_list and (
                model.id.startswith("computer-use") or model.has_mode(MODE_COMPUTER)
            )


def append_tools(
        tools: list,
        window,
        model: ModelItem,
        preset: PresetItem,
        allow_local_tools: bool = True,
        allow_remote_tools: bool = True,
        is_expert_call: bool = False,
):
    """
    Append tools to the kwargs based on the model and preset configuration.

    :param tools: Local tools to append
    :param window: Window instance
    :param model: ModelItem instance
    :param preset: PresetItem instance
    :param allow_local_tools: Allow local tools to be appended
    :param allow_remote_tools: Allow remote tools to be appended
    :param is_expert_call: Flag indicating if it's an expert call
    :return: kwargs dictionary with tools and model settings
    """
    kwargs = {}
    remote_tools = []
    if not allow_local_tools:
        tools = []

    if allow_remote_tools:
        tool_kwargs = {
            "window": window,
            "model": model,
            "preset": preset,
            "is_expert_call": is_expert_call,
        }
        remote_tools = get_remote_tools(**tool_kwargs)

        # Non-OpenAI models used by the OpenAI Agents SDK need a small outer
        # FunctionTool bridge for provider-native client-side Computer Use. The
        # bridge itself reuses the same Google/Anthropic continuation adapters
        # as Chat with Files / Agents v2, and is treated as a remote tool so
        # per-agent allow_remote_tools remains authoritative.
        agent_tools = getattr(getattr(window, "core", None), "agents", None)
        tools_core = getattr(agent_tools, "tools", None)
        context = getattr(tools_core, "context", None)
        computer_runtime = getattr(tools_core, "computer_runtime", None)
        computer_tool = build_openai_agent_computer_tool(
            window=window,
            context=context,
            model=model,
            runtime=computer_runtime,
            system_prompt=getattr(context, "system_prompt", "") if context else "",
        )
        if computer_tool is not None:
            # Prefer the shared PyGPT provider-native Computer Use bridge over
            # Agents SDK ComputerTool. This keeps OpenAI Agents on the exact same
            # continuation/runtime path as Chat with Files, legacy LlamaIndex
            # agents and Agents v2. It also makes Computer Use a regular
            # FunctionTool from the worker's point of view, so it survives nested
            # worker/supervisor flows reliably. Keep native ComputerTool only as
            # a fallback when no provider bridge can be constructed.
            remote_tools = [
                tool for tool in remote_tools
                if not isinstance(tool, ComputerTool)
            ]
            remote_tools.append(computer_tool)

        model_settings = {}

        # Agents SDK uses Responses API for hosted WebSearchTool. Request the
        # complete consulted source list, not only inline url_citation entries.
        if any(isinstance(tool, WebSearchTool) for tool in remote_tools):
            model_settings["response_include"] = [
                "web_search_call.action.sources"
            ]

        if model_settings:
            kwargs["model_settings"] = ModelSettings(**model_settings)

    all_tools = remote_tools + tools
    if all_tools:
        kwargs["tools"] = all_tools
    return kwargs

def get_remote_tools(
        window,
        model: ModelItem,
        preset: PresetItem,
        is_expert_call: bool,
):
    """
    Append remote tools to the list based on the model and preset configuration.

    :param model: ModelItem instance
    :param preset: PresetItem instance
    :param is_expert_call: Flag indicating if it's an expert call
    :param window: Window instance
    """
    tools = []

    if not model.is_gpt():
        return []

    if model.id.startswith("o1") or model.id.startswith("o3"):
        return tools

    def on_safety_check(data):
        """
        Safety check for the computer tool.
        """
        return True

    # disabled by default
    enabled = {
        "web_search": False,
        "image": False,
        "code_interpreter": False,
        "mcp": False,
        "file_search": False,
        "computer_use": False,
    }

    enabled_global = window.controller.chat.remote_tools.enabled  # get global config

    # from global config if not expert call
    if not is_expert_call:
        enabled["web_search"] = enabled_global(model, "web_search") # <-- from global config
        enabled["image"] = window.core.config.get("remote_tools.image", False)
        enabled["code_interpreter"] = window.core.config.get("remote_tools.code_interpreter", False)
        enabled["mcp"] = window.core.config.get("remote_tools.mcp", False)
        enabled["file_search"] = window.core.config.get("remote_tools.file_search", False)
        enabled["computer_use"] = (
            model.id.startswith("computer-use")
            or (
                window.core.config.get("remote_tools.computer_use", False)
                and model.has_mode(MODE_COMPUTER)
            )
        )
    else:
        # for expert call, get from preset config
        if preset:
            if preset.remote_tools:
                if isinstance(preset.remote_tools, str):
                    tools_list = [preset_remote_tool.strip() for preset_remote_tool in preset.remote_tools.split(",") if
                                  preset_remote_tool.strip()]
                elif isinstance(preset.remote_tools, list):
                    tools_list = [str(preset_remote_tool).strip() for preset_remote_tool in preset.remote_tools if
                                  str(preset_remote_tool).strip()]
                else:
                    tools_list = []
                if "web_search" not in tools_list:
                    enabled["web_search"] = enabled_global(model, "web_search")  # <-- from global config
                for item in tools_list:
                    if item in enabled:
                        enabled[item] = True

    # Expert presets may list Computer Use explicitly, but only expose it on
    # models that actually advertise the Computer capability.
    if enabled["computer_use"] and not (
            model.id.startswith("computer-use") or model.has_mode(MODE_COMPUTER)
    ):
        enabled["computer_use"] = False

    dedicated_computer = model.id.startswith("computer-use")
    if enabled["computer_use"] and model.id not in OPENAI_REMOTE_TOOL_DISABLE_COMPUTER_USE:
        computer = LocalComputer(window=window)
        tools.append(ComputerTool(computer, on_safety_check=on_safety_check))

    if not dedicated_computer:
        if model.id not in OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH and enabled["web_search"]:
            tools.append(WebSearchTool())

        if model.id not in OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER and enabled["code_interpreter"]:
            tools.append(CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}},
            ))

        if model.id not in OPENAI_REMOTE_TOOL_DISABLE_IMAGE and enabled["image"]:
            tools.append(ImageGenerationTool(
                tool_config={"type": "image_generation", "quality": "low"},
            ))

        if model.id not in OPENAI_REMOTE_TOOL_DISABLE_FILE_SEARCH and enabled["file_search"]:
            vector_store_ids = window.core.config.get("remote_tools.file_search.args", "")
            if vector_store_ids:
                vector_store_ids = [store.strip() for store in vector_store_ids.split(",") if store.strip()]
            tools.append(FileSearchTool(
                max_num_results=3,
                vector_store_ids=vector_store_ids,
                include_search_results=True,
            ))

        if model.id not in OPENAI_REMOTE_TOOL_DISABLE_MCP and enabled["mcp"]:
            mcp_tool = window.core.config.get("remote_tools.mcp.args", "")
            if mcp_tool:
                mcp_tool = json.loads(mcp_tool)
                tools.append(HostedMCPTool(
                    tool_config=mcp_tool,
                ))

    return tools
