#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 19:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.installer import Installer


def test_install(mock_window):
    """Test install"""
    installer = Installer(mock_window)
    path = MagicMock()
    Path = MagicMock(return_value=path)
    mock_window.core.config.install = MagicMock()
    mock_window.core.models.install = MagicMock()
    mock_window.core.presets.install = MagicMock()
    mock_window.core.history.install = MagicMock()
    mock_window.core.ctx.install = MagicMock()
    mock_window.core.notepad.install = MagicMock()
    mock_window.core.attachments.install = MagicMock()
    mock_window.core.assistants.install = MagicMock()
    mock_window.core.image.install = MagicMock()
    mock_window.core.filesystem.install = MagicMock()
    mock_window.core.camera.install = MagicMock()

    with patch('pygpt_net.core.installer.Path', Path):
        installer.install()
        mock_window.core.config.install.assert_called_once()
        mock_window.core.models.install.assert_called_once()
        mock_window.core.presets.install.assert_called_once()
        mock_window.core.history.install.assert_called_once()
        mock_window.core.ctx.install.assert_called_once()
        mock_window.core.notepad.install.assert_called_once()
        mock_window.core.attachments.install.assert_called_once()
        mock_window.core.assistants.install.assert_called_once()
        mock_window.core.image.install.assert_called_once()
        mock_window.core.filesystem.install.assert_called_once()
        mock_window.core.camera.install.assert_called_once()
        path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
