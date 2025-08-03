#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from pygpt_net.core.types import MODE_AGENT
from pygpt_net.controller.agent.common import Common

@pytest.fixture
def mock_window():
    # Create a dummy window with all necessary attributes
    window = MagicMock()
    window.core = MagicMock()
    window.core.config = MagicMock()
    window.core.plugins = MagicMock()
    window.ui = MagicMock()
    window.ui.dialogs = MagicMock()
    # Create a dummy node for status display
    status_agent = MagicMock()
    window.ui.nodes = {'status.agent': status_agent}
    window.controller = MagicMock()
    window.controller.plugins = MagicMock()
    legacy = MagicMock()
    window.controller.agent = MagicMock()
    window.controller.agent.legacy = legacy
    return window

def test_enable_auto_stop(mock_window):
    common = Common(window=mock_window)
    common.enable_auto_stop()
    mock_window.core.config.set.assert_called_once_with('agent.auto_stop', True)
    mock_window.core.config.save.assert_called_once()

def test_disable_auto_stop(mock_window):
    common = Common(window=mock_window)
    common.disable_auto_stop()
    mock_window.core.config.set.assert_called_once_with('agent.auto_stop', False)
    mock_window.core.config.save.assert_called_once()

def test_toggle_auto_stop_true(mock_window):
    common = Common(window=mock_window)
    common.toggle_auto_stop(True)
    mock_window.core.config.set.assert_called_once_with('agent.auto_stop', True)
    mock_window.core.config.save.assert_called_once()

def test_toggle_auto_stop_false(mock_window):
    common = Common(window=mock_window)
    common.toggle_auto_stop(False)
    mock_window.core.config.set.assert_called_once_with('agent.auto_stop', False)
    mock_window.core.config.save.assert_called_once()

def test_enable_continue(mock_window):
    common = Common(window=mock_window)
    common.enable_continue()
    mock_window.core.config.set.assert_called_once_with('agent.continue.always', True)
    mock_window.core.config.save.assert_called_once()

def test_disable_continue(mock_window):
    common = Common(window=mock_window)
    common.disable_continue()
    mock_window.core.config.set.assert_called_once_with('agent.continue.always', False)
    mock_window.core.config.save.assert_called_once()

def test_toggle_continue_true(mock_window):
    common = Common(window=mock_window)
    common.toggle_continue(True)
    mock_window.core.config.set.assert_called_once_with('agent.continue.always', True)
    mock_window.core.config.save.assert_called_once()

def test_toggle_continue_false(mock_window):
    common = Common(window=mock_window)
    common.toggle_continue(False)
    mock_window.core.config.set.assert_called_once_with('agent.continue.always', False)
    mock_window.core.config.save.assert_called_once()

def test_is_infinity_loop_mode_agent(mock_window):
    common = Common(window=mock_window)
    # legacy: iterations equals 0
    mock_window.core.config.get.return_value = 0
    mock_window.controller.plugins.is_enabled.return_value = False
    assert common.is_infinity_loop(MODE_AGENT) is True

def test_is_infinity_loop_plugin(mock_window):
    common = Common(window=mock_window)
    # core iterations is not 0 but plugin option is 0
    mock_window.core.config.get.return_value = 5
    mock_window.controller.plugins.is_enabled.return_value = True
    mock_window.core.plugins.get_option.return_value = 0
    assert common.is_infinity_loop("other_mode") is True

def test_is_infinity_loop_false(mock_window):
    common = Common(window=mock_window)
    mock_window.core.config.get.return_value = 5
    mock_window.controller.plugins.is_enabled.return_value = False
    mock_window.core.plugins.get_option.return_value = 5
    assert common.is_infinity_loop("other_mode") is False

def test_display_infinity_loop_confirm(mock_window, monkeypatch):
    common = Common(window=mock_window)
    fake_trans = "translated"
    monkeypatch.setattr("pygpt_net.controller.agent.common.trans", lambda text: fake_trans)
    common.display_infinity_loop_confirm()
    mock_window.ui.dialogs.confirm.assert_called_once_with(
        type="agent.infinity.run",
        id=0,
        msg=fake_trans,
    )

def test_show_status(mock_window):
    common = Common(window=mock_window)
    common.show_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once_with(True)

def test_hide_status(mock_window):
    common = Common(window=mock_window)
    common.hide_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once_with(False)

def test_toggle_status_mode_agent(mock_window):
    # If mode is agent, status should be shown.
    mock_window.core.config.get.return_value = MODE_AGENT
    mock_window.controller.agent.legacy.is_inline.return_value = False
    common = Common(window=mock_window)
    common.toggle_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once_with(True)

def test_toggle_status_inline(mock_window):
    # If legacy.is_inline returns True, status is shown regardless of mode.
    mock_window.core.config.get.return_value = "other_mode"
    mock_window.controller.agent.legacy.is_inline.return_value = True
    common = Common(window=mock_window)
    common.toggle_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once_with(True)

def test_toggle_status_hide(mock_window):
    # If mode is not agent and legacy.is_inline is False, status is hidden.
    mock_window.core.config.get.return_value = "other_mode"
    mock_window.controller.agent.legacy.is_inline.return_value = False
    common = Common(window=mock_window)
    common.toggle_status()
    mock_window.ui.nodes['status.agent'].setVisible.assert_called_once_with(False)

def test_enable_loop(mock_window):
    common = Common(window=mock_window)
    common.enable_loop()
    mock_window.core.config.set.assert_called_once_with('agent.llama.loop.enabled', True)
    mock_window.core.config.save.assert_called_once()

def test_disable_loop(mock_window):
    common = Common(window=mock_window)
    common.disable_loop()
    mock_window.core.config.set.assert_called_once_with('agent.llama.loop.enabled', False)
    mock_window.core.config.save.assert_called_once()

def test_toggle_loop_true(mock_window):
    common = Common(window=mock_window)
    common.toggle_loop(True)
    mock_window.core.config.set.assert_called_once_with('agent.llama.loop.enabled', True)
    mock_window.core.config.save.assert_called_once()

def test_toggle_loop_false(mock_window):
    common = Common(window=mock_window)
    common.toggle_loop(False)
    mock_window.core.config.set.assert_called_once_with('agent.llama.loop.enabled', False)
    mock_window.core.config.save.assert_called_once()
