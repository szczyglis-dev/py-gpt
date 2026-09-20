#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import builtins
import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


APP_PATH = Path(__file__).resolve().parents[1] / "src" / "pygpt_net" / "app.py"


def _load_app_module():
    """Load app.py without importing its real UI/provider dependency graph."""
    fake_icons = ModuleType("pygpt_net.icons_rc")
    fake_utils = ModuleType("pygpt_net.utils")
    fake_utils.set_env = MagicMock()

    spec = importlib.util.spec_from_file_location("pygpt_net._test_app_entrypoint", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    original_open = builtins.open
    try:
        with patch.dict(
            sys.modules,
            {
                "pygpt_net.icons_rc": fake_icons,
                "pygpt_net.utils": fake_utils,
            },
        ):
            spec.loader.exec_module(module)
    finally:
        # app.py intentionally patches builtins.open in production. The unit test
        # must never leave that process-global hook installed for other tests.
        builtins.open = original_open
    return module


@pytest.fixture
def app_module():
    return _load_app_module()


def test_open_wrapper_blocks_snap_dotenv(app_module):
    original_open = MagicMock()
    app_module._original_open = original_open
    app_module.os = SimpleNamespace(environ={"SNAP": "/snap/pygpt/current", "SNAP_NAME": "pygpt"})

    text_handle = app_module.open_wrapper("/home/test/.env", "r")
    binary_handle = app_module.open_wrapper(".env", "rb")

    assert isinstance(text_handle, io.StringIO)
    assert text_handle.read() == ""
    assert isinstance(binary_handle, io.BytesIO)
    assert binary_handle.read() == b""
    original_open.assert_not_called()


def test_open_wrapper_delegates_for_regular_files(app_module):
    sentinel = object()
    original_open = MagicMock(return_value=sentinel)
    app_module._original_open = original_open
    app_module.os = SimpleNamespace(environ={})

    result = app_module.open_wrapper("config.json", "w", encoding="utf-8")

    assert result is sentinel
    original_open.assert_called_once_with("config.json", "w", encoding="utf-8")


def _extension_importer(original_import):
    prefixes = (
        "pygpt_net.plugin.",
        "pygpt_net.provider.",
        "pygpt_net.tools.",
    )

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(prefixes) and fromlist:
            module = ModuleType(name)
            for attr in fromlist:
                if attr != "*":
                    setattr(module, attr, type(attr, (), {"__module__": name}))
            return module
        return original_import(name, globals, locals, fromlist, level)

    return fake_import


def _runtime_modules(preloader, launcher_factory):
    preload_module = ModuleType("pygpt_net.preload")
    preload_module._start_preloader = MagicMock(return_value=preloader)

    launcher_module = ModuleType("pygpt_net.launcher")
    launcher_module.Launcher = launcher_factory

    init_module = ModuleType("pygpt_net.__init__")
    init_module.__version__ = "test"
    return {
        "pygpt_net.preload": preload_module,
        "pygpt_net.launcher": launcher_module,
        "pygpt_net.__init__": init_module,
    }, preload_module, launcher_module


def test_run_registers_custom_extensions_and_closes_preloader(app_module, monkeypatch):
    freeze_support = MagicMock()
    monkeypatch.setattr("multiprocessing.freeze_support", freeze_support)

    preloader = MagicMock()
    launcher = MagicMock()
    launcher.window = SimpleNamespace(core=SimpleNamespace(llm=SimpleNamespace(sync_custom=MagicMock())))
    modules, preload_module, launcher_module = _runtime_modules(
        preloader,
        MagicMock(return_value=launcher),
    )

    original_import = builtins.__import__
    custom = [object() for _ in range(9)]
    keys = (
        "plugins",
        "llms",
        "vector_stores",
        "loaders",
        "audio_input",
        "audio_output",
        "web",
        "agents",
        "tools",
    )

    with patch.dict(sys.modules, modules), patch.object(
        builtins,
        "__import__",
        _extension_importer(original_import),
    ):
        app_module.run(**{key: [value] for key, value in zip(keys, custom)})

    freeze_support.assert_called_once_with()
    preload_module._start_preloader.assert_called_once_with(title="PyGPT", message="vtest")
    launcher_module.Launcher.assert_called_once_with()
    launcher.attach_preloader.assert_called_once_with(preloader)
    launcher.init.assert_called_once_with()
    launcher.add_plugin.assert_any_call(custom[0])
    launcher.add_llm.assert_any_call(custom[1])
    launcher.add_vector_store.assert_any_call(custom[2])
    launcher.add_loader.assert_any_call(custom[3])
    launcher.add_audio_input.assert_any_call(custom[4])
    launcher.add_audio_output.assert_any_call(custom[5])
    launcher.add_web.assert_any_call(custom[6])
    launcher.add_agent.assert_any_call(custom[7])
    launcher.add_tool.assert_any_call(custom[8])
    launcher.window.core.llm.sync_custom.assert_called_once_with(force=True)
    launcher.run.assert_called_once_with()
    preloader.close.assert_called_once_with(wait=False)


def test_run_handles_launcher_failure_without_leaking_modules(app_module, monkeypatch, capsys):
    monkeypatch.setattr("multiprocessing.freeze_support", MagicMock())
    preloader = MagicMock()
    modules, _, _ = _runtime_modules(
        preloader,
        MagicMock(side_effect=RuntimeError("boom")),
    )

    original_import = builtins.__import__
    before = {name: sys.modules.get(name) for name in modules}
    with patch.dict(sys.modules, modules), patch.object(
        builtins,
        "__import__",
        _extension_importer(original_import),
    ):
        app_module.run()

    out = capsys.readouterr().out
    assert "Fatal error during application startup:" in out
    assert "boom" in out
    preloader.close.assert_called_once_with(wait=False)
    for name, previous in before.items():
        if previous is None:
            assert name not in sys.modules
        else:
            assert sys.modules[name] is previous
