#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


APP_CORE_PATH = Path(__file__).resolve().parents[1] / "src" / "pygpt_net" / "app_core.py"

_COMPONENTS = {
    "access": ("pygpt_net.core.access", "Access"),
    "agents": ("pygpt_net.core.agents", "Agents"),
    "agents_v2": ("pygpt_net.core.agents_v2", "AgentsV2"),
    "api": ("pygpt_net.provider.api", "Api"),
    "assistants": ("pygpt_net.core.assistants", "Assistants"),
    "attachments": ("pygpt_net.core.attachments", "Attachments"),
    "audio": ("pygpt_net.core.audio", "Audio"),
    "bridge": ("pygpt_net.core.bridge", "Bridge"),
    "banners": ("pygpt_net.core.banners", "Banners"),
    "calendar": ("pygpt_net.core.calendar", "Calendar"),
    "camera": ("pygpt_net.core.camera", "Camera"),
    "command": ("pygpt_net.core.command", "Command"),
    "config": ("pygpt_net.config", "Config"),
    "ctx": ("pygpt_net.core.ctx", "Ctx"),
    "db": ("pygpt_net.core.db", "Database"),
    "debug": ("pygpt_net.core.debug", "Debug"),
    "dispatcher": ("pygpt_net.core.dispatcher", "Dispatcher"),
    "experts": ("pygpt_net.core.experts", "Experts"),
    "filesystem": ("pygpt_net.core.filesystem", "Filesystem"),
    "idx": ("pygpt_net.core.idx", "Idx"),
    "image": ("pygpt_net.core.image", "Image"),
    "installer": ("pygpt_net.core.installer", "Installer"),
    "llm": ("pygpt_net.core.llm", "LLM"),
    "models": ("pygpt_net.core.models", "Models"),
    "modes": ("pygpt_net.core.modes", "Modes"),
    "notepad": ("pygpt_net.core.notepad", "Notepad"),
    "platforms": ("pygpt_net.core.platforms", "Platforms"),
    "plugins": ("pygpt_net.core.plugins", "Plugins"),
    "presets": ("pygpt_net.core.presets", "Presets"),
    "prompt": ("pygpt_net.core.prompt", "Prompt"),
    "remote_store": ("pygpt_net.core.remote_store", "RemoteStore"),
    "security": ("pygpt_net.core.security", "Security"),
    "settings": ("pygpt_net.core.settings", "Settings"),
    "tabs": ("pygpt_net.core.tabs", "Tabs"),
    "text": ("pygpt_net.core.text", "Text"),
    "tokens": ("pygpt_net.core.tokens", "Tokens"),
    "updater": ("pygpt_net.core.updater", "Updater"),
    "video": ("pygpt_net.core.video", "Video"),
    "vision": ("pygpt_net.core.vision", "Vision"),
    "web": ("pygpt_net.core.web", "Web"),
}


def _load_isolated_module():
    fake_modules = {}
    for _, (module_name, class_name) in _COMPONENTS.items():
        module = fake_modules.setdefault(module_name, ModuleType(module_name))
        setattr(module, class_name, type(class_name, (), {}))

    spec = importlib.util.spec_from_file_location("pygpt_net._test_app_core", APP_CORE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, fake_modules):
        spec.loader.exec_module(module)
    return module


@pytest.fixture
def app_core_module():
    return _load_isolated_module()


def test_core_initializes_all_components_with_window(app_core_module, monkeypatch):
    window = object()
    factories = {}
    sentinels = {}

    for attr, (_, class_name) in _COMPONENTS.items():
        sentinel = object()
        factory = MagicMock(return_value=sentinel)
        factories[class_name] = factory
        sentinels[attr] = sentinel
        monkeypatch.setattr(app_core_module, class_name, factory)

    core = app_core_module.Core(window)

    assert core.window is window
    for attr, (_, class_name) in _COMPONENTS.items():
        assert getattr(core, attr) is sentinels[attr]
        factories[class_name].assert_called_once_with(window)


def _bare_core(app_core_module):
    core = object.__new__(app_core_module.Core)
    core.config = MagicMock()
    core.platforms = MagicMock()
    core.updater = MagicMock()
    core.db = MagicMock()
    core.debug = MagicMock()
    core.llm = MagicMock()
    core.prompt = SimpleNamespace(custom=MagicMock())
    return core


def test_core_lifecycle_delegates_to_components(app_core_module):
    core = _bare_core(app_core_module)

    core.init()
    core.patch()
    core.post_setup()
    core.reload()

    core.config.init.assert_called_once_with(all=True)
    core.platforms.init.assert_called_once_with()
    assert core.updater.patch.call_count == 2
    core.db.reload.assert_called_once_with()
    core.debug.update_logger_path.assert_called_once_with()
    assert core.config.setup_env.call_count == 2
    core.llm.sync_custom.assert_called_once_with(force=True)
    core.prompt.custom.reload.assert_called_once_with()
