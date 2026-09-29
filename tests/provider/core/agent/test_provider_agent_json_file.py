#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packaging.version import Version

from pygpt_net.item.agent import AgentItem
from pygpt_net.item.builder_layout import BuilderLayoutItem
from pygpt_net.provider.core.agent.json_file import JsonFileProvider


def make_window(tmp_path):
    config = SimpleNamespace(path=str(tmp_path), append_meta=MagicMock(return_value={"version": "test"}))
    return SimpleNamespace(core=SimpleNamespace(config=config, debug=SimpleNamespace(log=MagicMock())))


def test_agent_json_provider_create_id_and_existing_id(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    with patch("pygpt_net.provider.core.agent.json_file.uuid.uuid4", return_value="uuid-1"):
        item = AgentItem()
        assert provider.create(item) == "uuid-1"
        assert item.id == "uuid-1"

    item.id = "existing"
    provider.create_id = MagicMock(return_value="unused")
    assert provider.create(item) == "existing"
    provider.create_id.assert_not_called()


def test_agent_json_provider_save_and_load_round_trip(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    layout = BuilderLayoutItem()
    layout.id = "layout"
    layout.name = "Main"
    layout.data = {"zoom": 1.2}
    agent = AgentItem()
    agent.id = "a1"
    agent.name = "Agent"
    agent.layout = {"x": 1}
    agent.schema = [{"name": "worker"}]

    provider.save(layout, {"a1": agent})

    raw = json.loads((tmp_path / "agents.json").read_text(encoding="utf-8"))
    assert raw["__meta__"] == {"version": "test"}
    assert raw["layout"]["data"] == {"zoom": 1.2}
    assert raw["items"]["a1"]["schema"] == [{"name": "worker"}]

    loaded = provider.load()
    assert loaded["layout"].id == "layout"
    assert loaded["layout"].data == {"zoom": 1.2}
    assert loaded["agents"]["a1"].name == "Agent"
    assert loaded["agents"]["a1"].schema == [{"name": "worker"}]


def test_agent_json_provider_load_handles_invalid_json_and_missing_file(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    assert provider.load() == {"layout": None, "agents": {}}

    (tmp_path / "agents.json").write_text("{broken", encoding="utf-8")
    assert provider.load() == {"layout": None, "agents": {}}


def test_agent_json_provider_load_logs_io_errors(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    with patch("pygpt_net.provider.core.agent.json_file.os.path.exists", return_value=True), \
            patch("builtins.open", side_effect=OSError("boom")):
        assert provider.load() == {"layout": None, "agents": {}}
    window.core.debug.log.assert_called_once()


def test_agent_json_provider_save_logs_errors(tmp_path, capsys):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    with patch("builtins.open", side_effect=OSError("boom")):
        provider.save(None, {})
    window.core.debug.log.assert_called_once()
    assert "Error while saving agents" in capsys.readouterr().out


def test_agent_json_provider_serializers_dump_and_patch(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    item = AgentItem()
    item.id = "a"
    item.name = "N"
    item.layout = {"k": 1}
    item.schema = [1]
    assert JsonFileProvider.serialize(item) == {"id": "a", "name": "N", "layout": {"k": 1}, "schema": [1]}

    restored = AgentItem()
    restored.id = "keep"
    JsonFileProvider.deserialize({"name": "Changed", "schema": [2]}, restored)
    assert restored.id == "keep"
    assert restored.name == "Changed"
    assert restored.schema == [2]

    layout = BuilderLayoutItem()
    layout.id, layout.name, layout.data = "l", "Layout", {"x": 2}
    assert JsonFileProvider.serialize_layout(layout) == {"id": "l", "name": "Layout", "data": {"x": 2}}
    assert JsonFileProvider.serialize_layout(None) == {"id": "", "name": "", "data": {}}

    restored_layout = BuilderLayoutItem()
    JsonFileProvider.deserialize_layout({"name": "L2", "data": {"y": 3}}, restored_layout)
    assert restored_layout.id is None
    assert restored_layout.name == "L2"
    assert restored_layout.data == {"y": 3}

    assert json.loads(provider.dump(item))["id"] == "a"
    assert provider.patch(Version("2.0.0")) is False
