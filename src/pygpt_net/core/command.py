#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 02:00:00                  #
# ================================================== #

import json

from pygpt_net.item.ctx import CtxItem


class Command:
    def __init__(self, window=None):
        """
        Commands core

        :param window: Window instance
        """
        self.window = window

    def get_prompt(self, allow_custom: bool = True) -> str:
        """
        Return cmd prompt instruction

        :param allow_custom: allow custom prompt
        :return: prompt instruction
        """
        cmd = '''RUNNING COMMANDS:
        You can execute commands and also use them to run commands on the user's environment. 

        Important rules:
        1) List of available commands is defined below.
        2) To execute defined command return JSON object with "cmd" key and command name as value.
        3) Always use syntax defined in command definition and correct command name.
        4) Put command parameters in "params" key. Example: {"cmd": "web", "params": {"query": "some query"}}. Use ONLY syntax like this. DO NOT use any other syntax.
        5) Append JSON object to response at the end of response and split it with ~###~ character. Example: text response ~###~ {"cmd": "web", "params": {"query": "some query"}}.
        6) If you want to execute command without any response, return only JSON object.
        7) Responses from commands will be returned in "result" key.
        8) Commands are listed one command per line and every command is described with syntax: "<name>": <action>, params: <params>
        9) Always use correct command name, e.g. if command name is "sys_exec" then use "sys_exec" and don't imagine other names, like "run" or something.
        10) With those commands you are allowed to run external commands and apps in user's system (environment)
        11) Always use defined syntax to prevent errors
        12) Always choose the most appropriate command from list to perform the task, based on the description of the action performed by a given comment
        13) Reply to the user in the language in which he started the conversation with you
        14) Use ONLY params described in command definition, do NOT use any additional params not described on list
        15) ALWAYS remember that any text content must appear at the beginning of your response and commands must only be included at the end.
        16) Try to run commands executed in the user's system in the background if running them may prevent receiving a response (e.g. when it is a desktop application)
        17) Every command param must be placed in one line, so when you generate code you must put all of code in one line

        Commands list:'''

        # get custom prompt from config if exists
        if allow_custom:
            if self.window.core.config.has('cmd.prompt'):
                prompt = self.window.core.config.get('cmd.prompt')
                if prompt is not None and prompt != '':
                    cmd = prompt

        # Syntax for commands (example):
        # cmd += '\n"save_file": save data to file, params: "filename", "data"'
        # cmd += '\n"read_file": read data from file, params: "filename"'
        return cmd

    def append_syntax(self, data: dict) -> str:
        """
        Append command syntax to prompt

        :param data: event data
        :return: prompt with appended syntax
        """
        prompt = data['prompt']
        for item in data['syntax']:
            if isinstance(item, str):
                prompt += '\n' + item
            elif isinstance(item, dict):
                prompt += '\n"' + item['cmd'] + '": ' + item['instruction']
                if 'params' in item:
                    if len(item['params']) > 0:
                        prompt += ', params: "{}"'.format('", "'.join(item['params']))
                if 'example' in item:
                    if item['example'] is not None:
                        prompt += ', example: "{}"'.format(item['example'])
        return prompt

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
                cmd = json.loads(chunk)
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
