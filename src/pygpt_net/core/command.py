#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.17 13:00:00                  #
# ================================================== #

import copy
import json

from pygpt_net.item.ctx import CtxItem


class Command:
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
            prompt += "\n"
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
        Prepare and get tool calls outputs

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
