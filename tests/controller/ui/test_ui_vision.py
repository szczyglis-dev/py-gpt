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
from pygpt_net.controller.ui.vision import Vision


def test_update_vision_vision_mode(mock_window):
    """Test update vision: vision mode"""
    vision = Vision(mock_window)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=True)
    mock_window.controller.chat.vision.allowed_modes = ["chat", "completion"]
    mock_window.core.config.data['mode'] = 'vision'
    mock_window.controller.camera.setup = MagicMock()
    mock_window.controller.camera.show_camera = MagicMock()
    mock_window.controller.camera.hide_camera = MagicMock()
    mock_window.controller.chat.vision.show_inline = MagicMock()
    mock_window.controller.chat.vision.hide_inline = MagicMock()
    vision.update()
    mock_window.controller.camera.setup.assert_called()
    mock_window.controller.camera.show_camera.assert_called()
    mock_window.controller.camera.hide_camera.assert_not_called()
    mock_window.controller.chat.vision.show_inline.assert_not_called()
    mock_window.controller.chat.vision.hide_inline.assert_not_called()


def test_update_vision_inline(mock_window):
    """Test update vision: inline mode"""
    vision = Vision(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=True)
    mock_window.controller.chat.vision.allowed_modes = ["chat", "completion"]
    mock_window.controller.camera.setup = MagicMock()
    mock_window.controller.camera.show_camera = MagicMock()
    mock_window.controller.camera.hide_camera = MagicMock()
    mock_window.controller.chat.vision.show_inline = MagicMock()
    mock_window.controller.chat.vision.hide_inline = MagicMock()
    vision.update()
    mock_window.controller.camera.setup.assert_called()
    mock_window.controller.camera.show_camera.assert_called()
    mock_window.controller.camera.hide_camera.assert_not_called()
    mock_window.controller.chat.vision.show_inline.assert_not_called()
    mock_window.controller.chat.vision.hide_inline.assert_not_called()


def test_update_vision_no_vision(mock_window):
    """Test update vision: no vision"""
    vision = Vision(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    mock_window.controller.painter.is_active = MagicMock(return_value=False)
    mock_window.controller.camera.setup = MagicMock()
    mock_window.controller.camera.show_camera = MagicMock()
    mock_window.controller.camera.hide_camera = MagicMock()
    mock_window.controller.chat.vision.show_inline = MagicMock()
    mock_window.controller.chat.vision.hide_inline = MagicMock()
    vision.update()
    mock_window.controller.camera.setup.assert_not_called()
    mock_window.controller.camera.show_camera.assert_not_called()
    mock_window.controller.camera.hide_camera.assert_called()
    mock_window.controller.chat.vision.show_inline.assert_not_called()
    mock_window.controller.chat.vision.hide_inline.assert_called()
