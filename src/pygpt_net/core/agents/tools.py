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
import os
import re
from typing import List, Dict, Any
from pydantic import BaseModel, create_model
from inspect import Signature, Parameter
from functools import wraps

from agents import (
    FunctionTool as OpenAIFunctionTool,
    RunContextWrapper,
    function_tool
)
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
        self.agent_idx = None  # agent index, used for query engine tool
        self.context = None  # BridgeContext instance, used for tool execution

    def prepare(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            verbose: bool = False,
            force: bool = False
    ) -> List[BaseTool]:
        """
        Prepare tools for agent

        :param context: BridgeContext
        :param extra: extra data
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        :return: list of tools
        """
        self.verbose = verbose
        tools = []

        # add functions from plugins
        plugin_functions = self.get_plugin_functions(context.ctx, verbose=verbose, force=force)
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
            verbose: bool = False,
            force: bool = False
    ) -> list:
        """
        Parse plugin functions

        :param ctx: CtxItem
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        :return: List of functions
        """
        tools = []
        functions = self.window.core.command.get_functions(force=force)
        for item in functions:
            try:
                name = item['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands

                description = item['desc']
                schema = json.loads(item['params'])  # from JSON to dict

                def make_func(name, description):
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

                    func.__name__ = name
                    func.__doc__ = description
                    return func

                func = make_func(name, description)
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

    def get_function_tools(
            self,
            ctx: CtxItem,
            verbose: bool = False,
            force: bool = False
    ) -> list:
        """
        Parse plugin functions and return as OpenAI FunctionTool instances

        :param ctx: CtxItem
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        :return: List of OpenAIFunctionTool instances
        """
        tools = []
        functions = self.window.core.command.get_functions(force=force)
        blacklist = []
        for item in functions:
            try:
                name = item['name']
                if name in self.cmd_blacklist or name in blacklist:
                    continue
                description = item['desc']

                async def run_function(run_ctx: RunContextWrapper[Any], args: str) -> str:
                    name = run_ctx.tool_name
                    print("[Plugin] Tool call: " + name + " with args: " + str(args))
                    cmd = {
                        "cmd": name,
                        "params": json.loads(args)  # args should be a JSON string
                    }
                    return self.window.controller.plugins.apply_cmds_all(ctx, [cmd])

                tool = OpenAIFunctionTool(
                    name=name,
                    description=description,
                    params_json_schema=json.loads(item['params']),
                    on_invoke_tool=run_function,
                )
                tools.append(tool)
            except Exception as e:
                print(e)
        return tools

    def get_plugin_tools(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            verbose: bool = False,
            force: bool = False
    ) -> dict:
        """
        Parse plugin functions

        :param context: BridgeContext
        :param extra: extra data
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        """
        tools = {}
        functions = self.window.core.command.get_functions(force=force)
        for item in functions:
            try:
                name = item['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands

                description = item['desc']
                schema = json.loads(item['params'])  # from JSON to dict

                def make_func(name, description):
                    def func(**kwargs):
                        self.log("[Plugin] Tool call: " + name + " " + str(kwargs))
                        cmd = {
                            "cmd": name,
                            "params": kwargs,
                        }
                        response = self.window.controller.plugins.apply_cmds_all(
                            context.ctx,  # current ctx
                            [cmd],  # commands
                        )
                        return str(response)  # return response as string

                    func.__name__ = name
                    func.__doc__ = description
                    return func

                func = make_func(name, description)
                tools[name] = func
            except Exception as e:
                print(e)

        # add query engine tool if idx is provided
        if self.agent_idx is not None and self.agent_idx  != "_":
            tools["query_engine"] = None  # placeholder for query engine tool

        return tools


    def get_plugin_specs(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            verbose: bool = False,
            force: bool = False
    ) -> list:
        """
        Parse plugin functions

        :param context: BridgeContext
        :param extra: extra data
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        """
        specs = []
        functions = self.window.core.command.get_functions(force=force)

        # add query engine tool spec if idx is provided
        if self.agent_idx is not None and self.agent_idx  != "_":
            specs.append("**query_engine**: "
                         "Provides additional context and access to the indexed documents, "
                         "available params: {'query': {'type': 'string', 'description': 'query string'}}, required: [query]")

        for func in functions:
            try:
                name = func['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands
                description = func['desc']
                schema = json.loads(func['params'])  # from JSON to dict
                spec = "**{}**: {}, available params: {}, required: {}\n".format(name, description, schema.get("properties", {}), schema.get("required", []))
                specs.append(spec)
            except Exception as e:
                print(e)
        return specs

    def tool_exec(self, cmd: str, params: Dict[str, Any]) -> str:
        """
        Execute tool command

        :param cmd: command name
        :param params: command parameters
        :return: command output
        """
        print("[Plugin] Tool call: " + cmd + " " + str(params))
        # special case for query engine tool
        if cmd == "query_engine":
            if "query" not in params:
                return "Query parameter is required for query_engine tool."
            if self.context is None:
                return "Context is not set for query_engine tool."
            if self.agent_idx is None or self.agent_idx == "_":
                return "Agent index is not set for query_engine tool."
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=self.context.model)
            index = self.window.core.idx.storage.get(self.agent_idx, llm, embed_model)  # get index
            if index is not None:
                query_engine = index.as_query_engine(similarity_top_k=3)
                response = query_engine.query(params["query"])
                print("[Plugin] Query engine response: " + str(response))
                self.log("[Plugin] Query engine response: " + str(response))
                return str(response)
            else:
                return "Index not found for query_engine tool."

        # rest of the plugin commands
        cmd = {
            "cmd": cmd,
            "params": params,
        }
        ctx = CtxItem()
        ctx.extra["agent_input"] = True  # mark as user input
        ctx.agent_call = True  # disables reply from plugin commands
        response = self.window.controller.plugins.apply_cmds_all(
            ctx,  # current ctx
            [cmd],  # commands
        )
        return response

    def get_retriever_tool(
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
        tool = None
        # add query engine tool if idx is provided
        idx = extra.get("agent_idx", None)
        if idx is not None and idx != "_":
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=context.model)
            index = self.window.core.idx.storage.get(idx, llm, embed_model)  # get index
            if index is not None:
                query_engine = index.as_query_engine(similarity_top_k=3)
                tool = [
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
        return tool

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

    def get_last_tool_output(self) -> dict:
        """
        Get last tool output

        :return: last tool output
        """
        if self.window.core.agents.tools.last_tool_output is None:
            return {}
        return self.window.core.agents.tools.last_tool_output

    def has_last_tool_output(self) -> bool:
        """
        Check if there is a last tool output

        :return: True if last tool output exists, False otherwise
        """
        return self.window.core.agents.tools.last_tool_output is not None

    def clear_last_tool_output(self):
        """Clear last tool output"""
        self.window.core.agents.tools.last_tool_output = None

    def append_tool_outputs(self, ctx: CtxItem, clear: bool = True):
        """
        Append tool outputs to context

        :param ctx: CtxItem
        :param clear: clear last tool output after appending
        """
        if self.has_last_tool_output():
            outputs = [self.get_last_tool_output()]
            ctx.extra["tool_output"] = outputs
            if outputs is not None:
                response = ""
                for output in outputs:
                    if ("code" in output and "output" in output["code"] and
                            "content" in output["code"]["output"]):
                        response += str(output["code"]["output"]["content"])
                self.window.core.filesystem.parser.extract_data_files(ctx, response) # img, files
            if clear:
                self.clear_last_tool_output()  # clear after use

    def extract_tool_outputs(self, ctx: CtxItem, clear: bool = True):
        """
        Append tool outputs to context

        :param ctx: CtxItem
        :param clear: clear last tool output after appending
        """
        if self.has_last_tool_output():
            outputs = [self.get_last_tool_output()]
            if outputs is not None:
                response = ""
                for output in outputs:
                    if ("code" in output and "output" in output["code"] and
                            "content" in output["code"]["output"]):
                        response += str(output["code"]["output"]["content"])
                self.window.core.filesystem.parser.extract_data_files(ctx, response) # img, files
            if clear:
                self.clear_last_tool_output()  # clear after use

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
