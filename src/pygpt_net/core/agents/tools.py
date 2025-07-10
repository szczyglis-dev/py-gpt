#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 23:00:00                  #
# ================================================== #

import json
from typing import List, Dict, Any

from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.tools import BaseTool, FunctionTool, QueryEngineTool, ToolMetadata

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem


class Tools:
    def __init__(self, window=None):
        """
        Agent tools

        :param window: Window instance
        """
        self.window = window
        self.cmd_blacklist = []
        self.verbose = False
        self.code_execute_fn = CodeExecutor(window)
        self.last_tool_output = None

    def prepare(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            verbose: bool = False
    ) -> List[BaseTool]:
        """
        Prepare tools for agent

        :param context: BridgeContext
        :param extra: extra data
        :param verbose: verbose mode
        :return: list of tools
        """
        self.verbose = verbose
        tools = []

        # add functions from plugins
        plugin_functions = self.get_plugin_functions(context.ctx, verbose=verbose)
        tools.extend(plugin_functions)

        # add query engine tool if idx is provided
        idx = extra.get("agent_idx", None)
        if idx is not None and idx != "_":
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=context.model)
            index = self.window.core.idx.storage.get(idx, llm, embed_model)  # get index
            if index is not None:
                query_engine = index.as_query_engine(similarity_top_k=3)
                query_engine_tools = [
                    QueryEngineTool(
                        query_engine=query_engine,
                        metadata=ToolMetadata(
                            name="query_engine",
                            description=(
                                "Provides additional context and access to the indexed documents."
                            ),
                        ),
                    ),
                ]
                tools.extend(query_engine_tools)
        return tools

    def get_plugin_functions(
            self,
            ctx: CtxItem,
            verbose: bool = False
    ) -> list:
        """
        Parse plugin functions

        :param ctx: CtxItem
        :param verbose: verbose mode
        :return: List of functions
        """
        tools = []
        functions = self.window.core.command.get_functions()
        for func in functions:
            try:
                name = func['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands

                description = func['desc']
                schema = json.loads(func['params'])  # from JSON to dict

                def make_func(name):
                    def func(**kwargs):
                        self.log("[Plugin] Tool call: " + name + " " + str(kwargs))
                        cmd = {
                            "cmd": name,
                            "params": kwargs,
                        }
                        response = self.window.controller.plugins.apply_cmds_all(
                            ctx,  # current ctx
                            [cmd],  # commands
                        )
                        return str(response)  # return response as string

                    return func

                func = make_func(name)
                metadata = PluginToolMetadata(
                    name=name,
                    description=description,
                )
                metadata.schema = schema
                tool = FunctionTool(
                    fn=func,
                    metadata=metadata,
                )
                tools.append(tool)
            except Exception as e:
                print(e)
        return tools

    def export_sources(
            self,
            response: AgentChatResponse
    ) -> List[dict]:
        """
        Export sources from response

        :param response: response
        :return: list of sources
        """
        data = []
        for output in response.sources:
            item = {}
            item["ToolOutput"] = {
                "content": str(output.content),
                "tool_name": str(output.tool_name),
                "raw_input": str(output.raw_input),
                "raw_output": str(output.raw_output),
            }
            data.append(item)
        return data

    def log(self, msg: str):
        """
        Log message

        :param msg: message
        """
        if self.verbose:
            print(msg)
            self.window.core.debug.add(msg)

class PluginToolMetadata(ToolMetadata):
    def __init__(self, name: str, description: str):
        super().__init__(name=name, description=description)
        self.schema = None

    def get_parameters_dict(self) -> Dict[str, Any]:
        """
        Get parameters dictionary

        :return: parameters
        """
        parameters = {
            k: v
            for k, v in self.schema.items()
            if k in ["type", "properties", "required", "definitions"]
        }
        return parameters

class CodeExecutor:
    """Code executor for codeAct agent"""

    def __init__(self, window = None):
        """
        Initialize the code executor.

        :param window: Window instance
        """
        self.window = window

    def execute(self, code: str) -> str:
        """
        Execute Python code and capture output and return values.

        :param code: Python code to execute
        :return: Output from the code execution
        """
        self.window.core.agents.tools.last_tool_output = None
        if code == "/restart":
            commands = [
                {
                    "cmd": "ipython_kernel_restart",
                    "params": {},
                    "silent": True,
                    "force": True,
                }
            ]
        else:
            commands = [
                {
                    "cmd": "ipython_execute",
                    "params": {
                        "code": code,
                        "path": ".interpreter.current.py",
                    },
                    "silent": True,
                    "force": True,
                }
            ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
            'silent': True,
        })
        event.ctx = CtxItem()  # tmp
        event.ctx.async_disabled = True  # disable async for this event
        self.window.controller.command.dispatch_only(event)

        # if restart command was executed, return success message
        if code == "/restart":
            return "IPython kernel restarted successfully."

        response = event.ctx.bag  # tmp response
        output = ""

        # store tool output if available
        if "code" in response:
            if "output" in response["code"]:
                output = response["code"]["output"]["content"]
                tool_output = {
                    "cmd": "ipython_execute",
                    "code": {
                        "input": {
                            "content": response["code"]["input"]["content"],
                            "lang": "python"
                        },
                        "output": {
                            "content": response["code"]["output"]["content"],
                            "lang": "python"
                        }
                    },
                    "plugin": response["plugin"],
                    "result": response["result"]
                }
                self.window.core.agents.tools.last_tool_output = tool_output
        return output