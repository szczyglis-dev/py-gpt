#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import signal as signal_module
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


LAUNCHER_PATH = Path(__file__).resolve().parents[1] / "src" / "pygpt_net" / "launcher.py"


def _module(name, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _load_launcher_module():
    class Flag:
        SecureScheme = 1
        LocalAccessAllowed = 2
        CorsEnabled = 4
        ViewSourceAllowed = 8

    class Scheme:
        registered = None

        def __init__(self, name):
            self.name = name
            self.flags = None

        def setFlags(self, flags):
            self.flags = flags

        @classmethod
        def registerScheme(cls, scheme):
            cls.registered = scheme

    Scheme.Flag = Flag

    class QPixmapCache:
        @staticmethod
        def setCacheLimit(value):
            QPixmapCache.limit = value

    class QCoreApplication:
        setAttribute = MagicMock()

    class QApplication:
        @staticmethod
        def primaryScreen():
            return None

    Qt = SimpleNamespace(
        AA_ShareOpenGLContexts="share",
        AA_DontUseNativeMenuBar="native-menu",
        QueuedConnection="queued",
    )
    qtcore = _module("PySide6.QtCore", QCoreApplication=QCoreApplication, Qt=Qt)
    qtgui = _module("PySide6.QtGui", QScreen=MagicMock(), QPixmapCache=QPixmapCache)
    qtwidgets = _module("PySide6.QtWidgets", QApplication=QApplication)
    qtweb = _module("PySide6.QtWebEngineCore", QWebEngineUrlScheme=Scheme)
    pyside = _module("PySide6", QtCore=qtcore)

    class AppEvent:
        APP_STARTED = "app-started"

        def __init__(self, event):
            self.event = event

    class Debug:
        init = MagicMock()

    class Platforms:
        prepare = MagicMock()

    dependency_specs = {
        "pygpt_net.core.events": {"AppEvent": AppEvent},
        "pygpt_net.core.access.shortcuts": {"GlobalShortcutFilter": type("GlobalShortcutFilter", (), {})},
        "pygpt_net.core.debug": {"Debug": Debug},
        "pygpt_net.core.platforms": {"Platforms": Platforms},
        "pygpt_net.tools": {"BaseTool": type("BaseTool", (), {})},
        "pygpt_net.ui.main": {"MainWindow": type("MainWindow", (), {})},
        "pygpt_net.plugin.base.plugin": {"BasePlugin": type("BasePlugin", (), {})},
        "pygpt_net.provider.agents.base": {"BaseAgent": type("BaseAgent", (), {})},
        "pygpt_net.provider.audio_input.base": {"BaseProvider": type("BaseAudioInput", (), {})},
        "pygpt_net.provider.audio_output.base": {"BaseProvider": type("BaseAudioOutput", (), {})},
        "pygpt_net.provider.llms.base": {"BaseLLM": type("BaseLLM", (), {})},
        "pygpt_net.provider.loaders.base": {"BaseLoader": type("BaseLoader", (), {})},
        "pygpt_net.provider.vector_stores.base": {"BaseStore": type("BaseStore", (), {})},
        "pygpt_net.provider.web.base": {"BaseProvider": type("BaseWeb", (), {})},
    }
    fake_modules = {
        "PySide6": pyside,
        "PySide6.QtCore": qtcore,
        "PySide6.QtGui": qtgui,
        "PySide6.QtWidgets": qtwidgets,
        "PySide6.QtWebEngineCore": qtweb,
    }
    fake_modules.update({name: _module(name, **attrs) for name, attrs in dependency_specs.items()})

    spec = importlib.util.spec_from_file_location("pygpt_net._test_launcher_entrypoint", LAUNCHER_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, fake_modules):
        spec.loader.exec_module(module)
    return module


@pytest.fixture
def launcher_module():
    return _load_launcher_module()


def test_qrc_scheme_registration_happens_on_isolated_import(launcher_module):
    scheme = launcher_module.QWebEngineUrlScheme.registered
    assert scheme.name == b"qrc"
    assert scheme.flags == 15


def test_launcher_defaults_and_multiprocessing_argv_cleanup(launcher_module):
    launcher = launcher_module.Launcher()
    assert launcher.app is None
    assert launcher.window is None
    assert launcher.debug is False
    assert launcher.force_legacy is False
    assert launcher.force_disable_gpu is False
    assert launcher._preloader is None

    assert launcher._clean_multiprocessing_argv([
        "--debug", "2", "--multiprocessing-fork", "parent_pid=123", "pipe_handle=456", "--keep",
    ]) == ["--debug", "2", "--keep"]


@pytest.mark.parametrize(("debug_value", "expected_level"), [("1", 20), ("2", 10)])
def test_setup_applies_flags_without_touching_process_environment(launcher_module, debug_value, expected_level):
    launcher = launcher_module.Launcher()
    debug_init = MagicMock()
    launcher_module.Debug = SimpleNamespace(init=debug_init)
    local_env = {}
    launcher_module.os = SimpleNamespace(environ=local_env)
    launcher_module.sys = SimpleNamespace(argv=[
        "pygpt", "--debug", debug_value, "--legacy", "1", "--disable-gpu", "1",
        "--workdir", "/isolated/workdir", "--multiprocessing-fork", "parent_pid=100", "--unknown",
    ])

    args = launcher.setup()

    debug_init.assert_called_once_with(expected_level)
    assert args["debug"] == debug_value
    assert launcher.debug is True
    assert launcher.force_legacy is True
    assert launcher.force_disable_gpu is True
    assert local_env["PYGPT_WORKDIR"] == "/isolated/workdir"
    # The real process environment is never written by this test.
    import os
    assert os.environ.get("PYGPT_WORKDIR") != "/isolated/workdir"


def test_setup_default_and_parser_failure(launcher_module, capsys):
    launcher = launcher_module.Launcher()
    debug_init = MagicMock()
    launcher_module.Debug = SimpleNamespace(init=debug_init)
    launcher_module.os = SimpleNamespace(environ={})
    launcher_module.sys = SimpleNamespace(argv=["pygpt"])

    assert launcher.setup() == {"debug": None, "legacy": None, "disable_gpu": None, "workdir": None}
    debug_init.assert_called_once_with(launcher_module.ERROR)

    launcher_module.argparse = SimpleNamespace(ArgumentParser=MagicMock(side_effect=RuntimeError("parse failed")))
    assert launcher.setup() == {}
    assert "Launcher setup error: parse failed" in capsys.readouterr().out


def test_init_builds_application_window_and_shortcut_filter(launcher_module):
    launcher = launcher_module.Launcher()
    launcher.setup = MagicMock(return_value={"debug": None})
    launcher_module.Platforms = SimpleNamespace(prepare=MagicMock())
    launcher_module.QCoreApplication = SimpleNamespace(setAttribute=MagicMock())

    app = MagicMock()
    app_factory = MagicMock(return_value=app)
    window = MagicMock()
    window_factory = MagicMock(return_value=window)
    shortcut = object()
    shortcut_factory = MagicMock(return_value=shortcut)
    launcher_module.QApplication = app_factory
    launcher_module.MainWindow = window_factory
    launcher_module.GlobalShortcutFilter = shortcut_factory
    launcher_module.sys = SimpleNamespace(argv=["pygpt"])
    launcher._preloader = MagicMock()

    launcher.init()

    launcher_module.Platforms.prepare.assert_called_once_with()
    launcher_module.QCoreApplication.setAttribute.assert_called_once_with(launcher_module.Qt.AA_ShareOpenGLContexts)
    app_factory.assert_called_once_with(["pygpt"])
    app.setAttribute.assert_called_once_with(launcher_module.QtCore.Qt.AA_DontUseNativeMenuBar)
    window_factory.assert_called_once_with(app, args={"debug": None})
    shortcut_factory.assert_called_once_with(window)
    window.appReady.connect.assert_called_once_with(launcher._on_window_ready, launcher_module.Qt.QueuedConnection)
    assert launcher.shortcut_filter is shortcut


def test_signal_and_preloader_lifecycle(launcher_module):
    launcher = launcher_module.Launcher()
    launcher.handle_signal(signal_module.SIGTERM, None)

    window = MagicMock()
    launcher.window = window
    launcher.handle_signal(signal_module.SIGINT, None)
    window.close.assert_called_once_with()

    preloader = MagicMock()
    launcher.attach_preloader(preloader)
    window.appReady.connect.assert_called_once_with(launcher._on_window_ready, launcher_module.Qt.QueuedConnection)
    launcher._on_window_ready()
    preloader.close.assert_called_once_with()
    assert launcher._preloader is None


def test_preloader_close_exception_is_swallowed(launcher_module):
    launcher = launcher_module.Launcher()
    preloader = MagicMock()
    preloader.close.side_effect = RuntimeError("closed")
    launcher._preloader = preloader
    launcher._on_window_ready()
    assert launcher._preloader is None


_REGISTRATIONS = [
    ("add_plugin", "BasePlugin", "add_plugin"),
    ("add_llm", "BaseLLM", "add_llm"),
    ("add_vector_store", "BaseStore", "add_vector_store"),
    ("add_loader", "BaseLoader", "add_loader"),
    ("add_audio_input", "BaseAudioInput", "add_audio_input"),
    ("add_audio_output", "BaseAudioOutput", "add_audio_output"),
    ("add_web", "BaseWeb", "add_web"),
    ("add_tool", "BaseTool", "add_tool"),
    ("add_agent", "BaseAgent", "add_agent"),
]


@pytest.mark.parametrize(("method_name", "base_name", "window_method"), _REGISTRATIONS)
def test_registration_methods_accept_expected_type(launcher_module, method_name, base_name, window_method):
    base = getattr(launcher_module, base_name)
    item = base()
    item.id = "custom"
    launcher = launcher_module.Launcher()
    launcher.window = MagicMock()
    launcher.debug = True

    getattr(launcher, method_name)(item)

    getattr(launcher.window, window_method).assert_called_once_with(item)


@pytest.mark.parametrize(("method_name", "base_name", "window_method"), _REGISTRATIONS)
def test_registration_methods_reject_wrong_type(launcher_module, method_name, base_name, window_method):
    launcher = launcher_module.Launcher()
    launcher.window = MagicMock()

    with pytest.raises(TypeError):
        getattr(launcher, method_name)(object())

    getattr(launcher.window, window_method).assert_not_called()


def test_run_executes_window_lifecycle_without_real_qt_or_process_exit(launcher_module):
    launcher = launcher_module.Launcher()
    launcher.window = MagicMock()
    launcher.app = MagicMock()
    launcher.app.exec.return_value = 7

    geometry = MagicMock()
    geometry.width.return_value = 1280
    geometry.height.return_value = 900
    launcher.window.screen.return_value.availableGeometry.return_value = geometry

    screen_geometry = MagicMock()
    screen_geometry.topLeft.return_value = "top-left"
    launcher_module.QScreen = SimpleNamespace(availableGeometry=MagicMock(return_value=screen_geometry))
    launcher_module.QApplication = SimpleNamespace(primaryScreen=MagicMock(return_value="primary"))
    signal_mock = MagicMock()
    exit_mock = MagicMock()
    launcher_module.signal = SimpleNamespace(
        SIGTERM=signal_module.SIGTERM,
        SIGINT=signal_module.SIGINT,
        signal=signal_mock,
    )
    launcher_module.sys = SimpleNamespace(exit=exit_mock)

    launcher.run()

    launcher.window.setup.assert_called_once_with()
    launcher.window.resize.assert_called_once_with(1180, 800)
    launcher.window.show.assert_called_once_with()
    launcher.window.move.assert_called_once_with("top-left")
    launcher.window.post_setup.assert_called_once_with()
    launcher.app.setWindowIcon.assert_called_once_with(launcher.window.ui.get_app_icon.return_value)
    launcher.window.ui.tray.setup.assert_called_once_with(launcher.app)
    launcher.window.controller.after_setup.assert_called_once_with()
    launcher.window.dispatch.assert_called_once()
    launcher.window.setup_global_shortcuts.assert_called_once_with()
    signal_mock.assert_any_call(signal_module.SIGTERM, launcher.handle_signal)
    signal_mock.assert_any_call(signal_module.SIGINT, launcher.handle_signal)
    exit_mock.assert_called_once_with(7)
