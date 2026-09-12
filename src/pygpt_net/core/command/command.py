#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.20 09:00:00                  #
# ================================================== #

import copy
import json
import re
from typing import Optional, Dict, Any, List

from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_COMPLETION,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_AUDIO,
)
from pygpt_net.core.events import Event
from pygpt_net.core.types.tools import (
    PERSIST_HIDDEN_TOOL_CALLS,
    is_hidden_tool as is_hidden_tool_name,
    register_hidden_tool_definition,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


class Command:
    DESC_LIMIT = 1024
    _RE_CMD_PRESENCE = re.compile(r'<tool>\s*{.*}\s*</tool>', re.DOTALL)
    _RE_TOOL_BLOCKS = re.compile(r'<tool>(.*?)</tool>', re.DOTALL)

    def __init__(self, window=None):
        """
        Commands core

        :param window: Window instance
        """
        self.window = window

    @staticmethod
    def _tool_name(value: Any) -> str:
        """Extract a tool/command name from supported definition/call shapes."""
        if isinstance(value, str):
            return value.strip()
        if not isinstance(value, dict):
            return ""
        name = value.get("cmd") or value.get("name")
        function = value.get("function")
        if not name and isinstance(function, dict):
            name = function.get("name")
        return str(name or "").strip()

    def is_tool_hidden(self, name: str, definition: Optional[Dict[str, Any]] = None) -> bool:
        """Return True when a tool must be omitted from the conversation UI."""
        if isinstance(definition, dict) and definition.get("hidden") is True:
            register_hidden_tool_definition(definition)
            return True
        value = str(name or "").strip()
        if not value:
            return False
        if is_hidden_tool_name(value):
            return True

        # Current command syntax also covers dynamic tools supplied directly by
        # plugins instead of BasePlugin.add_cmd().
        for item in getattr(self.window.core.ctx, "current_cmd", None) or []:
            if (isinstance(item, dict)
                    and self._tool_name(item) == value
                    and item.get("hidden") is True):
                register_hidden_tool_definition(item)
                return True

        # BasePlugin.add_cmd(hidden=True) stores the marker on the command option.
        # Inspect registered plugins as a history/reload fallback even when the
        # command has not yet been advertised in the current model prompt.
        try:
            for plugin in self.window.core.plugins.all().values():
                option = getattr(plugin, "options", {}).get(f"cmd.{value}")
                if isinstance(option, dict) and option.get("hidden") is True:
                    register_hidden_tool_definition({"cmd": value, "hidden": True})
                    return True
        except Exception:
            pass
        return False

    def visible_tools(self, values: List[Any]) -> List[Any]:
        """Filter hidden commands/tool calls while preserving input objects/order."""
        result = []
        for value in values or []:
            name = self._tool_name(value)
            if name and self.is_tool_hidden(name, value if isinstance(value, dict) else None):
                continue
            result.append(value)
        return result

    def visible_tool_names(self, names: List[str]) -> List[str]:
        """Return only names that may be surfaced in conversation UI statuses."""
        return [
            str(name)
            for name in (names or [])
            if str(name) and not self.is_tool_hidden(str(name))
        ]

    def tool_calls_for_storage(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply the code-level hidden-tool persistence policy."""
        if PERSIST_HIDDEN_TOOL_CALLS:
            return list(tool_calls or [])
        return self.visible_tools(tool_calls or [])

    def commands_for_storage(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return command metadata that may be written to durable context storage."""
        if PERSIST_HIDDEN_TOOL_CALLS:
            return list(commands or [])
        return self.visible_tools(commands or [])

    def tool_results_for_storage(self, results: List[Any]) -> List[Any]:
        """Remove model-facing results that belong to non-persisted hidden tools."""
        if PERSIST_HIDDEN_TOOL_CALLS:
            return list(results or [])
        stored = []
        for result in results or []:
            name = ""
            if isinstance(result, dict):
                request = result.get("request")
                if isinstance(request, dict):
                    name = str(request.get("cmd") or request.get("name") or "")
                if not name:
                    name = str(result.get("cmd") or "")
            if name and self.is_tool_hidden(name):
                continue
            stored.append(result)
        return stored

    def extra_for_storage(self, extra: Any) -> Any:
        """Sanitize compatibility tool caches before writing context extras."""
        if PERSIST_HIDDEN_TOOL_CALLS or not isinstance(extra, dict):
            return extra
        stored = copy.deepcopy(extra)
        for key in ("tool_calls", "prev_tool_calls"):
            if isinstance(stored.get(key), list):
                values = self.visible_tools(stored[key])
                if values:
                    stored[key] = values
                else:
                    stored.pop(key, None)
        if isinstance(stored.get("tool_output"), list):
            outputs = self.tool_results_for_storage(stored["tool_output"])
            # Plugin output caches usually carry the command at top level rather
            # than under request; apply the same rule explicitly.
            outputs = [
                value for value in outputs
                if not (
                    isinstance(value, dict)
                    and str(value.get("cmd") or "")
                    and self.is_tool_hidden(str(value.get("cmd") or ""))
                )
            ]
            if outputs:
                stored["tool_output"] = outputs
            else:
                stored.pop("tool_output", None)
        return stored

    def output_for_storage(self, text: Optional[str]) -> Optional[str]:
        """Remove hidden legacy ``<tool>`` requests from durable assistant text."""
        if PERSIST_HIDDEN_TOOL_CALLS or text is None:
            return text

        def replace(match):
            command = self.extract_cmd(match.group(1))
            if isinstance(command, dict):
                name = self._tool_name(command)
                if name and self.is_tool_hidden(name, command):
                    return ""
            return match.group(0)

        return self._RE_TOOL_BLOCKS.sub(replace, str(text))

    def append_syntax(
            self,
            data: Dict[str, Any],
            mode: str = None,
            model: ModelItem = None
    ) -> str:
        """
        Append command syntax to the system prompt

        :param data: event data
        :param mode: mode
        :param model: model item
        :return: prompt with appended syntax
        """
        prompt = data['prompt']
        core = self.window.core
        cmd_prompt = core.prompt.get('cmd')
        extra = ""
        schema = self.extract_syntax(data['cmd'])
        if schema:
            if core.config.get('mode') == MODE_ASSISTANT:
                extra = core.prompt.get('cmd.extra.assistants')
            else:
                extra = core.prompt.get('cmd.extra')
        if prompt.strip() != "":
            prompt += "\n\n"
        prompt += cmd_prompt.strip().replace("{extra}", extra).replace("{schema}", schema)
        return prompt

    def extract_syntax(
            self,
            cmds: List[Dict[str, Any]]
    ) -> str:
        """
        Extract syntax from commands

        :param cmds: commands list
        :return: JSON string with commands usage syntax
        """
        data: Dict[str, Any] = {}
        self.window.core.ctx.current_cmd = copy.deepcopy(cmds)

        for cmd in cmds:
            register_hidden_tool_definition(cmd)
            if "cmd" in cmd and "instruction" in cmd:
                cmd_name = cmd["cmd"]
                data_cmd = {"help": cmd["instruction"]}
                if "params" in cmd and len(cmd["params"]) > 0:
                    params_out: Dict[str, Any] = {}
                    for param in cmd["params"]:
                        try:
                            if isinstance(param, dict) and "name" in param:
                                key = param["name"]
                                p = dict(param)
                                p.pop("name", None)
                                if "required" in p:
                                    if p["required"] is False:
                                        p["optional"] = True
                                    p.pop("required", None)
                                if p.get("type") == "str":
                                    p.pop("type", None)
                                if "description" in p:
                                    p["help"] = p["description"]
                                    p.pop("description", None)
                                params_out[key] = p
                        except Exception:
                            pass
                    if params_out:
                        data_cmd["params"] = params_out
                data[cmd_name] = data_cmd

        self.window.core.ctx.current_cmd_schema = data
        return json.dumps(data)

    def has_cmds(self, text: str) -> bool:
        """
        Check if text has command execute syntax

        :param text: text to check
        :return: True if text has commands
        """
        if text is None:
            return False
        return bool(self._RE_CMD_PRESENCE.search(text))

    def extract_cmds(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract commands from text

        :param text: text to extract commands from
        :return: list of commands (dict)
        """
        cmds: List[Dict[str, Any]] = []
        try:
            chunks = self._RE_TOOL_BLOCKS.findall(text)
            for chunk in chunks:
                cmd = self.extract_cmd(chunk)
                if cmd is not None:
                    cmds.append(cmd)
        except Exception:
            pass
        return cmds

    def strip_cmds(self, text: Optional[str]) -> Optional[str]:
        """Remove legacy <tool> request blocks from assistant-visible text."""
        if text is None:
            return None
        return self._RE_TOOL_BLOCKS.sub("", str(text)).strip()

    def extract_cmd(self, chunk: str) -> Optional[Dict[str, Any]]:
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
            except json.JSONDecodeError:
                pass
        return cmd

    def from_commands(
            self,
            cmds: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Unpack commands to execution list

        :param cmds: commands list
        :return parsed commands
        """
        return [cmd for cmd in cmds if 'cmd' in cmd]

    def unpack_tool_calls(
            self,
            tool_calls: List
    ) -> List[Dict[str, Any]]:
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

    def unpack_tool_calls_responses(
            self,
            tool_calls: List
    ) -> List[Dict[str, Any]]:
        """
        Unpack tool calls from OpenAI response

        :param tool_calls: tool calls list
        :return: parsed tool calls list
        """
        parsed = []
        for tool_call in tool_calls:
            try:
                if not hasattr(tool_call, 'name'):
                    continue
                parsed.append(
                    {
                        "id": tool_call.id,
                        "call_id": getattr(tool_call, "call_id", None) or tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": json.loads(tool_call.arguments)
                        }
                    }
                )
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error parsing tool call: " + str(e))
        return parsed

    def unpack_tool_calls_chunks(
            self,
            ctx: CtxItem,
            tool_calls: List[Dict[str, Any]],
            append_output: bool = False,
    ):
        """
        Handle / unpack tool calls

        :param ctx: context
        :param tool_calls: tool calls
        :param append_output: if True then append output to context output
        """
        tmp_calls = []
        for tool_call in tool_calls:
            try:
                if "function" not in tool_call:
                    continue
                if "arguments" not in tool_call["function"]:
                    continue
                if not isinstance(tool_call["function"]["arguments"], str):
                    continue
                tool_call["function"]["arguments"] = json.loads(
                    tool_call["function"]["arguments"]
                )
                tmp_calls.append(tool_call)
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error parsing tool call JSON arguments: ", tool_call["function"]["arguments"])
        ctx.tool_calls = tmp_calls

        if append_output:
            stored_tool_calls = self.tool_calls_for_storage(ctx.tool_calls)
            if stored_tool_calls:
                ctx.extra["tool_calls"] = stored_tool_calls
            else:
                ctx.extra.pop("tool_calls", None)
            ctx.extra["tool_output"] = []

    def unpack_tool_calls_from_llama(
            self,
            tool_calls: List
    ) -> List[Dict[str, Any]]:
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

    def tool_call_to_cmd(
            self,
            tool_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert tool call to command

        :param tool_call: tool call
        :return: command
        """
        return {
            "cmd": tool_call["function"]["name"],
            "params": tool_call["function"]["arguments"]
        }

    def tool_calls_to_cmds(
            self,
            tool_calls: List[Dict[str, Any]]
    ) -> list:
        """
        Convert tool calls to commands

        :param tool_calls: tool calls
        :return: commands
        """
        return [self.tool_call_to_cmd(tool_call) for tool_call in tool_calls]

    def pack_cmds(
            self,
            cmds: List[Dict[str, Any]]
    ) -> str:
        """
        Pack commands to string

        :param cmds: commands
        :return: packed commands string
        """
        return "".join(
            "<tool>" + json.dumps(cmd, separators=(',', ':')) + "</tool>"
            for cmd in cmds
        )

    def append_tool_calls(self, ctx: CtxItem):
        """
        Append tool calls as CMD to context output

        :param ctx: context item
        """
        cmds_str = self.pack_cmds(self.tool_calls_to_cmds(ctx.tool_calls))
        if ctx.output is None:
            ctx.output = ""
        ctx.output += cmds_str

    def get_tool_calls_outputs(self, ctx: CtxItem) -> list:
        """
        Prepare and get tool calls outputs to send back to assistant

        :param ctx: context item
        :return: list of tool calls outputs
        """
        idx_outputs = {tool_call["id"]: "" for tool_call in ctx.tool_calls}
        try:
            responses = json.loads(ctx.input)
            last_by_name: Dict[str, Any] = {}
            for response in responses:
                req = response.get("request")
                if isinstance(req, dict) and "cmd" in req:
                    last_by_name[req["cmd"]] = response.get("result")
            for tool_call in ctx.tool_calls:
                name = tool_call["function"]["name"]
                if name in last_by_name:
                    idx_outputs[tool_call["id"]] = last_by_name[name]
        except Exception as e:
            self.window.core.debug.log(e)

        outputs = [{"tool_call_id": id_, "output": out} for id_, out in idx_outputs.items()]
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra["tool_calls_outputs"] = outputs
        return outputs

    def get_functions(
            self,
            parent_id: Optional[str] = None,
            force: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get current functions list

        :param parent_id: parent ID
        :param force: force to get native functions
        :return: functions list
        """
        func = []
        func_user = self.window.controller.presets.get_current_functions()
        if self.is_native_enabled(force=force):
            func = self.as_native_functions(all=False, parent_id=parent_id)
        if func_user is None:
            func_user = []
        return func + func_user

    def as_native_functions(
            self,
            all: bool = False,
            parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
            "description": "Get the delivery date for a customer's order. Call this whenever you need to know 
            the delivery date, for example when a customer asks 'Where is my package'",
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
        data = {
            'syntax': [],
            'cmd': [],
        }

        if self.window.core.config.get('cmd') or all:
            event = Event(Event.CMD_SYNTAX, data)
            self.window.dispatch(event)
        elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
            event = Event(Event.CMD_SYNTAX_INLINE, data)
            self.window.dispatch(event)

        cmds = copy.deepcopy(data['cmd'])
        func_plugins = self.cmds_to_functions(cmds)
        if self.window.controller.agent.legacy.enabled():
            func_agent = self.cmds_to_functions(self.window.controller.agent.legacy.get_functions())
        return func_plugins + func_agent

    def cmds_to_functions(
            self,
            cmds: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert commands to functions (native API format)

        :param cmds: commands list
        :return: functions list
        """
        functions = []
        limit = self.DESC_LIMIT
        for cmd in cmds:
            register_hidden_tool_definition(cmd)
            if "cmd" in cmd and "instruction" in cmd:
                cmd_name = cmd["cmd"]
                desc = cmd["instruction"]
                if len(desc) > limit:
                    desc = desc[:limit]
                functions.append(
                    {
                        "name": cmd_name,
                        "desc": desc,
                        "params": json.dumps(self.extract_params(cmd), separators=(',', ':')),
                    }
                )
        return functions

    def extract_params(
            self,
            cmd: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        params_list = cmd.get("params") or []
        if params_list:
            for param in params_list:
                if isinstance(param, dict) and param.get("required"):
                    required.append(param["name"])

            if required:
                params["required"] = required

            type_map = {
                "str": "string",
                "enum": "string",
                "text": "string",
                "int": "integer",
                "bool": "boolean",
                "dict": "object",
                "list": "array",
                "float": "number",
                "any": "string",
            }

            limit = self.DESC_LIMIT
            for param in params_list:
                try:
                    if isinstance(param, dict) and "name" in param:
                        key = param["name"]
                        prop: Dict[str, Any] = {}
                        prop["type"] = param.get("type", "string")
                        prop["description"] = ""
                        if "type" in param and param["type"] in type_map:
                            prop["type"] = type_map[param["type"]]
                        if "description" in param:
                            desc = param["description"]
                            if len(desc) > limit:
                                desc = desc[:limit]
                            prop["description"] = desc
                        if "enum" in param:
                            prop["description"] += ", enum: " + json.dumps(param["enum"]) + ")"
                            values = []
                            enum_block = param["enum"].get(key) if isinstance(param["enum"], dict) else None
                            if isinstance(enum_block, dict):
                                values = list(enum_block.keys())
                                sub_values = []
                                for k in enum_block:
                                    if isinstance(enum_block[k], dict):
                                        for v in list(enum_block[k].keys()):
                                            if v not in sub_values:
                                                sub_values.append(v)
                                    elif isinstance(enum_block[k], list):
                                        for v in enum_block[k]:
                                            if v not in sub_values:
                                                sub_values.append(v)
                                if sub_values:
                                    values = sub_values
                            elif isinstance(enum_block, list):
                                values = enum_block
                            if values:
                                prop["enum"] = values
                        if "default" in param:
                            prop["description"] += ", default: " + str(param["default"]) + ")"
                        if prop["type"] == "array":
                            prop["items"] = {"type": "string"}
                        params["properties"][key] = prop
                except Exception as e:
                    print(e)
                    pass
        return params

    def is_native_enabled(self, force: bool = False, model: str = None) -> bool:
        """
        Check if native tool calls are enabled

        :param force: force check, ignore config
        :param model: model name (optional)
        :return: True if enabled
        """
        disabled_modes = [
            # MODE_LLAMA_INDEX,
            # MODE_LANGCHAIN,
            MODE_COMPLETION,
        ]
        mode = self.window.core.config.get('mode')

        if mode in disabled_modes:
            return False

        if not force:
            if model is None:
                model = self.window.core.config.get('model')  # get from globals
            if model:
                model_data = self.window.core.models.get(model)
                if model_data:
                    if not self.window.core.models.is_tool_call_allowed(mode, model_data):
                        return False

        return self.window.core.config.get('func_call.native', False)

    def is_cmd(self, inline: bool = True) -> bool:
        """
        Check if tool execute is enabled

        :param inline: check if inline plugin is enabled
        :return: True if command is enabled
        """
        return bool(
            self.window.core.config.get('cmd')
            or (inline and self.window.controller.plugins.is_type_enabled("cmd.inline"))
        )

    def is_enabled(self, cmd: str) -> bool:
        """
        Check if command is enabled

        :param cmd: command
        :return: True if command is enabled
        """
        # Internal autonomous controls are advertised by the agent controller
        # rather than by a user-toggleable plugin, but execution still goes
        # through the same chat command/tool lifecycle.
        if self.window.controller.agent.legacy.is_tool_enabled(cmd):
            return True

        enabled_cmds = set()

        def collect(event_type):
            data = {
                'prompt': "",
                'silent': True,
                'force': True,
                'syntax': [],
                'cmd': [],
            }
            event = Event(event_type, data)
            self.window.dispatch(event)
            if event.data and "cmd" in event.data and isinstance(event.data["cmd"], list):
                for item in event.data["cmd"]:
                    if "cmd" in item:
                        enabled_cmds.add(item["cmd"])

        collect(Event.CMD_SYNTAX)
        collect(Event.CMD_SYNTAX_INLINE)

        return cmd in enabled_cmds

    def is_model_supports_tools(
            self,
            mode: str,
            model: ModelItem = None) -> bool:
        """
        Check if model supports tools

        :param mode: mode
        :param model: model item
        :return: True if model supports tools
        """
        return True  # TMP allowed all
        if model is None:
            return False
        disabled_models = [
            "deepseek-r1:1.5b",
            "deepseek-r1:7b",
            "llama2",
            #"llama3.1",
            "codellama",
        ]
        if model.id is not None:
            for disabled_model in disabled_models:
                if (model.get_provider() == "ollama"
                        and model.id.startswith(disabled_model)):
                    return False
        return True