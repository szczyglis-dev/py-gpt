#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 16:00:00                  #
# ================================================== #
# 
import os
from unittest.mock import MagicMock, call, patch

import PySide6

from tests.mocks import mock_window
from pygpt_net.controller import Camera


def test_setup(mock_window):
    """Test setup"""
    camera = Camera(mock_window)
    camera.start = MagicMock()
    camera.is_capture = True
    camera.thread_started = False
    camera.setup()
    camera.start.assert_called_once()


def test_setup_ui(mock_window):
    """Test setup ui"""
    camera = Camera(mock_window)
    mock_window.core.config.data['vision.capture.enabled'] = True
    mock_window.core.config.data['vision.capture.auto'] = True
    mock_window.ui.nodes['vision.capture.enable'].setChecked = MagicMock()
    mock_window.ui.nodes['vision.capture.auto'].setChecked = MagicMock()
    mock_window.ui.nodes['video.preview'].label.setText = MagicMock()
    camera.setup_ui()
    assert camera.is_capture is True
    assert camera.auto is True
    mock_window.ui.nodes['vision.capture.enable'].setChecked.assert_called()
    mock_window.ui.nodes['vision.capture.auto'].setChecked.assert_called()
    mock_window.ui.nodes['video.preview'].label.setText.assert_called()
    assert camera.auto is True


def test_start(mock_window):
    """Test start"""
    camera = Camera(mock_window)
    camera.window.threadpool.start = MagicMock()
    camera.start()
    camera.window.threadpool.start.assert_called_once()


def test_stop_capture(mock_window):
    """Test stop capture"""
    camera = Camera(mock_window)
    camera.stop = False
    camera.thread_started = True
    camera.stop_capture()
    assert camera.stop is True


def test_handle_error(mock_window):
    """Test handle error"""
    camera = Camera(mock_window)
    camera.window.core.debug.log = MagicMock()
    camera.window.ui.dialogs.alert = MagicMock()
    camera.handle_error("test")
    camera.window.core.debug.log.assert_called_once()
    camera.window.ui.dialogs.alert.assert_called_once()


def test_handle_capture(mock_window):
    """Test handle capture"""
    camera = Camera(mock_window)
    camera.update = MagicMock()
    camera.handle_capture("test")
    camera.update.assert_called_once()


def test_handle_stop(mock_window):
    """Test handle stop"""
    camera = Camera(mock_window)
    camera.thread_started = True
    camera.hide_camera = MagicMock()
    camera.handle_stop()
    camera.hide_camera.assert_called_once()
    assert camera.thread_started is False


def test_manual_capture(mock_window):
    """Test manual capture"""
    camera = Camera(mock_window)
    camera.capture_frame = MagicMock()
    camera.is_auto = MagicMock(return_value=False)
    camera.manual_capture()
    camera.capture_frame.assert_called_once_with(True)
    camera.is_auto.assert_called_once()


def test_show_camera(mock_window):
    """Test show camera"""
    camera = Camera(mock_window)
    camera.is_capture = True
    camera.window.ui.nodes['video.preview'].setVisible = MagicMock()
    camera.show_camera()
    camera.window.ui.nodes['video.preview'].setVisible.assert_called_once()


def test_hide_camera(mock_window):
    """Test hide camera"""
    camera = Camera(mock_window)
    camera.stop_capture = MagicMock()
    camera.window.ui.nodes['video.preview'].setVisible = MagicMock()
    camera.hide_camera()
    camera.stop_capture.assert_called_once()
    camera.window.ui.nodes['video.preview'].setVisible.assert_called_once()


def test_enable_capture(mock_window):
    """Test enable capture"""
    camera = Camera(mock_window)
    camera.window.core.config.set = MagicMock()
    camera.window.ui.nodes['video.preview'].setVisible = MagicMock()
    camera.window.controller.plugins.is_type_enabled = MagicMock(return_value=True)
    camera.enable_capture()
    camera.window.core.config.set.assert_called_once()
    camera.window.ui.nodes['video.preview'].setVisible.assert_called_once()


def test_disable_capture(mock_window):
    """Test disable capture"""
    camera = Camera(mock_window)
    camera.window.core.config.set = MagicMock()
    camera.window.ui.nodes['video.preview'].setVisible = MagicMock()
    camera.blank_screen = MagicMock()
    camera.disable_capture()
    camera.window.core.config.set.assert_called_once()
    camera.window.ui.nodes['video.preview'].setVisible.assert_called_once()


def test_toggle(mock_window):
    """Test toggle"""
    camera = Camera(mock_window)
    camera.enable_capture = MagicMock()
    camera.disable_capture = MagicMock()
    camera.toggle(True)
    camera.enable_capture.assert_called_once()
    camera.toggle(False)
    camera.disable_capture.assert_called_once()


def test_enable_auto(mock_window):
    """Test enable auto"""
    camera = Camera(mock_window)
    mock_window.core.config.data['mode'] = 'vision'
    mock_window.core.config.data['vision.capture.auto'] = False
    mock_window.core.config.data['vision.capture.enabled'] = False
    camera.enable_capture = MagicMock()
    mock_window.ui.nodes['video.preview'].label.setText = MagicMock()
    camera.enable_auto()
    camera.enable_capture.assert_called_once()
    mock_window.ui.nodes['video.preview'].label.setText.assert_called()
    assert camera.auto is True


def test_disable_auto(mock_window):
    """Test disable auto"""
    camera = Camera(mock_window)
    mock_window.core.config.data['mode'] = 'vision'
    camera.disable_capture = MagicMock()
    mock_window.ui.nodes['video.preview'].label.setText = MagicMock()
    camera.disable_auto()
    mock_window.ui.nodes['video.preview'].label.setText.assert_called()
    assert camera.auto is False


def test_toggle_auto(mock_window):
    """Test toggle auto"""
    camera = Camera(mock_window)
    camera.enable_auto = MagicMock()
    camera.disable_auto = MagicMock()
    camera.toggle_auto(True)
    camera.enable_auto.assert_called_once()
    camera.toggle_auto(False)
    camera.disable_auto.assert_called_once()


def test_is_enabled(mock_window):
    """Test is enabled"""
    camera = Camera(mock_window)
    camera.is_capture = True
    assert camera.is_enabled() is True
    camera.is_capture = False
    assert camera.is_enabled() is False


def test_is_auto(mock_window):
    """Test is auto"""
    camera = Camera(mock_window)
    camera.auto = True
    assert camera.is_auto() is True
    camera.auto = False
    assert camera.is_auto() is False


def test_blank_screen(mock_window):
    """Test blank screen"""
    camera = Camera(mock_window)
    mock_window.ui.nodes['video.preview'].video = MagicMock()

    with patch('PySide6.QtGui.QPixmap.fromImage') as mock_pixmap:
        camera.blank_screen()
        mock_pixmap.assert_called_once()
        mock_window.ui.nodes['video.preview'].video.setPixmap.assert_called_once()
