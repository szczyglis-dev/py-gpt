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

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.painter.capture import Capture


def test_camera(mock_window):
    """Test camera"""
    mock_window.controller.camera.is_enabled = MagicMock(return_value=True)
    mock_window.controller.camera.enable_capture = MagicMock()
    mock_window.controller.camera.setup_ui = MagicMock()
    frame = MagicMock()
    frame.shape = (100, 100, 3)
    frame.data = b'1111'
    mock_window.controller.camera.get_current_frame = MagicMock(return_value=frame)

    capture = Capture(mock_window)
    mock_window.ui.painter.set_image = MagicMock()
    capture.camera()
    mock_window.ui.painter.set_image.assert_called_once()


def test_screenshot(mock_window):
    """Test screenshot"""
    mock_window.controller.chat.vision.switch_to_vision = MagicMock()
    mock_window.controller.attachment.is_capture_clear = MagicMock(return_value=True)
    mock_window.controller.attachment.clear = MagicMock()
    mock_window.statusChanged = MagicMock()
    mock_window.app = MagicMock()
    mock_window.app.primaryScreen = MagicMock(return_value=MagicMock())
    capture = Capture(mock_window)
    capture.attach = MagicMock()
    mock_window.controller.painter.open = MagicMock()
    capture.screenshot()
    # mock_window.controller.painter.open.assert_called_once()
    mock_window.controller.attachment.clear.assert_called_once()


def test_use(mock_window):
    """Test use"""
    mock_window.controller.chat.vision.switch_to_vision = MagicMock()
    mock_window.controller.attachment.is_capture_clear = MagicMock(return_value=True)
    mock_window.controller.attachment.clear = MagicMock()
    mock_window.statusChanged = MagicMock()
    capture = Capture(mock_window)
    capture.attach = MagicMock()
    mock_window.ui.painter.image.save = MagicMock()
    capture.use()
    mock_window.ui.painter.image.save.assert_called_once()
    mock_window.controller.attachment.clear.assert_called_once()


def test_attach(mock_window):
    """Test attach"""
    mock_window.core.attachments.new = MagicMock()
    mock_window.core.attachments.save = MagicMock()
    mock_window.controller.attachment.update = MagicMock()
    capture = Capture(mock_window)
    capture.attach("Capture from ...", "test.png")
    mock_window.core.attachments.new.assert_called_once()
    mock_window.core.attachments.save.assert_called_once()
    mock_window.controller.attachment.update.assert_called_once()



def test_save_current_runtime_image_exports_composited_painter_without_persistent_attachment(mock_window, tmp_path):
    """Runtime Painter capture saves the logical canvas but does not touch chat attachments."""
    capture = Capture(mock_window)
    painter = MagicMock()
    painter.image.isNull.return_value = False
    painter.image.save.return_value = True
    mock_window.ui.painter = painter
    runtime_root = tmp_path / "runtime_artifacts"
    mock_window.core.filesystem.get_runtime_artifacts_dir.return_value = str(runtime_root)

    path = capture.save_current_runtime_image()

    assert path is not None
    assert path.startswith(str(runtime_root))
    assert path.endswith('.png')
    assert 'painter-user-' in path
    mock_window.core.filesystem.get_runtime_artifacts_dir.assert_called_once_with(create=True)
    painter._ensure_composited_image.assert_called_once_with()
    painter.image.save.assert_called_once_with(path, "PNG")
    mock_window.core.attachments.new.assert_not_called()
    mock_window.core.attachments.save.assert_not_called()
