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
from unittest.mock import MagicMock, patch
import copy

# Dummy model
class DummyModel:
    def __init__(self, id):
        self.id = id
        self.data = {
            "id": id,
            "name": f"Model {id}",
            "provider": "prov",
            "ctx": 10,
            "tokens": 100,
            "mode": True,
            "tool_calls": False,
            "input": [],
            "output": [],
            "default": False,
            "llama_index.args": {},
            "llama_index.env": {}
        }
    def to_dict(self):
        return self.data.copy()
    def from_dict(self, data):
        self.data.update(data)
        self.id = data.get("id", self.id)

@pytest.fixture(autouse=True)
def patch_trans():
    with patch("pygpt_net.utils.trans", lambda s: s):
        yield

@pytest.fixture
def dummy_window():
    window = MagicMock()
    window.model_settings = MagicMock()
    window.model_settings.setup = MagicMock()
    window.model_settings.update_list = MagicMock()

    dialogs = MagicMock()
    window.ui = MagicMock()
    window.ui.dialogs = dialogs
    list_widget = MagicMock()
    list_widget.index.side_effect = lambda idx, col: idx
    window.ui.models = {"models.list": list_widget}
    node_widget = MagicMock()
    window.ui.nodes = {"models.list": node_widget}
    window.ui.add_hook = MagicMock()

    core_models = MagicMock()
    core_models.items = {}
    core_models.get_ids.side_effect = lambda: list(core_models.items.keys())
    core_models.sort_items = MagicMock()
    core_models.save = MagicMock()
    core_models.create_empty = MagicMock()
    core_models.delete = MagicMock()
    core_models.restore_default = MagicMock()
    core = MagicMock()
    core.models = core_models
    core.config.get = MagicMock(return_value="test_mode")
    window.core = core

    # Controller
    controller_config = MagicMock()
    controller_config.get_value.side_effect = lambda parent_id, key, option: f"value_{key}"
    controller = MagicMock()
    controller.config = controller_config
    controller.model = MagicMock()
    window.controller = controller

    window.update_status = MagicMock()
    window.dispatch = MagicMock()
    return window

@pytest.fixture
def editor(dummy_window):
    from pygpt_net.controller.model.editor import Editor
    return Editor(window=dummy_window)

def test_get_options(editor):
    opts = editor.get_options()
    assert isinstance(opts, dict)
    assert "id" in opts

def test_get_option_existing(editor):
    opt = editor.get_option("id")
    assert opt is not None

def test_get_option_non_existing(editor):
    opt = editor.get_option("nonexistent")
    assert opt is None

def test_setup(editor, dummy_window):
    editor.setup()
    dummy_window.model_settings.setup.assert_called_with(None)
    hooks = [call.args[0] for call in dummy_window.ui.add_hook.call_args_list]
    assert "update.model.name" in hooks
    assert "update.model.mode" in hooks

def test_hook_update(editor, dummy_window):
    dummy_model = MagicMock()
    dummy_model.id = "test_model"
    dummy_window.core.models.items = {"test_model": dummy_model}
    editor.current = "test_model"
    editor.locked = False
    editor.window.controller.reloading = False
    editor.save = MagicMock()
    editor.reload_items = MagicMock()
    editor.set_by_tab = MagicMock()
    editor.hook_update("name", "new_value", caller="caller")
    editor.save.assert_called_with(persist=False)
    editor.reload_items.assert_called_once()
    editor.set_by_tab.assert_called_with(0)

def test_toggle_editor_open(editor):
    editor.dialog = False
    editor.open = MagicMock()
    editor.close = MagicMock()
    editor.toggle_editor()
    editor.open.assert_called_once()
    editor.close.assert_not_called()

def test_toggle_editor_close(editor):
    editor.dialog = True
    editor.open = MagicMock()
    editor.close = MagicMock()
    editor.toggle_editor()
    editor.close.assert_called_once()
    editor.open.assert_not_called()

def test_open(editor, dummy_window):
    editor.config_initialized = False
    editor.init = MagicMock()
    dummy_window.core.models.items = {"model1": MagicMock()}
    editor.open(force=False)
    assert editor.config_initialized is True
    assert editor.dialog is True
    assert editor.previous == dummy_window.core.models.items
    dummy_window.ui.dialogs.open.assert_called_with("models.editor", width=800, height=500)

def test_close(editor, dummy_window):
    editor.dialog = True
    editor.close()
    dummy_window.ui.dialogs.close.assert_called_with("models.editor")
    assert editor.dialog is False

def test_init(editor, dummy_window):
    dummy_model = DummyModel("test_id")
    dummy_window.core.models.items = {"test_id": dummy_model}
    editor.current = "test_id"
    editor.set_tab_by_id = MagicMock()
    editor.reload_items = MagicMock()
    editor.window.controller.config.load_options = MagicMock()
    editor.init()
    dummy_window.core.models.sort_items.assert_called_once()
    editor.reload_items.assert_called_once()
    editor.set_tab_by_id.assert_called_with("test_id")
    editor.window.controller.config.load_options.assert_called()
    args, _ = editor.window.controller.config.load_options.call_args
    assert args[0] == "model"
    options_arg = args[1]
    assert options_arg["id"]["value"] == "test_id"

def test_save_persist_true(editor, dummy_window):
    dummy_model = DummyModel("model1")
    dummy_window.core.models.items = {"model1": dummy_model}
    editor.current = "model1"
    editor.close = MagicMock()
    editor.save(persist=True)
    assert dummy_model.id == "value_id"
    assert "value_id" in dummy_window.core.models.items
    assert editor.current == "value_id"
    dummy_window.core.models.save.assert_called_once()
    editor.close.assert_called_once()
    dummy_window.update_status.assert_called_once_with("Settings saved")
    dummy_window.core.models.sort_items.assert_called_once()
    editor.window.controller.model.reload.assert_called_once()
    dummy_window.dispatch.assert_called_once()

def test_save_persist_false(editor, dummy_window):
    dummy_model = DummyModel("model1")
    dummy_window.core.models.items = {"model1": dummy_model}
    editor.current = "model1"
    editor.close = MagicMock()
    editor.save(persist=False)
    dummy_window.core.models.save.assert_not_called()
    editor.close.assert_not_called()
    dummy_window.update_status.assert_not_called()
    dummy_window.core.models.sort_items.assert_called_once()
    editor.window.controller.model.reload.assert_called_once()
    dummy_window.dispatch.assert_called_once()

def test_reload_items(editor, dummy_window):
    dummy_window.core.models.items = {"model1": MagicMock()}
    editor.reload_items()
    dummy_window.model_settings.update_list.assert_called_with("models.list", dummy_window.core.models.items)

def test_select(editor, dummy_window):
    dummy_window.core.models.items = {"model1": MagicMock()}
    editor.get_model_by_tab_idx = MagicMock(return_value="model1")
    editor.save = MagicMock()
    editor.init = MagicMock()
    editor.locked = False
    editor.select(0)
    editor.save.assert_called_with(persist=False)
    assert editor.current == "model1"
    editor.init.assert_called_once()

def test_new(editor, dummy_window):
    editor.save = MagicMock()
    editor.reload_items = MagicMock()
    editor.init = MagicMock()
    dummy_new_model = DummyModel("new_model")
    dummy_window.core.models.create_empty = MagicMock(return_value=dummy_new_model)
    editor.get_tab_by_id = MagicMock(return_value=0)
    editor.set_by_tab = MagicMock()
    editor.locked = False
    editor.new()
    editor.save.assert_called_with(persist=False)
    dummy_window.core.models.create_empty.assert_called_once()
    dummy_window.core.models.save.assert_called_once()
    editor.reload_items.assert_called_once()
    assert editor.current == "new_model"
    editor.set_by_tab.assert_called_with(0)
    editor.init.assert_called_once()

def test_delete_by_idx_without_force(editor, dummy_window):
    dummy_model = DummyModel("model1")
    dummy_window.core.models.items = {"model1": dummy_model}
    editor.get_model_by_tab_idx = MagicMock(return_value="model1")
    editor.delete_by_idx(0, force=False)
    dummy_window.ui.dialogs.confirm.assert_called_with(
        type="models.editor.delete",
        id=0,
        msg='Are you sure you want to delete the model?'
    )

def test_delete_by_idx_with_force(editor, dummy_window):
    dummy_model = DummyModel("model1")
    dummy_window.core.models.items = {"model1": dummy_model}
    editor.get_model_by_tab_idx = MagicMock(return_value="model1")
    editor.init = MagicMock()
    editor.reload_items = MagicMock()
    editor.current = "model1"
    editor.delete_by_idx(0, force=True)
    dummy_window.core.models.delete.assert_called_with("model1")
    dummy_window.core.models.save.assert_called_once()
    editor.reload_items.assert_called_once()
    editor.init.assert_called_once()
    assert editor.current is None

def test_load_defaults_user_without_force(editor, dummy_window):
    editor.load_defaults_user(force=False)
    dummy_window.ui.dialogs.confirm.assert_called_with(
        type="models.editor.defaults.user",
        id=-1,
        msg='Undo current changes?'
    )

def test_load_defaults_user_with_force(editor):
    editor.undo = MagicMock()
    editor.load_defaults_user(force=True)
    editor.undo.assert_called_once()

def test_load_defaults_app_without_force(editor, dummy_window):
    editor.load_defaults_app(force=False)
    dummy_window.ui.dialogs.confirm.assert_called_with(
        type="models.editor.defaults.app",
        id=-1,
        msg='Load models factory settings?'
    )

def test_load_defaults_app_with_force(editor, dummy_window):
    from pygpt_net.utils import trans
    editor.init = MagicMock()
    editor.reload_items = MagicMock()
    dummy_window.ui.dialogs.alert = MagicMock()
    editor.load_defaults_app(force=True)
    dummy_window.core.models.restore_default.assert_called_once()
    dummy_window.core.models.save.assert_called_once()
    assert editor.current is None
    dummy_window.core.models.sort_items.assert_called_once()
    editor.reload_items.assert_called_once()
    editor.init.assert_called_once()
    dummy_window.ui.dialogs.alert.assert_called_with(trans('Restored to models factory settings.'))

def test_set_by_tab(editor, dummy_window):
    dummy_window.core.models.items = {"a": MagicMock(), "b": MagicMock()}
    dummy_window.core.models.get_ids = lambda: list(dummy_window.core.models.items.keys())
    editor.set_by_tab(1)
    assert editor.current == "b"
    dummy_window.ui.models["models.list"].index.assert_called_with(1, 0)
    dummy_window.ui.nodes["models.list"].setCurrentIndex.assert_called_with(1)

def test_set_tab_by_id(editor, dummy_window):
    dummy_window.core.models.items = {"a": MagicMock(), "b": MagicMock()}
    dummy_window.core.models.get_ids = lambda: list(dummy_window.core.models.items.keys())
    editor.set_tab_by_id("a")
    dummy_window.ui.models["models.list"].index.assert_called_with(0, 0)
    dummy_window.ui.nodes["models.list"].setCurrentIndex.assert_called_with(0)

def test_get_tab_idx(editor, dummy_window):
    dummy_window.core.models.items = {"a": MagicMock(), "b": MagicMock()}
    dummy_window.core.models.get_ids = lambda: list(dummy_window.core.models.items.keys())
    idx = editor.get_tab_idx("b")
    assert idx == 1
    idx_none = editor.get_tab_idx("c")
    assert idx_none is None

def test_get_tab_by_id(editor, dummy_window):
    dummy_window.core.models.items = {"a": MagicMock(), "b": MagicMock()}
    dummy_window.core.models.get_ids = lambda: list(dummy_window.core.models.items.keys())
    idx = editor.get_tab_by_id("b")
    assert idx == 1
    idx_none = editor.get_tab_by_id("c")
    assert idx_none is None

def test_get_model_by_tab_idx(editor, dummy_window):
    dummy_window.core.models.items = {"a": MagicMock(), "b": MagicMock()}
    dummy_window.core.models.get_ids = lambda: list(dummy_window.core.models.items.keys())
    model_id = editor.get_model_by_tab_idx(0)
    assert model_id == "a"
    model_id_none = editor.get_model_by_tab_idx(5)
    assert model_id_none is None

def test_open_by_idx(editor, dummy_window):
    dummy_window.core.models.get_by_idx = MagicMock(return_value="model1")
    editor.open = MagicMock()
    editor.open_by_idx(0)
    assert editor.current == "model1"
    editor.open.assert_called_with(force=True)

def test_selected_methods(editor):
    editor.selected = []
    editor.add_selected(1)
    assert 1 in editor.selected
    editor.add_selected(1)
    assert editor.selected.count(1) == 1
    editor.remove_selected(1)
    assert 1 not in editor.selected
    editor.set_selected(2)
    assert editor.selected == [2]
    editor.clear_selected()
    assert editor.selected == []