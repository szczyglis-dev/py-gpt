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
import os
import pytest
from unittest.mock import MagicMock
from pygpt_net.controller.model.importer import Importer

# A fake index used to simulate selection indexes
class FakeIndex:
    def __init__(self, row_value):
        self._row = row_value

    def row(self):
        return self._row

@pytest.fixture
def mock_window():
    window = MagicMock()

    # Set up UI nodes
    available = MagicMock()
    current = MagicMock()
    add_button = MagicMock()
    remove_button = MagicMock()
    status_label = MagicMock()
    url_label = MagicMock()
    editor = MagicMock()
    avail_all = MagicMock()

    editor.update_available = MagicMock()
    editor.update_current = MagicMock()
    avail_all.isChecked = MagicMock(return_value=False)

    window.ui.nodes = {
        "models.importer.available": available,
        "models.importer.add": add_button,
        "models.importer.current": current,
        "models.importer.remove": remove_button,
        "models.importer.status": status_label,
        "models.importer.url": url_label,
        "models.importer.editor": editor,
        "models.importer.available.all": avail_all,
    }
    available.selectionModel = MagicMock()
    current.selectionModel = MagicMock()

    # Config and dialogs setup
    provider_config = MagicMock()
    window.ui.config = {"models.importer": {"provider": provider_config}}
    window.ui.dialogs = MagicMock()
    window.ui.add_hook = MagicMock()

    # model_importer and core setup
    window.model_importer = MagicMock()
    window.model_importer.setup = MagicMock()
    llm = MagicMock()
    llm.get_provider_name = MagicMock(return_value="Test Provider")
    llm.get_choices = MagicMock(return_value={
        "openai": "OpenAI", 
        "azure_openai": "Azure OpenAI", 
        "perplexity": "Perplexity"
    })
    window.core.llm = llm
    models = MagicMock()
    models.items = {}
    models.create_empty = MagicMock()
    models.sort_items = MagicMock()
    models.save = MagicMock()
    # ollama in models
    ollama = MagicMock()
    ollama.get_status = MagicMock(return_value={"status": False})
    models.ollama = ollama
    window.core.models = models

    # Controller setup
    model_controller = MagicMock()
    model_controller.init_list = MagicMock()
    model_controller.update = MagicMock()
    window.controller = MagicMock()
    window.controller.model = model_controller
    window.controller.config = MagicMock()
    window.controller.config.apply_value = MagicMock()

    window.dispatch = MagicMock()
    return window

@pytest.fixture
def importer(mock_window):
    return Importer(window=mock_window)

def test_in_current(importer):
    model_id = "model1"
    assert importer.in_current(model_id) is False
    fake_model = type("FakeModel", (), {})()
    fake_model.id = model_id
    importer.items_current[importer.provider] = {"model1": fake_model}
    assert importer.in_current("model1") is True
    assert importer.in_current(fake_model.id) is True

def test_change_available_no_selection(importer, mock_window):
    avail = mock_window.ui.nodes["models.importer.available"]
    fake_index = MagicMock()
    fake_index.row.return_value = -1
    avail.selectionModel.return_value.currentIndex.return_value = fake_index
    importer.items_available = {"model1": MagicMock()}
    importer.change_available()
    assert importer.selected_available is None
    mock_window.ui.nodes["models.importer.add"].setEnabled.assert_called_with(False)

def test_change_available_valid_not_in_current(importer, mock_window):
    avail = mock_window.ui.nodes["models.importer.available"]
    fake_index = MagicMock()
    fake_index.row.return_value = 0
    avail.selectionModel.return_value.currentIndex.return_value = fake_index
    importer.items_available = {"model1": MagicMock()}
    importer.items_current = {}
    importer.change_available()
    assert importer.selected_available == "model1"
    mock_window.ui.nodes["models.importer.add"].setEnabled.assert_called_with(True)

def test_change_available_valid_in_current(importer, mock_window):
    avail = mock_window.ui.nodes["models.importer.available"]
    fake_index = MagicMock()
    fake_index.row.return_value = 0
    avail.selectionModel.return_value.currentIndex.return_value = fake_index
    fake_model = type("FakeModel", (), {})()
    fake_model.id = "model1"
    importer.items_available = {"model1": MagicMock()}
    importer.items_current = {importer.provider: {"model1": fake_model}}
    importer.change_available()
    assert importer.selected_available == "model1"
    mock_window.ui.nodes["models.importer.add"].setEnabled.assert_called_with(False)

def test_change_current_no_selection(importer, mock_window):
    curr = mock_window.ui.nodes["models.importer.current"]
    fake_index = MagicMock()
    fake_index.row.return_value = -1
    curr.selectionModel.return_value.currentIndex.return_value = fake_index
    importer.items_current = {importer.provider: {"model1": MagicMock()}}
    importer.change_current()
    assert importer.selected_current is None
    mock_window.ui.nodes["models.importer.remove"].setEnabled.assert_called_with(False)

def test_change_current_valid_in_available(importer, mock_window):
    curr = mock_window.ui.nodes["models.importer.current"]
    fake_index = MagicMock()
    fake_index.row.return_value = 0
    curr.selectionModel.return_value.currentIndex.return_value = fake_index
    importer.items_current = {importer.provider: {"model1": MagicMock()}}
    importer.items_available_all = {"model1": MagicMock()}
    importer.change_current()
    assert importer.selected_current == "model1"
    mock_window.ui.nodes["models.importer.remove"].setEnabled.assert_called_with(True)

def test_change_current_valid_not_in_available(importer, mock_window):
    curr = mock_window.ui.nodes["models.importer.current"]
    fake_index = MagicMock()
    fake_index.row.return_value = 0
    curr.selectionModel.return_value.currentIndex.return_value = fake_index
    importer.items_current = {importer.provider: {"model1": MagicMock()}}
    importer.items_available_all = {}
    importer.change_current()
    assert importer.selected_current == "model1"
    mock_window.ui.nodes["models.importer.remove"].setEnabled.assert_called_with(False)

def test_add_no_selected(importer, mock_window):
    importer.selected_available = None
    importer.items_available = {"model1": MagicMock()}
    importer.add()
    assert "model1" not in importer.items_current[importer.provider]
    assert "model1" not in importer.pending
    assert "model1" in importer.items_available

def test_add_already_in_current(importer, mock_window):
    importer.selected_available = "model1"
    fake_model = MagicMock()
    importer.items_available = {"model1": fake_model}
    importer.items_current = {importer.provider: {"model1": fake_model}}
    importer.add()
    assert "model1" in importer.items_current[importer.provider]
    assert "model1" not in importer.pending
    assert "model1" in importer.items_available

def test_add_success(importer, mock_window):
    importer.selected_available = "model1"
    fake_model = MagicMock()
    importer.items_available = {"model1": fake_model}
    importer.items_current = {importer.provider: {}}
    importer.all = False
    importer.add()
    assert "model1" in importer.items_current[importer.provider]
    assert "model1" in importer.pending
    assert "model1" not in importer.items_available

def test_remove_no_selected(importer, mock_window):
    importer.selected_current = None
    importer.items_current = {importer.provider: {"model1": MagicMock()}}
    importer.remove()
    assert "model1" not in importer.items_available
    assert "model1" in importer.items_current[importer.provider]
    assert "model1" not in importer.removed

def test_remove_not_in_current(importer, mock_window):
    importer.selected_current = "model1"
    importer.items_current = {importer.provider: {}}
    importer.remove()
    assert "model1" not in importer.items_available
    assert "model1" not in importer.items_current[importer.provider]
    assert "model1" not in importer.removed

def test_remove_success(importer, mock_window):
    fake_model = MagicMock()
    importer.selected_current = "model1"
    importer.items_current = {importer.provider: {"model1": fake_model}}
    importer.pending = {"model1": fake_model}
    importer.remove()
    assert "model1" in importer.items_available
    assert "model1" not in importer.items_current[importer.provider]
    assert "model1" in importer.removed

def test_setup(importer, mock_window):
    importer.get_providers_option = lambda: {"keys": ["test_key"]}
    importer.setup()
    mock_window.model_importer.setup.assert_called_with(None)
    mock_window.ui.config["models.importer"]["provider"].set_keys.assert_called_with(["test_key"])
    mock_window.ui.add_hook.assert_called_with("update.models.importer.provider", importer.hook_update)

def test_toggle_editor(importer):
    importer.dialog = False
    importer.open = MagicMock()
    importer.close = MagicMock()
    importer.toggle_editor()
    importer.open.assert_called_once()
    importer.dialog = True
    importer.toggle_editor()
    importer.close.assert_called_once()

def test_open(importer, mock_window):
    importer.initialized = False
    importer.setup = MagicMock()
    importer.init = MagicMock()
    importer.dialog = False
    importer.open()
    importer.setup.assert_called_once()
    assert importer.dialog is True
    mock_window.ui.dialogs.open.assert_called_with("models.importer", width=importer.width, height=importer.height)

def test_close(importer, mock_window):
    importer.dialog = True
    importer.close()
    mock_window.ui.dialogs.close.assert_called_with('models.importer')
    assert importer.dialog is False

def test_cancel(importer):
    importer.close = MagicMock()
    importer.cancel()
    importer.close.assert_called_once()

def test_init(importer, mock_window):
    mock_window.ui.nodes["models.importer.available.all"].isChecked.return_value = True
    importer.get_available = lambda: {"a": "model_a"}
    importer.get_current = lambda: {"current_model": "model_current"}
    importer.refresh = MagicMock()
    importer.init(reload=False, on_change=False)
    assert importer.all is False
    assert importer.items_available == {"a": "model_a"}
    assert importer.items_current[importer.provider] == {"current_model": "model_current"}
    importer.refresh.assert_called()

def test_update_title_default(importer, mock_window, monkeypatch):
    monkeypatch.setattr("pygpt_net.utils.trans", lambda s: s)
    importer.provider = "_"
    importer.update_title()
    mock_window.ui.nodes["models.importer.url"].setText.assert_called_with("Please select a provider from the list.")

def test_update_title_other(importer, mock_window):
    importer.provider = "test_provider"
    importer.window.core.llm.get_provider_name.return_value = "Test Provider Name"
    importer.update_title()
    mock_window.ui.nodes["models.importer.url"].setText.assert_called_with("Test Provider Name")

def test_update_title_ollama(importer, mock_window):
    importer.provider = "ollama"
    if "OLLAMA_API_BASE" in os.environ:
        del os.environ["OLLAMA_API_BASE"]
    importer.update_title()
    mock_window.ui.nodes["models.importer.url"].setText.assert_called_with("http://localhost:11434")

def test_update_title_ollama_env(importer, mock_window, monkeypatch):
    importer.provider = "ollama"
    monkeypatch.setenv("OLLAMA_API_BASE", "http://testenv")
    importer.update_title()
    mock_window.ui.nodes["models.importer.url"].setText.assert_called_with("http://testenv")

def test_toggle_all(importer):
    importer.refresh = MagicMock()
    importer.toggle_all(True)
    assert importer.all is True
    importer.refresh.assert_called_with(reload=True)

def test_set_status(importer, mock_window):
    importer.initialized = True
    importer.set_status("Test")
    mock_window.ui.nodes["models.importer.status"].setText.assert_called_with("Test")

def test_get_by_idx_get_ids(importer):
    items = {"a": 1, "b": 2}
    ids = importer.get_ids(items)
    assert set(ids) == {"a", "b"}
    assert importer.get_by_idx(0, items) in ids
    assert importer.get_by_idx(5, items) is None

def test_get_providers_option(importer, mock_window, monkeypatch):
    mock_window.core.llm.get_choices.return_value = {
        "openai": "OpenAI",
        "azure_openai": "Azure OpenAI",
        "perplexity": "Perplexity"
    }
    monkeypatch.setattr("pygpt_net.utils.trans", lambda s: s)
    option = importer.get_providers_option()
    keys = option["keys"]
    assert any("_" in list(d.keys())[0] for d in keys)
    for d in keys:
        key = list(d.keys())[0]
        assert key not in ["azure_openai", "perplexity"]

def test_hook_update(importer):
    importer.init = MagicMock()
    importer.set_status = MagicMock()
    importer.hook_update("provider", "new_provider", None)
    assert importer.provider == "new_provider"
    importer.init.assert_called_with(reload=True, on_change=True)

def test_hook_update_default(importer):
    importer.init = MagicMock()
    importer.set_status = MagicMock()
    importer.hook_update("provider", "_", None)
    importer.set_status.assert_called_with("")

def test_from_pending(importer, mock_window):
    fake_model = MagicMock()
    importer.pending = {"model1": fake_model}
    importer.removed = {"model2": fake_model}
    mock_window.core.models.items = {}
    mock_window.core.models.sort_items = MagicMock()
    mock_window.core.models.save = MagicMock()
    importer.from_pending()
    assert "model1" in mock_window.core.models.items
    assert "model2" not in mock_window.core.models.items
    assert importer.pending == {}
    assert importer.removed == {}
    mock_window.core.models.sort_items.assert_called_once()
    mock_window.core.models.save.assert_called_once()

def test_save(importer, mock_window):
    importer.from_pending = MagicMock()
    importer.close = MagicMock()
    importer.window.controller.model.init_list = MagicMock()
    importer.window.controller.model.update = MagicMock()
    importer.save()
    importer.from_pending.assert_called_once()
    importer.window.controller.model.init_list.assert_called_once()
    importer.window.controller.model.update.assert_called_once()
    importer.close.assert_called_once()
    mock_window.dispatch.assert_called()

def test_refresh(importer, mock_window):
    importer.provider = "test"
    fake_model1 = MagicMock()
    fake_model2 = MagicMock()
    importer.items_available = {"model1": fake_model1, "model2": fake_model2}
    importer.items_current = {importer.provider: {"model1": fake_model1}}
    importer.get_available = lambda: {"model1": fake_model1, "model2": fake_model2}
    importer.all = False
    importer.refresh(reload=True)
    assert "model1" not in importer.items_available
    mock_window.ui.nodes["models.importer.editor"].update_available.assert_called_with(importer.items_available)
    mock_window.ui.nodes["models.importer.editor"].update_current.assert_called_with(importer.items_current[importer.provider])

def test_get_provider_available(importer, mock_window):
    importer.provider = "openai"
    fake_llm = MagicMock()
    fake_llm.get_models.return_value = [{"id": "modelX", "name": "Model X"}]
    mock_window.core.llm.get.return_value = fake_llm

    def fake_create_empty(append=False):
        fake = type("FakeModel", (), {})()
        fake.llama_index = {}
        return fake

    mock_window.core.models.create_empty.side_effect = fake_create_empty
    result = importer.get_provider_available()
    assert "modelX" in result

def test_get_ollama_available_success(importer, mock_window):
    importer.provider = "ollama"
    mock_window.core.models.ollama.get_status.return_value = {"status": True, "models": [{"name": "test:latest"}]}

    def fake_create_empty(append=False):
        fake = type("FakeModel", (), {})()
        fake.llama_index = {}
        return fake

    mock_window.core.models.create_empty.side_effect = fake_create_empty
    result = importer.get_ollama_available()
    assert "test" in result