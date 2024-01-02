#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 02:00:00                  #
# ================================================== #

import os

import pytest
from unittest.mock import MagicMock, mock_open, patch

from PySide6.QtWidgets import QMainWindow

from pygpt_net.config import Config
from pygpt_net.controller.chat.files import Files


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.config = Config(window)  # real config object
    window.core.config.initialized = True  # prevent initializing config
    window.core.config.init = MagicMock()  # mock init method to prevent init
    window.core.config.load = MagicMock()  # mock load method to prevent loading
    window.core.config.save = MagicMock()  # mock save method to prevent saving
    window.controller = MagicMock()
    window.ui = MagicMock()
    return window


def test_upload(mock_window):
    """Test handle files"""
    files = Files(mock_window)
    attachments = []
    json_list = {
        "file1": {"name": "file1", "path": "/home/user/file1"},
        "file2": {"name": "file2", "path": "/home/user/file2"}
    }
    mock_window.core.attachments.get_all = MagicMock(return_value=attachments)
    mock_window.controller.assistant.files.count_upload = MagicMock(return_value=2)
    mock_window.controller.assistant.files.upload = MagicMock(return_value=2)  # 2 uploaded
    mock_window.core.attachments.make_json_list = MagicMock(return_value=json_list)

    assert files.upload('assistant') == json_list
