#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from packaging.version import Version

from pygpt_net.provider.core.plugin_preset.json_file import JsonFileProvider


def make_window(tmp_path):
    config = SimpleNamespace(path=str(tmp_path), append_meta=MagicMock(return_value={"version": "3.0.0"}))
    return SimpleNamespace(core=SimpleNamespace(config=config))


def test_plugin_preset_install_save_load_and_version(tmp_path, capsys):
    provider = JsonFileProvider(make_window(tmp_path))
    provider.install()
    assert (tmp_path / "plugin_presets.json").exists()
    assert "Installed:" in capsys.readouterr().out
    assert provider.load() == {}
    assert provider.get_version() == "3.0.0"

    items = {"plugin": {"enabled": True}}
    provider.save(items)
    assert provider.load() == items


def test_plugin_preset_install_does_not_overwrite_existing_file(tmp_path):
    path = tmp_path / "plugin_presets.json"
    path.write_text(json.dumps({"items": {"keep": 1}}), encoding="utf-8")
    provider = JsonFileProvider(make_window(tmp_path))
    provider.save = MagicMock()
    provider.install()
    provider.save.assert_not_called()


def test_plugin_preset_get_version_handles_missing_and_empty_metadata(tmp_path):
    provider = JsonFileProvider(make_window(tmp_path))
    assert provider.get_version() is None

    path = tmp_path / "plugin_presets.json"
    for payload in (None, "", {"items": {}}, {"__meta__": {}, "items": {}}):
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert provider.get_version() is None


def test_plugin_preset_load_missing_items_missing_file_and_json_error(tmp_path, capsys):
    provider = JsonFileProvider(make_window(tmp_path))
    assert provider.load() is None

    path = tmp_path / "plugin_presets.json"
    path.write_text(json.dumps({"x": 1}), encoding="utf-8")
    assert provider.load() == {}

    path.write_text("{broken", encoding="utf-8")
    result = provider.load()
    assert result == {}
    assert "FATAL ERROR" in capsys.readouterr().out


def test_plugin_preset_save_error_and_patch_delegate(tmp_path, capsys):
    provider = JsonFileProvider(make_window(tmp_path))
    with patch("builtins.open", side_effect=OSError("bad")):
        provider.save({"x": 1})
    assert "FATAL ERROR" in capsys.readouterr().out

    provider.patcher.execute = MagicMock(return_value=True)
    version = Version("2.0")
    assert provider.patch(version) is True
    provider.patcher.execute.assert_called_once_with(version)
