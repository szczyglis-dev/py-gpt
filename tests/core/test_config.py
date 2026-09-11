#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from packaging.version import Version

from tests.mocks import mock_window_conf
import pygpt_net.config as config_module
from pygpt_net.config import Config, quick_get_config_value


def _bare_config():
    cfg = object.__new__(Config)
    cfg.window = None
    cfg.path = None
    cfg.initialized = False
    cfg.initialized_base = False
    cfg.initialized_workdir = False
    cfg.db_echo = False
    cfg.data = {}
    cfg.data_base = {}
    cfg.data_session = {}
    cfg.version = "1.2.3"
    cfg.dirs = {
        "capture": "capture", "css": "css", "data": "data", "history": "history",
        "idx": "idx", "ctx_idx": "ctx_idx", "img": "img", "locale": "locale",
        "presets": "presets", "upload": "upload", "tmp": "tmp", "video": "video",
        "music": "music",
    }
    cfg._app_path = None
    cfg._version_cache = None
    cfg._build_cache = None
    cfg.provider = MagicMock()
    return cfg


def test_get_user_path(mock_window_conf):
    config = _bare_config()
    config.path = "test_path"
    assert config.get_user_path() == "test_path"


def test_get_available_langs(mock_window_conf, monkeypatch):
    config = _bare_config()
    config.get_app_path = MagicMock(return_value="test_path")
    config.get_user_path = MagicMock(return_value="test_path")
    exists_mock = MagicMock(return_value=True)
    listdir_mock = MagicMock(return_value=["locale.en.ini", "locale.de.ini", "locale.fr.ini"])
    monkeypatch.setattr(os.path, "exists", exists_mock)
    monkeypatch.setattr(os, "listdir", listdir_mock)
    assert config.get_available_langs() == ["en", "de", "fr"]


def test_quick_get_config_value_uses_minimal_flow(monkeypatch):
    fake = MagicMock()
    fake.prepare_workdir.return_value = "/work"
    fake.get.return_value = "value"
    factory = MagicMock(return_value=fake)
    monkeypatch.setattr(config_module, "Config", factory)

    assert quick_get_config_value("key", "fallback") == "value"
    fake.prepare_workdir.assert_called_once_with()
    fake.set_workdir.assert_called_once_with("/work")
    fake.load_config.assert_called_once_with(all=False)
    fake.get.assert_called_once_with("key", "fallback")


def test_constructor_wires_profile_provider_and_workdir(monkeypatch):
    profile = MagicMock()
    provider = MagicMock()
    monkeypatch.setattr(config_module, "Profile", MagicMock(return_value=profile))
    monkeypatch.setattr(config_module, "JsonFileProvider", MagicMock(return_value=provider))
    monkeypatch.setattr(Config, "get_version", lambda self: "9.8.7")
    monkeypatch.setattr(Config, "get_base_workdir", staticmethod(lambda: "/base"))
    monkeypatch.setattr(Config, "get_app_path", lambda self: "/app")
    monkeypatch.setattr(Config, "prepare_workdir", staticmethod(lambda: "/work"))

    cfg = Config(window="window")

    assert cfg.window == "window"
    assert cfg.version == "9.8.7"
    profile.init.assert_called_once_with("/base")
    assert provider.path_app == "/app"
    assert provider.path == "/work"
    assert cfg.path == "/work"
    assert cfg.initialized_workdir is True


def test_is_compiled_uses_sys_frozen(monkeypatch):
    cfg = _bare_config()
    monkeypatch.delattr(config_module.sys, "frozen", raising=False)
    assert cfg.is_compiled() is False
    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    assert cfg.is_compiled() is True


def test_install_initializes_database_and_provider():
    cfg = _bare_config()
    cfg.db_echo = True
    cfg.window = SimpleNamespace(core=SimpleNamespace(db=MagicMock()))
    cfg.install()
    assert cfg.window.core.db.echo is True
    cfg.window.core.db.init.assert_called_once_with()
    cfg.provider.install.assert_called_once_with()


def test_get_path_prepares_workdir_only_once():
    cfg = _bare_config()
    cfg.prepare_workdir = MagicMock(return_value="/prepared")
    cfg.set_workdir = MagicMock(side_effect=lambda path: setattr(cfg, "path", path))

    assert cfg.get_path() == "/prepared"
    cfg.prepare_workdir.assert_called_once_with()
    cfg.initialized_workdir = True
    cfg.prepare_workdir.reset_mock()
    assert cfg.get_path() == "/prepared"
    cfg.prepare_workdir.assert_not_called()


def test_get_base_workdir_default_and_override_without_process_env(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    fake_os = SimpleNamespace(
        environ={},
        path=os.path,
        getcwd=lambda: str(cwd),
        makedirs=os.makedirs,
    )
    monkeypatch.setattr(config_module, "os", fake_os)
    monkeypatch.setattr(config_module.Path, "home", classmethod(lambda cls: home))

    assert Config.get_base_workdir() == os.path.join(str(home), ".config", Config.CONFIG_DIR)

    fake_os.environ["PYGPT_WORKDIR"] = "relative-work"
    relative = Config.get_base_workdir()
    assert relative == os.path.join(str(cwd), "relative-work")
    assert os.path.isdir(relative)

    absolute = tmp_path / "absolute-work"
    fake_os.environ["PYGPT_WORKDIR"] = str(absolute)
    assert Config.get_base_workdir() == str(absolute)
    assert absolute.is_dir()


def test_prepare_workdir_creates_and_reads_path_cfg_without_process_env(monkeypatch, tmp_path):
    base = tmp_path / "base"
    fake_os = SimpleNamespace(environ={}, path=os.path)
    monkeypatch.setattr(config_module, "os", fake_os)
    monkeypatch.setattr(Config, "get_base_workdir", staticmethod(lambda: str(base)))

    assert Config.prepare_workdir() == str(base)
    assert (base / "path.cfg").read_text(encoding="utf-8") == ""

    alternate = tmp_path / "alternate"
    alternate.mkdir()
    (base / "path.cfg").write_text(str(alternate), encoding="utf-8")
    assert Config.prepare_workdir() == str(alternate)


def test_set_workdir_and_patch_delegate_to_provider():
    cfg = _bare_config()
    cfg.initialized = True
    cfg.init = MagicMock()
    cfg.set_workdir("/new", reload=True)
    assert cfg.path == "/new"
    assert cfg.provider.path == "/new"
    assert cfg.initialized is False
    cfg.init.assert_called_once_with(True)

    version = Version("2.0.0")
    cfg.provider.patch.return_value = True
    assert cfg.patch(version) is True
    cfg.provider.patch.assert_called_once_with(version)


def test_get_user_dir_data_dir_and_unknown(tmp_path):
    cfg = _bare_config()
    cfg.path = str(tmp_path)
    cfg.data["upload.data_dir"] = True

    assert cfg.get_user_dir("img") == os.path.join(str(tmp_path), "data", "img")
    assert cfg.get_user_dir("history") == os.path.join(str(tmp_path), "history")
    with pytest.raises(Exception, match="Unknown dir"):
        cfg.get_user_dir("missing")


def test_get_workdir_prefix_switches_for_sandbox():
    cfg = _bare_config()
    cfg.get_user_dir = MagicMock(return_value="/user/data")
    plugins = MagicMock()
    filesystem = SimpleNamespace(get_data_dir=MagicMock(return_value='/user/data'))
    cfg.window = SimpleNamespace(core=SimpleNamespace(plugins=plugins, filesystem=filesystem))

    plugins.get_option.return_value = False
    assert cfg.get_workdir_prefix() == "/user/data"
    plugins.get_option.return_value = True
    assert cfg.get_workdir_prefix() == "/data"


def test_plugin_config_update_and_remove():
    cfg = _bare_config()
    plugins = MagicMock()
    cfg.window = SimpleNamespace(core=SimpleNamespace(plugins=plugins))

    assert cfg.update_plugin_config("demo", "enabled", True) is True
    assert cfg.data == {"plugins": {"demo": {"enabled": True}}}
    assert cfg.remove_plugin_config("demo", "enabled") is True
    plugins.remove_plugin_param_from_presets.assert_called_once_with("demo", "enabled")
    assert cfg.remove_plugin_config("missing") is False

    cfg.data = None
    assert cfg.update_plugin_config("demo", "enabled", False) is False


def test_get_app_path_cached_compiled_and_source(monkeypatch, tmp_path):
    cfg = _bare_config()
    cfg._app_path = "/cached"
    assert cfg.get_app_path() == "/cached"

    cfg._app_path = None
    cfg.is_compiled = MagicMock(return_value=True)
    monkeypatch.setattr(config_module.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert cfg.get_app_path() == os.path.abspath(str(tmp_path))

    cfg._app_path = None
    cfg.is_compiled = MagicMock(return_value=False)
    assert cfg.get_app_path() == os.path.abspath(os.path.dirname(config_module.__file__))


def test_init_full_minimal_and_idempotent():
    cfg = _bare_config()
    cfg.get_version = MagicMock(return_value="1.2.3")
    cfg.get_build = MagicMock(return_value="2026.09.07")
    installer = MagicMock()
    platforms = MagicMock()
    platforms.get_os.return_value = "Linux"
    platforms.get_architecture.return_value = "x86_64"
    cfg.window = SimpleNamespace(core=SimpleNamespace(installer=installer, platforms=platforms))
    cfg.load = MagicMock()

    cfg.init(all=True)
    installer.install.assert_called_once_with()
    cfg.load.assert_called_once_with(True)

    cfg.initialized = False
    cfg.load.reset_mock()
    installer.install.reset_mock()
    cfg.init(all=False)
    installer.install.assert_not_called()
    cfg.load.assert_called_once_with(False)

    cfg.load.reset_mock()
    cfg.init(all=False)
    cfg.load.assert_not_called()


def test_version_and_build_parse_and_cache(tmp_path):
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "3.4.5"\n__build__ = "2026.09.07"\n', encoding="utf-8")
    cfg = _bare_config()
    cfg.get_app_path = MagicMock(return_value=str(tmp_path))

    assert cfg.get_version() == "3.4.5"
    assert cfg.get_build() == "2026.09.07"
    init_file.write_text('__version__ = "changed"\n__build__ = "changed"\n', encoding="utf-8")
    assert cfg.get_version() == "3.4.5"
    assert cfg.get_build() == "2026.09.07"


def test_accessors_session_and_language_without_process_env(monkeypatch):
    cfg = _bare_config()
    cfg.data = {"a": 1, "lang": "pl"}
    cfg.data_session = {"session": 2}
    cfg.provider.get_options.return_value = {"o": 1}
    cfg.provider.get_sections.return_value = {"s": 1}
    monkeypatch.setattr(config_module, "os", SimpleNamespace(environ={}))

    assert cfg.get_options() == {"o": 1}
    assert cfg.get_sections() == {"s": 1}
    assert cfg.get("a") == 1
    assert cfg.get("missing", 9) == 9
    assert cfg.get_session("session") == 2
    assert cfg.get_lang() == "pl"

    cfg.set("b", 3)
    cfg.set_session("other", 4)
    assert cfg.has("b") is True
    assert cfg.has_session("other") is True
    assert cfg.all() is cfg.data
    assert cfg.all_session() is cfg.data_session


def test_get_available_langs_merges_real_temp_directories(tmp_path):
    cfg = _bare_config()
    app = tmp_path / "app"
    user = tmp_path / "user"
    app_locale = app / "data" / "locale"
    user_locale = user / "locale"
    app_locale.mkdir(parents=True)
    user_locale.mkdir(parents=True)
    for name in ("locale.de.ini", "locale.en.ini", "ignore.txt"):
        (app_locale / name).write_text("", encoding="utf-8")
    for name in ("locale.pl.ini", "locale.de.ini", "locale.fr.ini"):
        (user_locale / name).write_text("", encoding="utf-8")
    cfg.get_app_path = MagicMock(return_value=str(app))
    cfg.get_user_path = MagicMock(return_value=str(user))

    assert cfg.get_available_langs() == ["en", "pl", "de", "fr"]


def test_append_meta_uses_mocked_clock(monkeypatch):
    cfg = _bare_config()

    class FixedDateTime:
        @classmethod
        def now(cls):
            return SimpleNamespace(strftime=lambda fmt: "2026-09-07T00:00:00")

    monkeypatch.setattr(config_module.datetime, "datetime", FixedDateTime)
    assert cfg.append_meta() == {
        "version": "1.2.3",
        "app.version": "1.2.3",
        "updated_at": "2026-09-07T00:00:00",
    }


def test_load_config_base_and_from_base_copy():
    cfg = _bare_config()
    cfg.window = SimpleNamespace(core=SimpleNamespace(
        modes=MagicMock(), models=MagicMock(), presets=MagicMock(), plugins=MagicMock()
    ))
    cfg.load_config = MagicMock()
    cfg.load(all=True)
    cfg.load_config.assert_called_once_with(True)
    cfg.window.core.modes.load.assert_called_once_with()
    cfg.window.core.models.load.assert_called_once_with()
    cfg.window.core.presets.load.assert_called_once_with()
    cfg.window.core.plugins.load_presets.assert_called_once_with()

    cfg.load_config = Config.load_config.__get__(cfg, Config)
    cfg.provider.load.return_value = {"z": 1, "a": 2}
    cfg.load_config(all=False)
    assert list(cfg.data) == ["a", "z"]

    cfg.provider.load_base.return_value = {"z": {"v": 1}, "a": 2}
    cfg.load_base_config()
    assert list(cfg.data_base) == ["a", "z"]
    cfg.data = {}
    cfg.from_base_config()
    assert cfg.data == cfg.data_base
    assert cfg.data is not cfg.data_base
    assert cfg.data["z"] is not cfg.data_base["z"]


def test_last_used_dir_get_set_and_base_helpers(tmp_path):
    cfg = _bare_config()
    default = tmp_path / "default"
    saved = tmp_path / "saved"
    default.mkdir()
    saved.mkdir()
    cfg.get_user_dir = MagicMock(return_value=str(default))
    cfg.data["dialog.last_dir"] = str(saved)
    assert cfg.get_last_used_dir() == str(saved)

    cfg.save = MagicMock()
    cfg.set_last_used_dir("/new/path")
    assert cfg.data["dialog.last_dir"] == "/new/path"
    cfg.save.assert_called_once_with()

    cfg.initialized_base = True
    cfg.data_base = {"one": 1}
    assert cfg.get_base("one") == 1
    assert cfg.get_base() == {"one": 1}
    assert cfg.get_base("missing") is None

    nested = {"items": []}
    data = {"old": nested}
    result = cfg.replace_key(data, "old", "new")
    assert result["new"] == nested
    assert result["new"] is not nested


def test_setup_env_uses_local_environment_proxy(monkeypatch, capsys):
    cfg = _bare_config()
    cfg.data = {
        "name": "PyGPT",
        "app.env": [
            {"name": "PYGPT_TEST_NAME", "value": "{name}"},
            {"name": "", "value": "ignored"},
            {"name": "PYGPT_TEST_BAD", "value": "{missing}"},
        ],
    }
    local_env = {}
    monkeypatch.setattr(config_module, "os", SimpleNamespace(environ=local_env))

    cfg.setup_env()

    assert local_env["PYGPT_TEST_NAME"] == "PyGPT"
    assert "PYGPT_TEST_BAD" not in local_env
    assert "Error setting env var:" in capsys.readouterr().out

    cfg.data["app.env"] = "not-a-list"
    cfg.setup_env()


def test_save_delegates_to_provider():
    cfg = _bare_config()
    cfg.data = {"a": 1}
    cfg.save("custom.json")
    cfg.provider.save.assert_called_once_with({"a": 1}, "custom.json")
