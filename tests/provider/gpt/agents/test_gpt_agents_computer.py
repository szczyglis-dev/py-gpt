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

import base64
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from pygpt_net.provider.api.openai.agents.computer import LocalComputer, Agent

@pytest.fixture
def dummy_window():
    win = MagicMock()
    win.core.gpt.computer.get_current_env.return_value = "windows"
    win.core.plugins.get.return_value.handle_call = MagicMock()
    scr = MagicMock()
    size = MagicMock()
    size.width.return_value = 1920
    size.height.return_value = 1080
    scr.size.return_value = size
    win.app.primaryScreen.return_value = scr
    win.controller.attachment.clear_silent = MagicMock()
    win.controller.painter.capture.screenshot = MagicMock(return_value="dummy_path")
    return win

@pytest.fixture
def dummy_bridge():
    b = MagicMock()
    b.stopped.return_value = False
    b.on_stop = MagicMock()
    b.on_step = MagicMock()
    b.on_error = MagicMock()
    return b

@pytest.fixture
def dummy_ctx():
    c = MagicMock()
    c.stream = ""
    return c

def test_environment(dummy_window):
    comp = LocalComputer(dummy_window)
    assert comp.environment == "windows"

def test_dimensions(dummy_window):
    comp = LocalComputer(dummy_window)
    assert comp.dimensions == (1920, 1080)

def test_call_cmd(dummy_window):
    comp = LocalComputer(dummy_window)
    item = {"key": "value"}
    comp.call_cmd(item)
    dummy_window.core.plugins.get.return_value.handle_call.assert_called_once_with(item)

def test_screenshot(tmp_path, dummy_window):
    comp = LocalComputer(dummy_window)
    dummy_data = b"test_image"
    screenshot_file = tmp_path / "screenshot.png"
    screenshot_file.write_bytes(dummy_data)
    dummy_window.controller.painter.capture.screenshot.return_value = str(screenshot_file)
    result = comp.screenshot()
    expected = base64.b64encode(dummy_data).decode("utf-8")
    assert result == expected
    assert dummy_window.controller.attachment.clear_silent.call_count == 2

def test_click(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.click(100, 200, "left")
    comp.call_cmd.assert_called_once_with({
        "cmd": "mouse_move",
        "params": {"x": 100, "y": 200, "click": "left", "num_clicks": 1},
    })

def test_double_click(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.double_click(150, 250)
    comp.call_cmd.assert_called_once_with({
        "cmd": "mouse_move",
        "params": {"x": 150, "y": 250, "click": "left", "num_clicks": 2},
    })

def test_scroll(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.scroll(10, 20, 5, 15)
    comp.call_cmd.assert_called_once_with({
        "cmd": "mouse_scroll",
        "params": {"x": 10, "y": 20, "dx": 5, "dy": -15, "unit": "px"},
    })

def test_type(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.type("hello")
    comp.call_cmd.assert_called_once_with({
        "cmd": "keyboard_type",
        "params": {"text": "hello"},
    })

def test_wait(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.wait()
    comp.call_cmd.assert_called_once_with({
        "cmd": "wait",
        "params": {},
    })

def test_move(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.move(300, 400)
    comp.call_cmd.assert_called_once_with({
        "cmd": "mouse_move",
        "params": {"x": 300, "y": 400},
    })

def test_keypress(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.keypress(["Shift", "A", "B"])
    comp.call_cmd.assert_called_once_with({
        "cmd": "keyboard_keys",
        "params": {"keys": ["Shift", "A", "B"]},
    })

def test_drag_with_path(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.drag([(10, 20), (5, 5)])
    comp.call_cmd.assert_called_once_with({
        "cmd": "mouse_drag",
        "params": {"x": 10, "y": 20, "dx": 5, "dy": 5},
    })

def test_drag_empty(dummy_window):
    comp = LocalComputer(dummy_window)
    comp.call_cmd = MagicMock()
    comp.drag([])
    comp.call_cmd.assert_not_called()

def test_debug_print(monkeypatch, dummy_window, dummy_bridge, dummy_ctx):
    agent = Agent(computer=LocalComputer(dummy_window), bridge=dummy_bridge, ctx=dummy_ctx)
    fake_pp = MagicMock()
    mod = sys.modules[Agent.__module__]
    monkeypatch.setattr(mod, "pp", fake_pp)
    agent.debug = True
    agent.debug_print("test")
    fake_pp.assert_called_once_with("test")

def test_handle_item_stopped(dummy_window, dummy_bridge, dummy_ctx):
    agent = Agent(computer=LocalComputer(dummy_window), bridge=dummy_bridge, ctx=dummy_ctx)
    dummy_bridge.stopped.return_value = True
    item = {"type": "message", "content": [{"text": "stop"}]}
    result = agent.handle_item(item)
    dummy_bridge.on_stop.assert_called_once_with(dummy_ctx)
    assert result == []

def test_handle_item_message(dummy_window, dummy_bridge, dummy_ctx):
    agent = Agent(computer=LocalComputer(dummy_window), bridge=dummy_bridge, ctx=dummy_ctx, stream=True)
    agent.debug = False
    item = {"type": "message", "content": [{"text": "hello"}]}
    result = agent.handle_item(item)
    assert dummy_ctx.stream == "hello"
    dummy_bridge.on_step.assert_called_once_with(dummy_ctx, agent.begin)
    assert result == []

def test_handle_item_function_call(dummy_window, dummy_bridge, dummy_ctx):
    comp = LocalComputer(dummy_window)
    comp.click = MagicMock()
    agent = Agent(computer=comp, bridge=dummy_bridge, ctx=dummy_ctx)
    agent.debug = False
    args = {"x": 10, "y": 20}
    item = {"type": "function_call", "name": "click", "arguments": json.dumps(args), "call_id": "fid"}
    result = agent.handle_item(item)
    comp.click.assert_called_once_with(**args)
    assert result == [{"type": "function_call_output", "call_id": "fid", "output": "success"}]

def test_handle_item_computer_call(dummy_window, dummy_bridge, dummy_ctx):
    comp = LocalComputer(dummy_window)
    comp.click = MagicMock()
    comp.screenshot = MagicMock(return_value="base64img")
    agent = Agent(computer=comp, bridge=dummy_bridge, ctx=dummy_ctx)
    agent.debug = False
    item = {
        "type": "computer_call",
        "call_id": "cid",
        "action": {"type": "click", "x": 50, "y": 60},
        "pending_safety_checks": ["check1"],
    }
    result = agent.handle_item(item)
    comp.click.assert_called_once_with(x=50, y=60)
    comp.screenshot.assert_called_once()
    expected = [{
        "type": "computer_call_output",
        "call_id": "cid",
        "acknowledged_safety_checks": ["check1"],
        "output": {"type": "input_image", "image_url": "data:image/png;base64,base64img"},
    }]
    assert result == expected

def fake_create_response(model, input, tools, truncation):
    return {"id": "rid", "output": [{"role": "assistant", "content": "done", "type": "text"}]}

def test_run(monkeypatch, dummy_window, dummy_bridge, dummy_ctx):
    mod = sys.modules[Agent.__module__]
    monkeypatch.setattr(mod, "create_response", fake_create_response)
    comp = LocalComputer(dummy_window)
    agent = Agent(model="test-model", computer=comp, bridge=dummy_bridge, ctx=dummy_ctx)
    new_items, response_id = agent.run([{"role": "user", "content": "hi", "type": "text"}], debug=True)
    assert response_id == "rid"
    assert any(item.get("role") == "assistant" for item in new_items)

def test_run_stopped(dummy_window, dummy_bridge, dummy_ctx):
    dummy_bridge.stopped.return_value = True
    comp = LocalComputer(dummy_window)
    agent = Agent(model="test-model", computer=comp, bridge=dummy_bridge, ctx=dummy_ctx)
    new_items, response_id = agent.run([{"role": "user", "content": "hi"}])
    dummy_bridge.on_stop.assert_called_once_with(dummy_ctx)
    assert new_items == []
    assert response_id is None