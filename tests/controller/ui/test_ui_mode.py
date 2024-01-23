#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, call

from tests.mocks import mock_window
from pygpt_net.controller.ui.mode import Mode


def test_update(mock_window):
    """Test update"""
    mode = Mode(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.ui.nodes['presets.widget'].setVisible = MagicMock()
    mock_window.ui.nodes['preset.ai_name'].setDisabled = MagicMock()
    mock_window.ui.nodes['preset.user_name'].setDisabled = MagicMock()
    mock_window.ui.nodes['preset.clear'].setVisible = MagicMock()
    mock_window.ui.nodes['preset.use'].setVisible = MagicMock()
    mock_window.ui.nodes['assistants.widget'].setVisible = MagicMock()
    mock_window.ui.nodes['dalle.options'].setVisible = MagicMock()
    mock_window.ui.nodes['vision.capture.options'].setVisible = MagicMock()
    mock_window.ui.nodes['attachments.capture_clear'].setVisible = MagicMock()
    mock_window.ui.tabs['input'].setTabVisible = MagicMock()
    mock_window.ui.tabs['input'].setTabVisible = MagicMock()
    mock_window.ui.tabs['input'].setTabVisible = MagicMock()
    mock_window.ui.nodes['input.stream'].setVisible = MagicMock()
    mock_window.core.dispatcher.dispatch = MagicMock()
    mock_window.core.dispatcher.dispatch.return_value = MagicMock()
    mock_window.core.dispatcher.dispatch.return_value.data = {'value': True}
    mode.update()
    mock_window.ui.nodes['presets.widget'].setVisible.assert_called()
    mock_window.ui.nodes['preset.clear'].setVisible.assert_called()
    mock_window.ui.nodes['preset.use'].setVisible.assert_called()
    mock_window.ui.nodes['assistants.widget'].setVisible.assert_called()
    mock_window.ui.nodes['dalle.options'].setVisible.assert_called()
    mock_window.ui.nodes['vision.capture.options'].setVisible.assert_called()
