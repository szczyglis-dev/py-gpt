#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packaging.version import Version

from pygpt_net.item.prompt import PromptItem
from pygpt_net.provider.core.prompt.json_file import JsonFileProvider


def make_window(tmp_path):
    config = SimpleNamespace(path=str(tmp_path), append_meta=MagicMock(return_value={"version": "test"}))
    return SimpleNamespace(core=SimpleNamespace(config=config, debug=SimpleNamespace(log=MagicMock())))


def test_prompt_json_provider_create_save_load_and_dump(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    with patch("pygpt_net.provider.core.prompt.json_file.uuid.uuid4", return_value="p-uuid"):
        prompt = PromptItem()
        assert provider.create(prompt) == "p-uuid"
    prompt.name = "Coder"
    prompt.content = "Help"

    provider.save({prompt.id: prompt})
    loaded = provider.load()
    assert loaded[prompt.id].name == "Coder"
    assert loaded[prompt.id].content == "Help"
    assert json.loads(provider.dump(prompt)) == provider.serialize(prompt)


def test_prompt_json_provider_existing_id_partial_deserialize_and_patch(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    prompt = PromptItem()
    prompt.id = "existing"
    provider.create_id = MagicMock()
    assert provider.create(prompt) == "existing"
    provider.create_id.assert_not_called()

    restored = PromptItem()
    restored.id = "keep"
    provider.deserialize({"name": "N", "content": "C"}, restored)
    assert restored.id == "keep"
    assert provider.serialize(restored) == {"id": "keep", "name": "N", "content": "C"}
    assert provider.patch(Version("9.0")) is False


def test_prompt_json_provider_load_invalid_shapes_and_errors(tmp_path):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    assert provider.load() == {}

    for value in (None, "", {"other": {}}):
        (tmp_path / "prompts.json").write_text(json.dumps(value), encoding="utf-8")
        assert provider.load() == {}

    with patch("pygpt_net.provider.core.prompt.json_file.os.path.exists", return_value=True), \
            patch("builtins.open", side_effect=OSError("bad")):
        assert provider.load() == {}
    window.core.debug.log.assert_called_once()


def test_prompt_json_provider_truncate_and_error_paths(tmp_path, capsys):
    window = make_window(tmp_path)
    provider = JsonFileProvider(window)
    provider.truncate("chat")
    raw = json.loads((tmp_path / "prompts.json").read_text(encoding="utf-8"))
    assert raw["items"] == {}

    with patch("builtins.open", side_effect=OSError("bad")):
        provider.truncate("chat")
    assert window.core.debug.log.call_count == 1

    window.core.debug.log.reset_mock()
    with patch("builtins.open", side_effect=OSError("bad")):
        provider.save({})
    window.core.debug.log.assert_called_once()
    assert "Error while saving prompts" in capsys.readouterr().out
