#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 00:00:00                  #
# ================================================== #

import copy
import json
import re

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Command:
    DESC_LIMIT = 1024

    def __init__(self, window=None):
        """
        Commands core

        :param window: Window instance
        """
        self.window = window

    def append_syntax(self, data: dict) -> str:
        """
        Append command syntax to the system prompt

        :param data: event data
        :return: prompt with appended syntax
        """
        prompt = data['prompt']
        cmd_prompt = self.window.core.prompt.get('cmd')
        extra = ""
        schema = self.extract_syntax(data['cmd'])
        if schema:
            if self.window.core.config.get('mode') == "assistant":
                extra = self.window.core.prompt.get('cmd.extra.assistants')  # Assistants API env fix
            else:
                extra = self.window.core.prompt.get('cmd.extra')
        if prompt.strip() != "":
            prompt += "\n\n"
        prompt += cmd_prompt.strip().replace("{extra}", extra).replace("{schema}", schema)
        return prompt

    def extract_syntax(self, cmds: list) -> str:
        """
        Extract syntax from commands

        :param cmds: commands list
        :return: JSON string with commands usage syntax
        """
        data = {}
        cmds = copy.deepcopy(cmds)  # make copy to prevent changes in original data
        self.window.core.ctx.current_cmd = copy.deepcopy(cmds)  # for debug purposes

        for cmd in cmds:
            if "cmd" in cmd and "instruction" in cmd:
                cmd_name = cmd["cmd"]
                data[cmd_name] = {
                    "help": cmd["instruction"],
                }
                if "params" in cmd and len(cmd["params"]) > 0:
                    data[cmd_name]["params"] = {}
                    for param in cmd["params"]:
                        try:
                            if isinstance(param, dict):
                                if "name" in param:
                                    # assign param
                                    key = param["name"]
                                    del param["name"]
                                    data[cmd_name]["params"][key] = param

                                    # remove required, leave only optional
                                    if "required" in data[cmd_name]["params"][key]:
                                        if data[cmd_name]["params"][key]["required"] is False:
                                            data[cmd_name]["params"][key]["optional"] = True
                                        del data[cmd_name]["params"][key]["required"]

                                    # remove type if str (default)
                                    if ("type" in data[cmd_name]["params"][key]
                                            and data[cmd_name]["params"][key]["type"] == "str"):
                                        del data[cmd_name]["params"][key]["type"]

                                    # remove description and move to help
                                    if "description" in data[cmd_name]["params"][key]:
                                        data[cmd_name]["params"][key]["help"] = data[cmd_name]["params"][key]["description"]
                                        del data[cmd_name]["params"][key]["description"]

                        except Exception as e:
                            pass

        self.window.core.ctx.current_cmd_schema = data  # for debug
        return json.dumps(data)  # pack, return JSON string without indent and formatting

    def has_cmds(self, text: str) -> bool:
        """
        Check if text has command execute syntax

        :param text: text to check
        :return: True if text has commands
        """
        if text is None:
            return False
        regex_cmd = r'~###~\s*{.*}\s*~###~'
        return bool(re.search(regex_cmd, text))

    def extract_cmds(self, text: str) -> list:
        """
        Extract commands from text

        :param text: text to extract commands from
        :return: list of commands (dict)
        """
        cmds = []
        try:
            chunks = text.split('~###~')
            for chunk in chunks:
                cmd = self.extract_cmd(chunk)  # extract JSON string to dict
                if cmd is not None:
                    cmds.append(cmd)  # cmd = dict
        except Exception as e:
            # do nothing
            pass
        return cmds

    def extract_cmd(self, chunk: str) -> dict or None:
        """
        Extract command from text chunk (JSON string)

        :param chunk: text chunk (JSON command string)
        :return: command dict
        """
        cmd = None
        chunk = chunk.strip()
        if chunk and chunk.startswith('{') and chunk.endswith('}'):
            try:
                # syntax1: {"read_file": {"path": ["my_cars.txt"]}}
                # syntax2: {"cmd": "read_file", "params": {"path": ["my_cars.txt"]}}
                cmd = json.loads(chunk)

                # if the first key is not "cmd", then try to convert from incorrect syntax into "cmd" syntax:
                if "cmd" not in cmd:
                    if len(cmd) == 1:
                        for key in cmd:
                            if "params" in cmd[key]:
                                cmd = {
                                    "cmd": key,
                                    "params": cmd[key]["params"]
                                }
                            else:
                                cmd = {
                                    "cmd": key,
                                    "params": cmd[key]
                                }
            except json.JSONDecodeError as e:
                # do nothing
                pass
        return cmd

    def from_commands(self, cmds: list) -> list:
        """
        Unpack commands to execution list

        :param cmds: commands list
        :return parsed commands
        """
        commands = []
        for cmd in cmds:
            if 'cmd' in cmd:
                commands.append(cmd)
        return commands

    def unpack_tool_calls(self, tool_calls: list) -> list:
        """
        Unpack tool calls from OpenAI response

        :param tool_calls: tool calls list
        :return: parsed tool calls list
        """
        parsed = []
        for tool_call in tool_calls:
            try:
                parsed.append(
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments)
                        }
                    }
                )
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error parsing tool call: " + str(e))
        return parsed

    def unpack_tool_calls_chunks(self, ctx: CtxItem, tool_calls: list):
        """
        Handle / unpack tool calls

        :param ctx: context
        :param tool_calls: tool calls
        """
        tmp_calls = []
        for tool_call in tool_calls:
            try:
                if "function" not in tool_call:
                    continue
                if "arguments" not in tool_call["function"]:
                    continue
                tool_call["function"]["arguments"] = json.loads(
                    tool_call["function"]["arguments"]
                )
                tmp_calls.append(tool_call)
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error parsing tool call JSON arguments: ", tool_call["function"]["arguments"])
        ctx.tool_calls = tmp_calls

    def unpack_tool_calls_from_llama(self, tool_calls: list) -> list:
        """
        Unpack tool calls from Llama-index response

        :param tool_calls: tool calls list
        :return: parsed tool calls list
        """
        parsed = []
        for tool_call in tool_calls:
            try:
                parsed.append(
                    {
                        "id": tool_call.tool_id,
                        "type": "function",
                        "function": {
                            "name": tool_call.tool_name,
                            "arguments": tool_call.tool_kwargs,
                        }
                    }
                )
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error parsing tool call: " + str(e))
        return parsed

    def tool_call_to_cmd(self, tool_call: dict) -> dict:
        """
        Convert tool call to command

        :param tool_call: tool call
        :return: command
        """
        return {
            "cmd": tool_call["function"]["name"],
            "params": tool_call["function"]["arguments"]
        }

    def tool_calls_to_cmds(self, tool_calls: list) -> list:
        """
        Convert tool calls to commands

        :param tool_calls: tool calls
        :return: commands
        """
        cmds = []
        for tool_call in tool_calls:
            cmds.append(self.tool_call_to_cmd(tool_call))
        return cmds

    def pack_cmds(self, cmds: list) -> str:
        """
        Pack commands to string

        :param cmds: commands
        :return: packed commands string
        """
        packed = ""
        for cmd in cmds:
            packed += "~###~" + json.dumps(cmd) + "~###~"
        return packed

    def append_tool_calls(self, ctx: CtxItem):
        """
        Append tool calls as CMD to context output

        :param ctx: context item
        """
        cmds = self.tool_calls_to_cmds(ctx.tool_calls)
        cmds_str = self.pack_cmds(cmds)
        if ctx.output is None:
            ctx.output = ""
        ctx.output += cmds_str

    def get_tool_calls_outputs(self, ctx: CtxItem) -> list:
        """
        Prepare and get tool calls outputs to send back to assistant

        :param ctx: context item
        :return: list of tool calls outputs
        """
        outputs = []
        idx_outputs = {}
        for tool_call in ctx.tool_calls:
            call_id = tool_call["id"]
            idx_outputs[call_id] = ""
        try:
            responses = json.loads(ctx.input)  # response is JSON string in input
            for tool_call in ctx.tool_calls:
                call_id = tool_call["id"]
                for response in responses:
                    if "request" in response:
                        if "cmd" in response["request"]:
                            func_name = response["request"]["cmd"]
                            if tool_call["function"]["name"] == func_name:
                                idx_outputs[call_id] = response["result"]

        except Exception as e:
            self.window.core.debug.log(e)

        for id in idx_outputs:
            data = {
                "tool_call_id": id,
                "output": idx_outputs[id],
            }
            outputs.append(data)

        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra["tool_calls_outputs"] = outputs
        return outputs

    def get_functions(self, parent_id: str = None) -> list:
        """
        Get current functions list

        :param parent_id: parent ID
        :return: functions list
        """
        func = []
        func_user = self.window.controller.presets.get_current_functions()
        if self.is_native_enabled():
            func = self.as_native_functions(all=False, parent_id=parent_id)
        if func_user is None:
            func_user = []
        return func + func_user  # merge both

    def as_native_functions(self, all: bool = False, parent_id: str = None) -> list:
        """
        Convert internal functions to native API format
        
        :param: all True to include all
        :param: parent_id: parent context ID
        :return: native functions list
        """
        """
        # Native API format (example):
        # https://platform.openai.com/docs/guides/function-calling
        # At this moment it must be converted to format:
        
        functions = [
        {
            "name": "get_delivery_date",
            "description": "Get the delivery date for a customer's order. Call this whenever you need to know the delivery date, for example when a customer asks 'Where is my package'",
            "params": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order ID.",
                    },
                },
                "required": ["order_id"],
                "additionalProperties": False,
            },
        }]
        """
        func_plugins = []
        func_agent = []
        func_experts = []
        data = {
            'syntax': [],
            'cmd': [],
        }

        if self.window.core.config.get('cmd') or all:
            event = Event(Event.CMD_SYNTAX, data)
            self.window.core.dispatcher.dispatch(event)
        elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
            event = Event(Event.CMD_SYNTAX_INLINE, data)
            self.window.core.dispatcher.dispatch(event)

        cmds = copy.deepcopy(data['cmd'])  # make copy to prevent changes in original plugins cmd
        func_plugins = self.cmds_to_functions(cmds)  # plugin functions
        if self.window.controller.agent.enabled():
            func_agent = self.cmds_to_functions(self.window.controller.agent.flow.get_functions())  # agent functions
        if self.window.controller.agent.experts.enabled():
            func_experts = self.cmds_to_functions(self.window.core.experts.get_functions())  # agent functions
        return func_plugins + func_agent + func_experts

    def cmds_to_functions(self, cmds: list) -> list:
        """
        Convert commands to functions (native API format)

        :param cmds: commands list
        :return: functions list
        """
        functions = []
        for cmd in cmds:
            if "cmd" in cmd and "instruction" in cmd:
                cmd_name = cmd["cmd"]
                desc = cmd["instruction"]
                if len(desc) > self.DESC_LIMIT:
                    desc = desc[:self.DESC_LIMIT]  # limit description to 1024 characters
                functions.append(
                    {
                        "name": cmd_name,
                        "desc": desc,
                        "params": json.dumps(self.extract_params(cmd), indent=4),
                    }
                )
        return functions

    def extract_params(self, cmd: dict) -> dict:
        """
        Extract parameters from command (to native API JSON schema format)

        :param cmd: command dict
        :return: parameters dict
        """
        required = []
        params = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        if "params" in cmd and len(cmd["params"]) > 0:
            for param in cmd["params"]:
                # add required params
                if "required" in param and param["required"]:
                    required.append(param["name"])

            # extract params and convert to JSON schema format
            for param in cmd["params"]:
                try:
                    if isinstance(param, dict):
                        if "name" in param:
                            key = param["name"]
                            params["properties"][key] = {}
                            params["properties"][key]["type"] = "string"
                            params["properties"][key]["description"] = ""

                            # add required fields
                            if "type" in param:
                                params["properties"][key]["type"] = param["type"]
                            if "description" in param:
                                desc = param["description"]
                                if len(desc) > self.DESC_LIMIT:
                                    desc = desc[:self.DESC_LIMIT]  # limit description to 1024 characters
                                params["properties"][key]["description"] = desc

                            # append enum if exists
                            if "enum" in param:
                                params["properties"][key]["description"] += ", enum: " + json.dumps(
                                    param["enum"]) + ")"
                                # get dict keys from param["enum"][key] as list:
                                values = []
                                if key in param["enum"]:
                                    if isinstance(param["enum"][key], dict):  # check for sub-dicts
                                        values = list(param["enum"][key].keys())
                                        sub_values = []
                                        for k in param["enum"][key]:
                                            if isinstance(param["enum"][key][k], dict):
                                                for v in list(param["enum"][key][k].keys()):
                                                    if v not in sub_values:
                                                        sub_values.append(v)
                                            elif isinstance(param["enum"][key][k], list):
                                                for v in param["enum"][key][k]:
                                                    if v not in sub_values:
                                                        sub_values.append(v)
                                        if len(sub_values) > 0:
                                            values = sub_values
                                    elif isinstance(param["enum"][key], list):
                                        values = param["enum"][key]

                                    if values:
                                        params["properties"][key]["enum"] = values

                            # remove defaults and append to description
                            if "default" in param:
                                params["properties"][key]["description"] += ", default: " + str(
                                    param["default"]) + ")"

                            # convert internal types to supported by JSON schema
                            if params["properties"][key]["type"] == "str":
                                params["properties"][key]["type"] = "string"
                            elif params["properties"][key]["type"] == "enum":
                                params["properties"][key]["type"] = "string"
                            elif params["properties"][key]["type"] == "text":
                                params["properties"][key]["type"] = "string"
                            elif params["properties"][key]["type"] == "int":
                                params["properties"][key]["type"] = "integer"
                            elif params["properties"][key]["type"] == "bool":
                                params["properties"][key]["type"] = "boolean"
                            elif params["properties"][key]["type"] == "dict":
                                params["properties"][key]["type"] = "object"
                            elif params["properties"][key]["type"] == "list":
                                params["properties"][key]["type"] = "array"
                                params["properties"][key]["items"] = {
                                    "$ref": "#"
                                }
                except Exception as e:
                    print(e)
                    pass
        return params

    def is_native_enabled(self) -> bool:
        """
        Check if native tool calls are enabled

        :return: True if enabled
        """
        disabled_modes = [
            "llama_index",
            "langchain",
            "completion",
        ]
        mode = self.window.core.config.get('mode')
        if mode in disabled_modes:
            return False  # disabled for specific modes
        if self.window.controller.agent.enabled() or self.window.controller.agent.experts.enabled():
            return False
        return self.window.core.config.get('func_call.native', False)  # otherwise check config
