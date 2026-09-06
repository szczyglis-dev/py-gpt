import configparser
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.plugins.plugins as mod
from pygpt_net.core.plugins.plugins import Plugins


def make_manager(user_plugins=None):
    user_plugins = {} if user_plugins is None else user_plugins
    cfg = SimpleNamespace(
        data={"plugins_enabled": {}},
        get=MagicMock(side_effect=lambda key: user_plugins if key == "plugins" else None),
        save=MagicMock(),
        get_app_path=MagicMock(return_value="/app"),
    )
    dialogs = SimpleNamespace(register_dictionary=MagicMock())
    window = SimpleNamespace(
        core=SimpleNamespace(config=cfg, debug=SimpleNamespace(log=MagicMock())),
        ui=SimpleNamespace(dialogs=dialogs),
    )
    manager = Plugins.__new__(Plugins)
    manager.window = window
    manager.allowed_types = []
    manager.plugins = {}
    manager.presets = {}
    manager.provider = MagicMock()
    return manager, cfg, dialogs


def plugin(pid="p", name="Plugin", options=None, *, locale=False):
    p = SimpleNamespace(
        id=pid,
        name=name,
        description=f"{name} desc",
        options={} if options is None else options,
        use_locale=locale,
        enabled=False,
        attach=MagicMock(),
        destroy=MagicMock(),
    )
    return p


def test_registry_getters_sort_by_translated_name(monkeypatch):
    manager, *_ = make_manager()
    a = plugin("a", "Zulu"); b = plugin("b", "Alpha")
    manager.plugins = {"a": a, "b": b}
    monkeypatch.setattr(mod, "trans", lambda key, domain=None: key)
    assert manager.is_registered("a") is True
    assert manager.all() is manager.plugins
    assert manager.get_ids() == ["a", "b"]
    assert manager.get_ids(sort=True) == ["b", "a"]
    assert manager.get("a") is a and manager.get("missing") is None


def test_get_option_handles_missing_plugin_option_and_value():
    manager, *_ = make_manager()
    manager.plugins["p"] = plugin(options={"x": {"value": 7}})
    assert manager.get_option("p", "x") == 7
    assert manager.get_option("p", "missing") is None
    assert manager.get_option("missing", "x") is None


def test_register_applies_saved_values_removes_stale_and_registers_dict_options():
    user = {"p": {"x": "saved", "stale": 1}}
    manager, cfg, dialogs = make_manager(user)
    p = plugin(options={
        "x": {"type": "text", "value": "default"},
        "mapping": {"type": "dict", "value": {}, "label": "Map"},
        "run": {"type": "cmd", "value": {}, "label": "Run"},
    })
    manager.register(p)
    p.attach.assert_called_once_with(manager.window)
    assert manager.plugins["p"].options["x"]["value"] == "saved"
    assert "stale" not in user["p"]
    assert manager.plugins["p"].initial_options["x"]["value"] == "default"
    cfg.save.assert_called_once_with()
    calls = dialogs.register_dictionary.call_args_list
    assert calls[0].args[:2] == ("mapping", "plugin.p")
    assert calls[1].args[:2] == ("run.params", "plugin.p")


def test_apply_all_options_restores_initial_values_and_removes_invalid_user_keys():
    user = {"p": {"x": "saved", "bad": 3}}
    manager, cfg, _ = make_manager(user)
    p = plugin(options={"x": {"type": "text", "value": "mutated"}})
    p.initial_options = {"x": {"type": "text", "value": "default"}}
    manager.plugins["p"] = p
    manager.apply_all_options()
    assert p.options["x"]["value"] == "saved"
    assert "bad" not in user["p"]
    cfg.save.assert_called_once_with()


def test_unregister_enable_disable_destroy_and_has_options():
    manager, cfg, _ = make_manager()
    p = plugin(options={"x": {"value": 1}})
    manager.plugins["p"] = p
    assert manager.has_options("p") is True
    manager.enable("p")
    assert p.enabled is True and cfg.data["plugins_enabled"]["p"] is True
    manager.disable("p")
    assert p.enabled is False and cfg.data["plugins_enabled"]["p"] is False
    assert cfg.save.call_count == 2
    manager.destroy("p")
    p.destroy.assert_called_once_with()
    manager.unregister("p")
    assert manager.is_registered("p") is False


def test_restore_options_preserves_persisted_values_unless_all():
    manager, *_ = make_manager()
    p = plugin(options={
        "keep": {"value": "user", "persist": True},
        "reset": {"value": "user2", "persist": False},
    })
    p.initial_options = {
        "keep": {"value": "default", "persist": True},
        "reset": {"value": "default2", "persist": False},
    }
    manager.plugins["p"] = p
    manager.restore_options("p")
    assert p.options["keep"]["value"] == "user"
    assert p.options["reset"]["value"] == "default2"
    manager.restore_options("p", all=True)
    assert p.options["keep"]["value"] == "default"


def test_get_name_and_desc_use_default_translation_and_locale_domain(monkeypatch):
    manager, *_ = make_manager()
    p = plugin("p", "Fallback")
    manager.plugins["p"] = p
    monkeypatch.setattr(mod, "trans", lambda key, domain=None: key)
    assert manager.get_name("p") == "Fallback"
    assert manager.get_desc("p") == "Fallback desc"

    p.use_locale = True
    monkeypatch.setattr(mod, "trans", lambda key, domain=None: f"{domain}:{key}")
    assert manager.get_name("p") == "plugin.p:plugin.name"
    assert manager.get_desc("p") == "plugin.p:plugin.description"


def test_dump_locale_writes_plugin_and_option_text(tmp_path):
    manager, *_ = make_manager()
    p = plugin(options={
        "b": {"label": "B label", "description": "B desc", "tooltip": "tip"},
        "a": {"label": "A label", "description": "A desc", "tooltip": ""},
    })
    path = tmp_path / "locale.ini"
    manager.dump_locale(p, str(path))
    ini = configparser.ConfigParser()
    ini.read(path, encoding="utf-8")
    section = ini["LOCALE"]
    assert section["plugin.name"] == "Plugin"
    assert section["plugin.description"] == "Plugin desc"
    assert section["a.label"] == "A label"
    assert section["b.tooltip"] == "tip"
    assert "a.tooltip" not in section


def test_basic_preset_lifecycle_delegates_provider():
    manager, *_ = make_manager()
    manager.set_preset("one", {"config": {}})
    assert manager.has_preset("one") is True
    assert manager.get_preset("one") == {"config": {}}
    assert manager.get_preset("missing") is None
    manager.replace_presets({"two": {"config": {}}})
    assert manager.get_presets() == {"two": {"config": {}}}
    manager.provider.load.return_value = {"loaded": {"config": {}}}
    manager.load_presets()
    assert "loaded" in manager.presets
    manager.save_presets()
    manager.provider.save.assert_called_once_with(manager.presets)


def test_remove_and_update_plugin_params_across_presets():
    manager, *_ = make_manager()
    manager.presets = {
        "a": {"config": {"p": {"x": 1, "y": 2}}},
        "b": {"config": {"p": {"x": 3}, "q": {"z": 4}}},
    }
    manager.save_presets = MagicMock()
    assert manager.update_param_in_presets("p", "x", 9) is True
    assert manager.presets["a"]["config"]["p"]["x"] == 9
    assert manager.presets["b"]["config"]["p"]["x"] == 9
    assert manager.remove_plugin_param_from_presets("p", "y") is True
    assert "y" not in manager.presets["a"]["config"]["p"]
    assert manager.remove_plugin_param_from_presets("q") is True
    assert "q" not in manager.presets["b"]["config"]
    assert manager.save_presets.call_count == 3


def test_clean_presets_removes_unknown_keys_only_for_registered_plugins():
    manager, *_ = make_manager()
    manager.plugins = {"p": plugin(options={"good": {"value": 1}})}
    manager.presets = {"a": {"config": {"p": {"good": 1, "bad": 2}, "unknown": {"x": 1}}}}
    manager.save_presets = MagicMock()
    manager.clean_presets()
    assert manager.presets["a"]["config"]["p"] == {"good": 1}
    assert manager.presets["a"]["config"]["unknown"] == {"x": 1}
    manager.save_presets.assert_called_once_with()


def test_remove_and_update_preset_values_save_only_when_changed():
    manager, *_ = make_manager()
    manager.presets = {"a": {"config": {"p": {"x": 1}}}}
    manager.save_presets = MagicMock()
    manager.update_preset_values("p", "x", 2)
    assert manager.presets["a"]["config"]["p"]["x"] == 2
    manager.remove_preset_values("p", "x")
    assert manager.presets["a"]["config"]["p"] == {}
    assert manager.save_presets.call_count == 2


def test_reset_options_removes_user_and_preset_values():
    user = {"p": {"x": 1, "y": 2}}
    manager, cfg, _ = make_manager(user)
    manager.remove_preset_values = MagicMock()
    manager.reset_options("p", ["x", "missing"])
    assert user["p"] == {"y": 2}
    assert manager.remove_preset_values.call_args_list[0].args == ("p", "x")
    assert manager.remove_preset_values.call_args_list[1].args == ("p", "missing")
    cfg.save.assert_called_once_with()


def test_reset_reload_and_dump_locale_helpers(monkeypatch):
    manager, cfg, _ = make_manager()
    manager.plugins = {"p": plugin()}
    manager.restore_options = MagicMock(); manager.apply_all_options = MagicMock()
    manager.reset_all()
    manager.restore_options.assert_called_once_with("p", all=True)
    manager.apply_all_options.assert_called_once_with()

    manager.reset_all = MagicMock(); manager.presets = {}
    manager.reload_all()
    manager.reset_all.assert_called_once_with()

    manager.dump_locale = MagicMock()
    manager.dump_locale_by_id("p", "/x.ini")
    manager.dump_locale.assert_called_once_with(manager.plugins["p"], "/x.ini")
