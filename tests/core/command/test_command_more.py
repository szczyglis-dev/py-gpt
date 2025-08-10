#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import json
import re
from types import SimpleNamespace
import pytest
from unittest.mock import Mock

from pygpt_net.core.command import Command
from pygpt_net.core.events import Event
from pygpt_net.core.types import MODE_ASSISTANT, MODE_COMPLETION


def make_window():
    prompt = {
        'cmd': '{extra}{schema}',
        'cmd.extra': 'EXTRA',
        'cmd.extra.assistants': 'ASSIST'
    }
    config = {
        'mode': None,
        'cmd': False,
        'func_call.native': False,
        'agent.func_call.native': False,
        'experts.func_call.native': False,
        'model': None,
    }
    ctx = SimpleNamespace(current_cmd=None, current_cmd_schema=None)
    models = SimpleNamespace()
    models.get = lambda key: None
    models.is_tool_call_allowed = lambda mode, model_data: True
    experts = SimpleNamespace(get_functions=lambda: [])
    debug = SimpleNamespace(log=Mock())
    core = SimpleNamespace(prompt=prompt, config=config, ctx=ctx, models=models, experts=experts, debug=debug)
    presets = SimpleNamespace(get_current_functions=lambda: [])
    plugins = SimpleNamespace(is_type_enabled=lambda t: False)
    agent = SimpleNamespace(
        legacy=SimpleNamespace(enabled=lambda check_inline=True: False, get_functions=lambda: []),
        experts=SimpleNamespace(enabled=lambda: False)
    )
    controller = SimpleNamespace(presets=presets, plugins=plugins, agent=agent)
    window = SimpleNamespace(core=core, controller=controller, dispatch=lambda event: None)
    return window


def test_extract_syntax_transforms_params_and_sets_ctx():
    window = make_window()
    command = Command(window)
    cmds = [
        {
            "cmd": "read",
            "instruction": "Read file",
            "params": [
                {"name": "path", "type": "str", "description": "File path", "required": True},
                {"name": "opt", "type": "int", "description": "optional", "required": False, "default": 5}
            ]
        },
        {
            "cmd": "no_params",
            "instruction": "No params",
            "params": []
        },
        {"not_a_cmd": "skip"}
    ]
    result = json.loads(command.extract_syntax(cmds))
    assert "read" in result and "no_params" in result
    assert result["read"]["help"] == "Read file"
    assert result["read"]["params"]["path"] == {"help": "File path"}
    opt = result["read"]["params"]["opt"]
    assert opt["type"] == "int"
    assert opt["help"] == "optional"
    assert opt["optional"] is True
    assert opt["default"] == 5
    assert "params" not in result["no_params"]
    assert window.core.ctx.current_cmd == cmds
    assert window.core.ctx.current_cmd_schema == result


def test_append_syntax_uses_extra_and_schema(monkeypatch):
    window = make_window()
    window.core.prompt = {'cmd': 'CMD {extra} {schema}', 'cmd.extra': 'EXTRA', 'cmd.extra.assistants': 'ASSIST'}
    window.core.config['mode'] = None
    command = Command(window)
    monkeypatch.setattr(command, "extract_syntax", lambda x: '{"a":1}')
    out = command.append_syntax({'prompt': 'Hello', 'cmd': []})
    assert out == "Hello\n\nCMD EXTRA {\"a\":1}"
    window.core.config['mode'] = MODE_ASSISTANT
    out2 = command.append_syntax({'prompt': '', 'cmd': []})
    assert out2 == "CMD ASSIST {\"a\":1}"


def test_has_cmds_and_extract_cmd_variants():
    window = make_window()
    command = Command(window)
    assert not command.has_cmds(None)
    assert command.has_cmds('<tool>{"a":1}</tool>')
    text = 'prefix <tool>{"cmd":"r","params":{"p":[1]}}</tool> foo <tool>{"read":{"path":["x"]}}</tool> <tool>notjson</tool>'
    cmds = command.extract_cmds(text)
    assert len(cmds) == 2
    assert cmds[0]["cmd"] == "r"
    assert cmds[1]["cmd"] == "read"
    assert command.extract_cmd('not a json') is None
    assert command.extract_cmd('{"cmd":"ok","params":{"x":1}}') == {"cmd": "ok", "params": {"x": 1}}
    assert command.extract_cmd('{"read_file": {"path": ["my_cars.txt"]}}') == {"cmd": "read_file", "params": {"path": ["my_cars.txt"]}}


def test_from_commands_filters_without_cmd():
    window = make_window()
    command = Command(window)
    input_cmds = [{'a': 1}, {'cmd': 'x', 'params': {}}, {'cmd': 'y'}]
    out = command.from_commands(input_cmds)
    assert out == [{'cmd': 'x', 'params': {}}, {'cmd': 'y'}]


def test_unpack_tool_calls_parses_and_logs_on_error():
    window = make_window()
    window.core.debug.log.reset_mock()
    valid = SimpleNamespace(id="1", function=SimpleNamespace(name="func1", arguments=json.dumps({"a": 1})))
    invalid = SimpleNamespace(id="2", function=SimpleNamespace(name="func2", arguments="badjson"))
    command = Command(window)
    out = command.unpack_tool_calls([valid, invalid])
    assert out == [{"id": "1", "type": "function", "function": {"name": "func1", "arguments": {"a": 1}}}]
    assert window.core.debug.log.called


def test_unpack_tool_calls_responses_parses_and_skips_missing_name():
    window = make_window()
    window.core.debug.log.reset_mock()
    valid = SimpleNamespace(id="1", name="func1", arguments=json.dumps({"a": 1}))
    missing_name = SimpleNamespace(id="2")
    bad_json = SimpleNamespace(id="3", name="bad", arguments="notjson")
    command = Command(window)
    out = command.unpack_tool_calls_responses([valid, missing_name, bad_json])
    assert out[0]["id"] == "1"
    assert out[0]["function"]["name"] == "func1"
    assert window.core.debug.log.called


def test_unpack_tool_calls_chunks_with_append_output_and_error():
    window = make_window()
    window.core.debug.log.reset_mock()
    ctx = SimpleNamespace(tool_calls=None, extra={}, input=None, output=None)
    tool_calls = [
        {"id": "1", "function": {"name": "f", "arguments": json.dumps({"a": 1})}},
        {"id": "2", "function": {"name": "f2", "arguments": {"not": "str"}}},
        {"id": "3", "function": {"name": "f3", "arguments": "badjson"}},
    ]
    command = Command(window)
    command.unpack_tool_calls_chunks(ctx, tool_calls, append_output=True)
    assert isinstance(ctx.tool_calls, list)
    assert len(ctx.tool_calls) == 1
    assert ctx.extra["tool_calls"] == ctx.tool_calls
    assert ctx.extra["tool_output"] == []
    assert window.core.debug.log.called


def test_unpack_tool_calls_from_llama_parses_and_logs_on_error():
    window = make_window()
    window.core.debug.log.reset_mock()
    good = SimpleNamespace(tool_id="tid", tool_name="tname", tool_kwargs={"k": 1})
    bad = SimpleNamespace()
    command = Command(window)
    out = command.unpack_tool_calls_from_llama([good, bad])
    assert out == [{"id": "tid", "type": "function", "function": {"name": "tname", "arguments": {"k": 1}}}]
    assert window.core.debug.log.called


def test_tool_call_to_cmd_and_tool_calls_to_cmds_and_pack_and_append(monkeypatch):
    window = make_window()
    command = Command(window)
    tc = {"function": {"name": "do", "arguments": {"x": 1}}, "id": "1"}
    cmd = command.tool_call_to_cmd(tc)
    assert cmd == {"cmd": "do", "params": {"x": 1}}
    cmds = command.tool_calls_to_cmds([tc])
    assert cmds == [cmd]
    packed = command.pack_cmds(cmds)
    assert "<tool>{\"cmd\": \"do\", \"params\": {\"x\": 1}}</tool>" in packed
    ctx = SimpleNamespace(tool_calls=[tc], output=None)
    command.append_tool_calls(ctx)
    assert ctx.output is not None
    found = re.findall(r"<tool>(.*?)</tool>", ctx.output)
    assert json.loads(found[0]) == cmd


def test_get_tool_calls_outputs_parses_input_and_handles_bad_json():
    window = make_window()
    window.core.debug.log.reset_mock()
    ctx = SimpleNamespace(tool_calls=[{"id": "1", "function": {"name": "f"}}], input=json.dumps([{"request": {"cmd": "f"}, "result": "OK"}]), extra={})
    command = Command(window)
    out = command.get_tool_calls_outputs(ctx)
    assert out == [{"tool_call_id": "1", "output": "OK"}]
    assert ctx.extra["tool_calls_outputs"] == out
    ctx2 = SimpleNamespace(tool_calls=[{"id": "2", "function": {"name": "g"}}], input="badjson", extra=None)
    window.core.debug.log.reset_mock()
    out2 = command.get_tool_calls_outputs(ctx2)
    assert window.core.debug.log.called
    assert out2 == [{"tool_call_id": "2", "output": ""}]
    assert isinstance(ctx2.extra, dict)
    assert ctx2.extra["tool_calls_outputs"] == out2


def test_get_functions_merges_native_and_user(monkeypatch):
    window = make_window()
    command = Command(window)
    window.controller.presets.get_current_functions = lambda: [{"name": "user"}]
    monkeypatch.setattr(command, "is_native_enabled", lambda force=False: False)
    assert command.get_functions() == [{"name": "user"}]
    monkeypatch.setattr(command, "is_native_enabled", lambda force=False: True)
    monkeypatch.setattr(command, "as_native_functions", lambda all=False, parent_id=None: [{"name": "native"}])
    assert command.get_functions() == [{"name": "native"}, {"name": "user"}]


def test_as_native_functions_dispatch_and_agent_expert_calls(monkeypatch):
    window = make_window()
    def dispatch(event):
        if event.type == Event.CMD_SYNTAX:
            event.data["cmd"] = [{"cmd": "plugin_cmd", "instruction": "p"}]
        elif event.type == Event.CMD_SYNTAX_INLINE:
            event.data["cmd"] = [{"cmd": "inline_cmd", "instruction": "i"}]
    window.dispatch = dispatch
    window.controller.agent.legacy = SimpleNamespace(enabled=lambda check_inline=True: True, get_functions=lambda: [{"cmd": "agent_cmd", "instruction": "a"}])
    window.controller.agent.experts = SimpleNamespace(enabled=lambda: False)
    window.core.experts = SimpleNamespace(get_functions=lambda: [{"cmd": "expert_cmd", "instruction": "e"}])
    command = Command(window)
    def fake_cmds_to_functions(cmds):
        if any(c.get("cmd") == "plugin_cmd" for c in cmds):
            return [{"name": "plugin"}]
        if any(c.get("cmd") == "agent_cmd" for c in cmds):
            return [{"name": "agent"}]
        if any(c.get("cmd") == "expert_cmd" for c in cmds):
            return [{"name": "expert"}]
        return []
    monkeypatch.setattr(command, "cmds_to_functions", fake_cmds_to_functions)
    out = command.as_native_functions(all=False, parent_id=None)
    assert {"name": "agent"} in out and {"name": "expert"} in out


def test_cmds_to_functions_and_extract_params_behavior():
    window = make_window()
    command = Command(window)
    long_desc = "x" * (Command.DESC_LIMIT + 10)
    cmds = [
        {
            "cmd": "doit",
            "instruction": long_desc,
            "params": [
                {"name": "p1", "type": "str", "description": "desc1", "required": True},
                {"name": "p2", "type": "int", "description": "desc2", "default": 42}
            ]
        }
    ]
    funcs = command.cmds_to_functions(cmds)
    assert funcs[0]["name"] == "doit"
    assert len(funcs[0]["desc"]) == Command.DESC_LIMIT
    params_schema = json.loads(funcs[0]["params"])
    assert "p1" in params_schema["properties"]
    assert params_schema["required"] == ["p1"]
    assert params_schema["properties"]["p2"]["type"] == "integer"


def test_extract_params_complex_enums_and_types():
    window = make_window()
    command = Command(window)
    cmd = {
        "params": [
            {"name": "a", "type": "str", "description": "A", "required": True},
            {"name": "b", "type": "int", "description": "B", "default": 2},
            {"name": "c", "type": "list", "description": "C", "enum": {"c": ["x", "y"]}},
            {"name": "d", "type": "enum", "description": "D", "enum": {"d": {"one": ["u", "v"], "two": ["w"]}}}
        ]
    }
    params = command.extract_params(cmd)
    assert params["required"] == ["a"]
    assert params["properties"]["a"]["type"] == "string"
    assert params["properties"]["b"]["type"] == "integer"
    assert "enum" in params["properties"]["c"] and params["properties"]["c"]["enum"] == ["x", "y"]
    assert "enum" in params["properties"]["d"] and set(params["properties"]["d"]["enum"]) == {"u", "v", "w"}


def test_is_native_enabled_various_branches():
    window = make_window()
    command = Command(window)
    window.core.config['mode'] = MODE_COMPLETION
    assert command.is_native_enabled() is False
    window.core.config['mode'] = None
    window.core.config['model'] = "m1"
    window.core.models.get = lambda k: SimpleNamespace(id="m1")
    window.core.models.is_tool_call_allowed = lambda mode, model_data: False
    assert command.is_native_enabled() is False
    window.core.models.is_tool_call_allowed = lambda mode, model_data: True
    window.controller.agent.legacy = SimpleNamespace(enabled=lambda check_inline=True: True)
    window.core.config['agent.func_call.native'] = True
    assert command.is_native_enabled() is True
    window.controller.agent.legacy = SimpleNamespace(enabled=lambda check_inline=True: False)
    window.controller.agent.experts = SimpleNamespace(enabled=lambda: True)
    window.core.config['experts.func_call.native'] = False
    assert command.is_native_enabled() is False
    window.core.config['func_call.native'] = True
    assert command.is_native_enabled(force=True) is True


def test_is_cmd_and_is_enabled_with_dispatch_behavior():
    window = make_window()
    window.core.config['cmd'] = True
    command = Command(window)
    assert command.is_cmd() is True
    window.core.config['cmd'] = False
    window.controller.plugins = SimpleNamespace(is_type_enabled=lambda t: True)
    assert command.is_cmd(inline=True) is True
    def dispatch(event):
        if event.name == Event.CMD_SYNTAX:
            event.data["cmd"] = [{"cmd": "allowed"}]
        if event.name == Event.CMD_SYNTAX_INLINE:
            event.data["cmd"] = [{"cmd": "inline_allowed"}]
    window.dispatch = dispatch
    assert command.is_enabled("allowed") is True
    assert command.is_enabled("inline_allowed") is True
    assert command.is_enabled("not_present") is False


def test_is_model_supports_tools_always_true():
    window = make_window()
    command = Command(window)
    assert command.is_model_supports_tools("any", None) is True
    class M:
        def __init__(self):
            self.id = "deepseek-r1:1.5bX"
        def get_provider(self):
            return "ollama"
    assert command.is_model_supports_tools("any", M()) is True