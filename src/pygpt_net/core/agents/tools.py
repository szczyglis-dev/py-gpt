#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 14:45:00                  #
# ================================================== #

from __future__ import annotations
import json
from typing import TYPE_CHECKING, List, Dict, Any


from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types import (
    TOOL_QUERY_ENGINE_NAME,
    TOOL_QUERY_ENGINE_DESCRIPTION,
    TOOL_QUERY_ENGINE_SPEC,
)
from pygpt_net.item.ctx import CtxItem

if TYPE_CHECKING:
    from agents import FunctionTool as OpenAIFunctionTool
    from llama_index.core.chat_engine.types import AgentChatResponse
    from llama_index.core.tools import BaseTool
    from agents import RunContextWrapper

class Tools:

    def __init__(self, window=None):
        """
        Agent tools

        :param window: Window instance
        """
        self.window = window
        self.cmd_blacklist = []
        self.verbose = False
        self.agent_idx = None  # agent index, used for query engine tool
        self.context = None  # BridgeContext instance, used for tool execution
        self.computer_runtime = None  # shared provider-native Computer Use runtime

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
        from llama_index.core.tools import QueryEngineTool, ToolMetadata

        tool = None

        # add query engine tool if idx is provided. Resolve the virtual
        # Current project ID only at runtime, keeping normal configured index
        # IDs untouched.
        idx = extra.get("agent_idx", None)
        if self.window.core.idx.is_valid(idx):
            storage_idx = idx
            if self.window.core.idx.project.is_virtual(idx) is True:
                storage_idx = self.window.core.idx.resolve_idx(idx)
            if storage_idx is None:
                return tool
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=context.model)
            index = self.window.core.idx.storage.get(storage_idx, llm, embed_model)
            if index is not None:
                query_engine = index.as_query_engine(
                    llm=llm,
                    similarity_top_k=3,
                )
                tool = [
                    QueryEngineTool(
                        query_engine=query_engine,
                        metadata=ToolMetadata(
                            name=TOOL_QUERY_ENGINE_NAME,
                            description=TOOL_QUERY_ENGINE_DESCRIPTION,
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
        from agents import FunctionTool as OpenAIFunctionTool, RunContextWrapper

        async def run_function(_run_ctx, args: str) -> str:
            # openai-agents 0.18.x passes a plain RunContextWrapper when the
            # callback explicitly declares that type; tool_name lives only on
            # ToolContext. This tool has a fixed name, so do not depend on the
            # SDK-specific richer context here.
            name = TOOL_QUERY_ENGINE_NAME
            print(f"[Plugin] Tool call: {name} with args: {args}")
            cmd = {
                "cmd": name,
                "params": json.loads(args)  # args should be a JSON string
            }
            return self.tool_exec(name, cmd["params"])

        # ``from __future__ import annotations`` stores annotations as strings.
        # RunContextWrapper is imported locally to keep the Agents SDK optional,
        # so expose the concrete runtime type to introspection explicitly.
        run_function.__annotations__["_run_ctx"] = RunContextWrapper[Any]

        schema = {"type": "object", "properties": {
            "query": {
                "type": "string",
                "description": "The query string to search in the index."
            }
        }, "additionalProperties": False}
        description = TOOL_QUERY_ENGINE_DESCRIPTION + f" Index: {idx}"
        return OpenAIFunctionTool(
            name=TOOL_QUERY_ENGINE_NAME,
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
        from llama_index.core.tools import FunctionTool
        from pygpt_net.core.command.tool_schema import JsonSchemaToolMetadata

        tools = []
        functions = self.window.core.command.get_functions(force=force)
        for item in functions:
            try:
                name = item['name']
                if name in self.cmd_blacklist:
                    continue  # skip blacklisted commands

                description = item['desc']
                schema = json.loads(item['params'])  # from JSON to dict

                def make_func(name, description, tool_schema):
                    def func(**kwargs):
                        self.log(f"[Plugin] Tool call: {name} {kwargs}")
                        call_args = dict(kwargs or {})
                        for wrapper in ("params", "arguments"):
                            wrapped = call_args.get(wrapper)
                            if isinstance(wrapped, dict) and len(call_args) == 1:
                                call_args = dict(wrapped)
                                break

                        required = list((tool_schema or {}).get("required") or [])
                        missing = [
                            key for key in required
                            if key not in call_args or call_args.get(key) is None
                        ]
                        if missing:
                            return json.dumps({
                                "error": "Missing required tool parameter(s).",
                                "tool": name,
                                "missing": missing,
                                "required": required,
                                "received": sorted(call_args.keys()),
                            }, ensure_ascii=False)

                        cmd = {
                            "cmd": name,
                            "params": call_args,
                        }
                        response = self.window.controller.plugins.apply_cmds_all(
                            ctx,  # current ctx
                            [cmd],  # commands
                        )
                        return str(response)  # return response as string

                    func.__name__ = name
                    func.__doc__ = description
                    return func

                func = make_func(name, description, schema)
                metadata = JsonSchemaToolMetadata(
                    name=name,
                    description=description,
                    schema=schema,
                )
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
        from agents import FunctionTool as OpenAIFunctionTool, RunContextWrapper

        tools = []
        functions = self.window.core.command.get_functions(force=force)
        blacklist = []
        for item in functions:
            try:
                name = item['name']
                if name in self.cmd_blacklist or name in blacklist:
                    continue
                description = item['desc']

                def make_run_function(tool_name: str):
                    async def run_function(_run_ctx, args: str) -> str:
                        # Capture the tool name explicitly. In openai-agents
                        # 0.18.x RunContextWrapper itself has no ``tool_name``
                        # attribute; that metadata belongs to ToolContext.
                        print(f"[Plugin] Tool call: {tool_name} with args: {args}")
                        cmd = {
                            "cmd": tool_name,
                            "params": json.loads(args)  # args should be a JSON string
                        }
                        return self.window.controller.plugins.apply_cmds_all(ctx, [cmd])
                    run_function.__annotations__["_run_ctx"] = RunContextWrapper[Any]
                    return run_function

                run_function = make_run_function(name)
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
            specs.append(TOOL_QUERY_ENGINE_SPEC)

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
        if cmd == TOOL_QUERY_ENGINE_NAME:
            if "query" not in params:
                return "Query parameter is required for query_engine tool."
            if self.context is None:
                return "Context is not set for query_engine tool."
            if not self.window.core.idx.is_valid(self.agent_idx):
                return "Agent index is not set for query_engine tool."
            storage_idx = self.agent_idx
            if self.window.core.idx.project.is_virtual(storage_idx) is True:
                storage_idx = self.window.core.idx.resolve_idx(storage_idx)
            if storage_idx is None:
                return "Agent index is not set for query_engine tool."
            llm, embed_model = self.window.core.idx.llm.get_service_context(model=self.context.model)
            index = self.window.core.idx.storage.get(storage_idx, llm, embed_model)
            if index is not None:
                query_engine = index.as_query_engine(
                    llm=llm,
                    similarity_top_k=3,
                )
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

    def set_computer_runtime(self, runtime):
        """Set shared provider-native Computer Use runtime for legacy agents."""
        self.computer_runtime = runtime

    def log(self, msg: str):
        """
        Log message

        :param msg: message
        """
        if self.verbose:
            print(msg)
            self.window.core.debug.add(msg)
