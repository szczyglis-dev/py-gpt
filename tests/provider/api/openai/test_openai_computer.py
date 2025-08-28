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
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from pygpt_net.provider.api.openai.computer import Computer

@pytest.fixture
def fake_window():
    fake_combo = MagicMock()
    fake_combo.currentIndex.return_value = 0
    fake_combo.itemData.return_value = {"env": "test"}
    fake_ui = SimpleNamespace(nodes={"computer_env": fake_combo})
    fake_size = MagicMock()
    fake_size.width.return_value = 1920
    fake_size.height.return_value = 1080
    fake_app = MagicMock()
    fake_app.primaryScreen.return_value = fake_size
    return SimpleNamespace(ui=fake_ui, app=fake_app)

def test_get_current_env(fake_window):
    comp = Computer(window=fake_window)
    env = comp.get_current_env()
    assert env == {"env": "test"}

def test_get_tool(fake_window):
    comp = Computer(window=fake_window)
    tool = comp.get_tool()
    assert tool["type"] == "computer_use_preview"
    assert tool["environment"] == {"env": "test"}

def test_handle_stream_chunk_no_computer_call():
    comp = Computer(window=None)
    ctx = SimpleNamespace(extra={})
    chunk = SimpleNamespace(item=SimpleNamespace(type="other"))
    tool_calls = []
    calls, has_calls = comp.handle_stream_chunk(ctx, chunk, tool_calls)
    assert calls == []
    assert has_calls is False

def test_handle_stream_chunk_with_computer_call(monkeypatch):
    comp = Computer(window=None)
    ctx = SimpleNamespace(extra={})
    action_dummy = SimpleNamespace()
    pending_item = SimpleNamespace(id="check1", code="code1", message="msg1")
    chunk = SimpleNamespace(item=SimpleNamespace(
        type="computer_call",
        id="id1",
        call_id="call1",
        action=action_dummy,
        pending_safety_checks=[pending_item]
    ))
    def fake_handle_action(id, call_id, action, tool_calls):
        tool_calls.append("processed")
        return tool_calls, True
    monkeypatch.setattr(comp, "handle_action", fake_handle_action)
    tool_calls = []
    calls, has_calls = comp.handle_stream_chunk(ctx, chunk, tool_calls)
    assert calls == ["processed"]
    assert has_calls is True
    assert ctx.extra.get("pending_safety_checks") == [{"id": "check1", "code": "code1", "message": "msg1"}]

def test_handle_action_click():
    comp = Computer(window=None)
    action = SimpleNamespace(type="click", button="left", x=10, y=20)
    tool_calls, has_calls = comp.handle_action("id", "call", action, [])
    assert has_calls is True
    assert len(tool_calls) == 1
    call = tool_calls[0]
    assert call["id"] == "id"
    assert call["call_id"] == "call"
    assert call["type"] == "computer_call"
    assert call["function"]["name"] == "mouse_move"
    args = json.loads(call["function"]["arguments"])
    assert args == {"x": 10, "y": 20, "click": "left", "num_clicks": 1}

@pytest.mark.parametrize("dbl_type", ["double_click", "dblclick", "dbl_click"])
def test_handle_action_double_click(dbl_type):
    comp = Computer(window=None)
    action = SimpleNamespace(type=dbl_type, x=15, y=25)
    tool_calls, has_calls = comp.handle_action("id2", "call2", action, [])
    assert has_calls is True
    assert len(tool_calls) == 1
    call = tool_calls[0]
    assert call["function"]["name"] == "mouse_move"
    args = json.loads(call["function"]["arguments"])
    assert args == {"x": 15, "y": 25, "click": "left", "num_clicks": 2}

def test_handle_action_move():
    comp = Computer(window=None)
    action = SimpleNamespace(type="move", x=30, y=40)
    tool_calls, has_calls = comp.handle_action("id3", "call3", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "mouse_move"
    args = json.loads(call["function"]["arguments"])
    assert args == {"x": 30, "y": 40}

def test_handle_action_screenshot():
    comp = Computer(window=None)
    action = SimpleNamespace(type="screenshot")
    tool_calls, has_calls = comp.handle_action("id4", "call4", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "get_screenshot"
    assert call["function"]["arguments"] == "{}"

def test_handle_action_type():
    comp = Computer(window=None)
    action = SimpleNamespace(type="type", text="hello")
    tool_calls, has_calls = comp.handle_action("id5", "call5", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "keyboard_type"
    args = json.loads(call["function"]["arguments"])
    assert args == {"text": "hello"}

def test_handle_action_keypress():
    comp = Computer(window=None)
    action = SimpleNamespace(type="keypress", keys=["a", "b", "c"])
    tool_calls, has_calls = comp.handle_action("id6", "call6", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "keyboard_keys"
    args = json.loads(call["function"]["arguments"])
    assert args == {"keys": ["a", "b", "c"]}

def test_handle_action_scroll():
    comp = Computer(window=None)
    action = SimpleNamespace(type="scroll", x=50, y=60, scroll_x=5, scroll_y=10)
    tool_calls, has_calls = comp.handle_action("id7", "call7", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "mouse_scroll"
    args = json.loads(call["function"]["arguments"])
    assert args == {"x": 50, "y": 60, "dx": 5, "dy": -10, "unit": "px"}

def test_handle_action_wait():
    comp = Computer(window=None)
    action = SimpleNamespace(type="wait")
    tool_calls, has_calls = comp.handle_action("id8", "call8", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "wait"
    assert call["function"]["arguments"] == "{}"

def test_handle_action_drag():
    comp = Computer(window=None)
    point1 = SimpleNamespace(x=100, y=200)
    point2 = SimpleNamespace(x=150, y=250)
    action = SimpleNamespace(type="drag", path=[point1, point2])
    tool_calls, has_calls = comp.handle_action("id9", "call9", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "mouse_drag"
    args = json.loads(call["function"]["arguments"])
    assert args == {"x": 100, "y": 200, "dx": 150, "dy": 250}

def test_handle_action_unknown():
    comp = Computer(window=None)
    action = SimpleNamespace(type="unknown")
    tool_calls, has_calls = comp.handle_action("id10", "call10", action, [])
    assert has_calls is True
    call = tool_calls[0]
    assert call["function"]["name"] == "wait"
    assert call["function"]["arguments"] == "{}"