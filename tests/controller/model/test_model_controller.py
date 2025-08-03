#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #
import pytest
from unittest.mock import MagicMock
from pygpt_net.controller.model import Model, Event, AppEvent

# Dummy model item used for init_list tests
class DummyModelItem:
    def __init__(self, name, provider):
        self.name = name
        self.provider = provider

# Dummy config that stores data in a dict
class DummyConfig:
    def __init__(self, mode="test_mode", model=None):
        self.data = {"current_model": {}}
        self.data["mode"] = mode
        self.data["model"] = model

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

@pytest.fixture
def dummy_window():
    window = MagicMock()
    # Setup core.config
    config = DummyConfig(model=None)
    window.core.config = config

    # Setup core.models with dummy return values
    models = MagicMock()
    models.get_next = MagicMock(return_value="next_model")
    models.get_prev = MagicMock(return_value="prev_model")
    models.get_by_idx = MagicMock(return_value="model_by_idx")
    models.get_by_mode = MagicMock(return_value={})
    models.get_default = MagicMock(return_value="default_model")
    window.core.models = models

    # Setup core.llm
    llm = MagicMock()
    llm.get_choices = MagicMock(return_value={})
    window.core.llm = llm

    # Setup dispatch and UI update
    window.dispatch = MagicMock()
    window.controller.ui.update = MagicMock()
    window.controller.chat.input.generating = False

    # Setup UI nodes
    node_model = MagicMock()
    window.ui.nodes = {"prompt.model": node_model}

    return window

def test_change_locked(dummy_window):
    model_inst = Model(dummy_window)
    dummy_window.controller.chat.input.generating = False
    assert not model_inst.change_locked()
    dummy_window.controller.chat.input.generating = True
    assert model_inst.change_locked()

def test_select_locked(dummy_window):
    dummy_window.controller.chat.input.generating = True
    dummy_window.core.config.set = MagicMock()
    model_inst = Model(dummy_window)
    model_inst.select("locked_model")
    dummy_window.core.config.set.assert_not_called()
    dummy_window.dispatch.assert_not_called()
    dummy_window.controller.ui.update.assert_not_called()

def test_select_unlocked(dummy_window):
    dummy_window.controller.chat.input.generating = False
    # Replace set with a MagicMock to track calls if needed
    dummy_window.core.config.set = MagicMock(side_effect=dummy_window.core.config.set)
    model_inst = Model(dummy_window)
    model_inst.select("test_model")
    # Check config updated
    assert dummy_window.core.config.data["model"] == "test_model"
    mode = dummy_window.core.config.data["mode"]
    assert dummy_window.core.config.data["current_model"][mode] == "test_model"
    # Two events dispatched
    assert dummy_window.dispatch.call_count == 2
    dummy_window.controller.ui.update.assert_called_once()

def test_next(dummy_window):
    dummy_window.controller.chat.input.generating = False
    model_inst = Model(dummy_window)
    model_inst.select = MagicMock()
    dummy_window.core.config.data["model"] = "current_model"
    model_inst.next()
    model_inst.select.assert_called_once_with("next_model")

def test_prev(dummy_window):
    dummy_window.controller.chat.input.generating = False
    model_inst = Model(dummy_window)
    model_inst.select = MagicMock()
    dummy_window.core.config.data["model"] = "current_model"
    model_inst.prev()
    model_inst.select.assert_called_once_with("prev_model")

def test_set(dummy_window):
    model_inst = Model(dummy_window)
    model_inst.set("modeA", "modelA")
    assert dummy_window.core.config.data["model"] == "modelA"
    assert dummy_window.core.config.data["current_model"]["modeA"] == "modelA"

def test_set_by_idx(dummy_window):
    model_inst = Model(dummy_window)
    model_inst.set_by_idx("modeA", 5)
    assert dummy_window.core.config.data["model"] == "model_by_idx"
    assert dummy_window.core.config.data["current_model"]["modeA"] == "model_by_idx"
    # Verify dispatch event data
    dummy_window.dispatch.assert_called_once()
    event_arg = dummy_window.dispatch.call_args[0][0]
    assert event_arg.data["value"] == "model_by_idx"

def test_select_on_list(dummy_window):
    model_inst = Model(dummy_window)
    model_inst.select_on_list("list_model")
    dummy_window.ui.nodes["prompt.model"].set_value.assert_called_once_with("list_model")

def test_select_current(dummy_window):
    model_inst = Model(dummy_window)
    # Setup current model and make it available in models list
    dummy_window.core.config.data["model"] = "current_model"
    dummy_window.core.models.get_by_mode = MagicMock(
        return_value={"current_model": DummyModelItem("Current", "prov")}
    )
    model_inst.select_current()
    dummy_window.ui.nodes["prompt.model"].set_value.assert_called_once_with("current_model")

def test_select_default_with_current(dummy_window):
    model_inst = Model(dummy_window)
    dummy_window.core.config.data["model"] = None
    dummy_window.core.config.data["current_model"] = {"test_mode": "valid_model"}
    dummy_window.core.models.get_by_mode = MagicMock(
        return_value={"valid_model": DummyModelItem("Valid", "prov")}
    )
    model_inst.select_default()
    assert dummy_window.core.config.data["model"] == "valid_model"

def test_select_default_default(dummy_window):
    model_inst = Model(dummy_window)
    dummy_window.core.config.data["model"] = ""
    dummy_window.core.config.data["current_model"] = {"test_mode": "invalid_model"}
    dummy_window.core.models.get_by_mode = MagicMock(return_value={})
    dummy_window.core.models.get_default = MagicMock(return_value="default_model")
    model_inst.select_default()
    assert dummy_window.core.config.data["model"] == "default_model"

def test_switch_inline_no_change(dummy_window):
    model_inst = Model(dummy_window)
    dummy_model = MagicMock()
    result = model_inst.switch_inline("test_mode", dummy_model)
    assert result == dummy_model

def dispatch_side_effect(event):
    event.data["model"] = "changed_model"

def test_switch_inline_with_change(dummy_window):
    model_inst = Model(dummy_window)
    dummy_model = MagicMock()
    dummy_window.dispatch.side_effect = dispatch_side_effect
    result = model_inst.switch_inline("test_mode", dummy_model)
    assert result == "changed_model"

def test_init_list(dummy_window):
    model_inst = Model(dummy_window)
    # Setup two dummy model items with different providers
    m1 = DummyModelItem("Model 1", "prov1")
    m2 = DummyModelItem("Model 2", "prov2")
    data = {"m1": m1, "m2": m2}
    dummy_window.core.models.get_by_mode = MagicMock(return_value=data)
    dummy_window.core.llm.get_choices = MagicMock(return_value={"prov1": "Provider 1", "prov2": "Provider 2"})
    model_inst.init_list()
    expected = {
        "separator::prov1": "Provider 1",
        "m1": "Model 1",
        "separator::prov2": "Provider 2",
        "m2": "Model 2",
    }
    dummy_window.ui.nodes["prompt.model"].set_keys.assert_called_once_with(expected)

def test_reload(dummy_window):
    model_inst = Model(dummy_window)
    model_inst.init_list = MagicMock()
    model_inst.update = MagicMock()
    model_inst.reload()
    model_inst.init_list.assert_called_once()
    model_inst.update.assert_called_once()

def test_update(dummy_window):
    model_inst = Model(dummy_window)
    model_inst.select_default = MagicMock()
    model_inst.select_current = MagicMock()
    model_inst.update()
    model_inst.select_default.assert_called_once()
    model_inst.select_current.assert_called_once()