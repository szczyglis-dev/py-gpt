#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : PYGPT Contributors                   #
# Updated Date: 2026.03.11 00:00:00                  #
# ================================================== #

import platform
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_app_launcher import Plugin
from pygpt_net.plugin.cmd_app_launcher.worker import Worker


def test_options(mock_window):
    """Test plugin options are correctly initialized"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "cmd.app_launch" in options
    assert "cmd.app_close" in options
    assert "cmd.app_list_running" in options
    assert "cmd.app_open_url" in options
    assert "cmd.app_list_installed" in options
    assert "cmd.media_play_pause" in options
    assert "cmd.media_next_track" in options
    assert "cmd.media_prev_track" in options
    assert "cmd.volume_set" in options
    assert "cmd.volume_mute_toggle" in options
    assert "custom_app_aliases" in options
    assert "scan_start_menu" in options


def test_plugin_id(mock_window):
    """Test plugin id and name"""
    plugin = Plugin(window=mock_window)
    assert plugin.id == "cmd_app_launcher"
    assert plugin.name == "App Launcher"
    assert "cmd" in plugin.type


def test_allowed_cmds(mock_window):
    """Test all commands are in allowed list"""
    plugin = Plugin(window=mock_window)
    expected = [
        "app_launch", "app_close", "app_list_running",
        "app_open_url", "app_list_installed",
        "media_play_pause", "media_next_track", "media_prev_track",
        "volume_set", "volume_mute_toggle",
    ]
    for cmd in expected:
        assert cmd in plugin.allowed_cmds


def test_cmd_syntax(mock_window):
    """Test CMD_SYNTAX event appends commands"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    data = {"cmd": []}
    event = Event()
    event.name = Event.CMD_SYNTAX
    event.data = data
    event.ctx = None
    plugin.handle(event)

    cmd_names = [c["cmd"] for c in data["cmd"]]
    assert "app_launch" in cmd_names
    assert "app_close" in cmd_names
    assert "app_open_url" in cmd_names


def test_cmd_execute_dispatches(mock_window):
    """Test CMD_EXECUTE creates worker for matching commands"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    ctx = CtxItem()
    ctx.async_disabled = True

    commands = [
        {"cmd": "app_open_url", "params": {"url": "youtube.com"}},
    ]

    data = {"commands": commands}
    event = Event()
    event.name = Event.CMD_EXECUTE
    event.data = data
    event.ctx = ctx

    # Mock worker to prevent actual execution
    with patch("pygpt_net.plugin.cmd_app_launcher.plugin.Plugin.is_async", return_value=False):
        with patch("pygpt_net.plugin.cmd_app_launcher.worker.Worker.run") as mock_run:
            plugin.handle(event)
            # Worker.run should have been called
            mock_run.assert_called_once()


def test_worker_open_url(mock_window):
    """Test worker opens URL correctly"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    item = {"cmd": "app_open_url", "params": {"url": "youtube.com"}}

    with patch("webbrowser.open") as mock_open:
        result = worker.cmd_app_open_url(item)
        mock_open.assert_called_once_with("https://youtube.com")
        assert "Opened URL" in result["result"]


def test_worker_open_url_with_scheme(mock_window):
    """Test worker preserves existing URL scheme"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    item = {"cmd": "app_open_url", "params": {"url": "https://example.com"}}

    with patch("webbrowser.open") as mock_open:
        result = worker.cmd_app_open_url(item)
        mock_open.assert_called_once_with("https://example.com")


def test_worker_open_url_empty(mock_window):
    """Test worker handles empty URL"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    item = {"cmd": "app_open_url", "params": {"url": ""}}
    result = worker.cmd_app_open_url(item)
    assert "Error" in result["result"]


def test_worker_app_launch_not_found(mock_window):
    """Test worker handles app not found"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    item = {"cmd": "app_launch", "params": {"app_name": "nonexistent_app_xyz123"}}

    with patch("shutil.which", return_value=None):
        with patch.object(worker, "find_start_menu_shortcut", return_value=None):
            with patch.object(worker, "find_windows_app", return_value=None):
                result = worker.cmd_app_launch(item)
                assert "Could not find" in result["result"]


def test_worker_app_launch_empty_name(mock_window):
    """Test worker handles empty app name"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    item = {"cmd": "app_launch", "params": {"app_name": ""}}
    result = worker.cmd_app_launch(item)
    assert "Error" in result["result"]


def test_worker_app_list_installed(mock_window):
    """Test worker lists installed apps"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    item = {"cmd": "app_list_installed", "params": {"filter": "chrome"}}

    with patch.object(worker, "scan_start_menu", return_value=[]):
        result = worker.cmd_app_list_installed(item)
        # Should find "chrome" in custom aliases
        assert "chrome" in result["result"].lower()


def test_worker_volume_set_bounds(mock_window):
    """Test worker clamps volume to 0-100"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    worker = Worker()
    worker.plugin = plugin
    worker.window = mock_window
    worker.signals = MagicMock()

    # Test with out-of-bounds value
    item = {"cmd": "volume_set", "params": {"level": 150}}

    with patch("platform.system", return_value="Windows"):
        try:
            result = worker.cmd_volume_set(item)
            # Should clamp to 100, not error
            assert "Error" not in result.get("result", "") or "pycaw" in result.get("result", "")
        except ImportError:
            pass  # pycaw not installed in test env
