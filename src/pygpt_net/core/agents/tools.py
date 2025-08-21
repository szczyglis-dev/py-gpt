#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.21 07:00:00                  #
# ================================================== #

import json
from typing import List, Dict, Any

from agents import (
    FunctionTool as OpenAIFunctionTool,
    RunContextWrapper,
)
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.tools import BaseTool, FunctionTool, QueryEngineTool, ToolMetadata

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event
from pygpt_net.core.types import (
    QUERY_ENGINE_TOOL_NAME,
    QUERY_ENGINE_TOOL_DESCRIPTION,
    QUERY_ENGINE_TOOL_SPEC,
)
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
        query_engine_tools = self.get_retriever_tool(
            context=context,
            extra=extra,
            verbose=verbose,
        )
        if query_engine_tools:
            tools.extend(query_engine_tools)
        return tools

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
        if self.window.core.idx.is_valid(idx):
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=context.model)
            index = self.window.core.idx.storage.get(idx, llm, embed_model)  # get index
            if index is not None:
                query_engine = index.as_query_engine(similarity_top_k=3)
                tool = [
                    QueryEngineTool(
                        query_engine=query_engine,
                        metadata=ToolMetadata(
                            name=QUERY_ENGINE_TOOL_NAME,
                            description=QUERY_ENGINE_TOOL_DESCRIPTION,
                        ),
                    ),
                ]
        return tool

    def get_openai_retriever_tool(
            self,
            idx: str,
            verbose: bool = False
    ) -> OpenAIFunctionTool:
        """
        Prepare OpenAI retriever tool for agent

        :param idx: index name
        :param verbose: verbose mode
        :return: OpenAIFunctionTool instance
        """
        async def run_function(run_ctx: RunContextWrapper[Any], args: str) -> str:
            name = run_ctx.tool_name
            print(f"[Plugin] Tool call: {name} with args: {args}")
            cmd = {
                "cmd": name,
                "params": json.loads(args)  # args should be a JSON string
            }
            return self.tool_exec(name, cmd["params"])

        schema = {"type": "object", "properties": {
            "query": {
                "type": "string",
                "description": "The query string to search in the index."
            }
        }, "additionalProperties": False}
        description = QUERY_ENGINE_TOOL_DESCRIPTION + f" Index: {idx}"
        return OpenAIFunctionTool(
            name=QUERY_ENGINE_TOOL_NAME,
            description=description,
            params_json_schema=schema,
            on_invoke_tool=run_function,
        )

    def get_plugin_functions(
            self,
            ctx: CtxItem,
            verbose: bool = False,
            force: bool = False
    ) -> List[BaseTool]:
        """
        Parse plugin functions

        :param ctx: CtxItem
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        :return: List of BaseTool instances
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
                        self.log(f"[Plugin] Tool call: {name} {kwargs}")
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
                self.window.core.debug.log(e)
        return tools

    def get_function_tools(
            self,
            ctx: CtxItem,
            verbose: bool = False,
            force: bool = False
    ) -> List[OpenAIFunctionTool]:
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
                    print(f"[Plugin] Tool call: {name} with args: {args}")
                    cmd = {
                        "cmd": name,
                        "params": json.loads(args)  # args should be a JSON string
                    }
                    return self.window.controller.plugins.apply_cmds_all(ctx, [cmd])

                schema = json.loads(item['params'])  # from JSON to dict
                extra = ""
                # fix schema for OpenAI FunctionTool
                if "properties" in schema:
                    for property_name, property_value in schema["properties"].items():
                        if "enum" in property_value:
                            """
                            extra += ", Enum values: "
                            extra += ", ".join(
                                [str(enum_value) for enum_value in property_value["enum"]]
                            )
                            """
                            del property_value["enum"]  # remove enum for OpenAI FunctionTool
                        if property_value["type"] == "object":
                            if "properties" not in property_value:
                                property_value["properties"] = {}
                            if "required" not in property_value:
                                property_value["required"] = []
                            if "additionalProperties" not in property_value:
                                property_value["additionalProperties"] = False
                schema["additionalProperties"] = False
                description += extra
                tool = OpenAIFunctionTool(
                    name=name,
                    description=description,
                    params_json_schema=schema,
                    on_invoke_tool=run_function,
                )
                tools.append(tool)
            except Exception as e:
                self.window.core.debug.log(e)

        # append query engine tool if idx is provided
        if self.window.core.idx.is_valid(self.agent_idx):
            tools.append(self.get_openai_retriever_tool(self.agent_idx))

        return tools

    def get_plugin_tools(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            verbose: bool = False,
            force: bool = False
    ) -> Dict[str, BaseTool]:
        """
        Parse plugin functions

        :param context: BridgeContext
        :param extra: extra data
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        :return: Dictionary of tool names and BaseTool instances
        """
        tools = {}
        functions = self.window.core.command.get_functions(force=force)
        for item in functions:
            try:
                name = item['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands

                description = item['desc']

                def make_func(name, description):
                    def func(**kwargs):
                        self.log(f"[Plugin] Tool call: {name} {kwargs}")
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
                self.window.core.debug.log(e)

        # add query engine tool if idx is provided
        if self.window.core.idx.is_valid(self.agent_idx):
            extra = {
                "agent_idx": self.agent_idx,  # agent index for query engine tool
            }
            query_engine_tools = self.get_retriever_tool(
                context=context,
                extra=extra,
                verbose=verbose,
            )
            if query_engine_tools:
                tools["query_engine"] = query_engine_tools[0]  # add query engine tool
        return tools


    def get_plugin_specs(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            verbose: bool = False,
            force: bool = False
    ) -> List[str]:
        """
        Parse plugin functions

        :param context: BridgeContext
        :param extra: extra data
        :param verbose: verbose mode
        :param force: force to get functions even if not needed
        :return: List of tool specifications as strings
        """
        specs = []
        functions = self.window.core.command.get_functions(force=force)

        # add query engine tool spec if idx is provided
        if self.window.core.idx.is_valid(self.agent_idx):
            specs.append(QUERY_ENGINE_TOOL_SPEC)

        for func in functions:
            try:
                name = func['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands
                description = func['desc']
                schema = json.loads(func['params'])  # from JSON to dict
                specs.append(
                    f"**{name}**: {description}, available params: {schema.get('properties', {})}, required: {schema.get('required', [])}\n"
                )
            except Exception as e:
                self.window.core.debug.log(e)
        return specs

    def tool_exec(self, cmd: str, params: Dict[str, Any]) -> str:
        """
        Execute tool command

        :param cmd: command name
        :param params: command parameters
        :return: command output
        """
        print(f"[Plugin] Tool call: {cmd}, {params}")

        # special case for query engine tool
        if cmd == QUERY_ENGINE_TOOL_NAME:
            if "query" not in params:
                return "Query parameter is required for query_engine tool."
            if self.context is None:
                return "Context is not set for query_engine tool."
            if not self.window.core.idx.is_valid(self.agent_idx):
                return "Agent index is not set for query_engine tool."
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=self.context.model)
            index = self.window.core.idx.storage.get(self.agent_idx, llm, embed_model)  # get index
            if index is not None:
                query_engine = index.as_query_engine(similarity_top_k=3)
                response = query_engine.query(params["query"])
                print(f"[Plugin] Query engine response: {response}")
                self.log(f"[Plugin] Query engine response: {response}")
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
            item = {
                "ToolOutput": {
                    "content": str(output.content),
                    "tool_name": str(output.tool_name),
                    "raw_input": str(output.raw_input),
                    "raw_output": str(output.raw_output),
                }
            }
            data.append(item)
        return data

    def get_last_tool_output(self) -> dict:
        """
        Get last tool output

        :return: last tool output
        """
        if self.last_tool_output is None:
            return {}
        return self.last_tool_output

    def has_last_tool_output(self) -> bool:
        """
        Check if there is a last tool output

        :return: True if last tool output exists, False otherwise
        """
        return self.last_tool_output is not None

    def clear_last_tool_output(self):
        """Clear last tool output"""
        self.last_tool_output = None

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

    def set_idx(self, agent_idx: str):
        """
        Set agent index for query engine tool

        :param agent_idx: agent index
        """
        self.agent_idx = agent_idx

    def set_context(self, context: BridgeContext):
        """
        Set context for tool execution

        :param context: BridgeContext instance
        """
        self.context = context

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
