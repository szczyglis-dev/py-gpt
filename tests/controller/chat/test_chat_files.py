#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.chat.files import Files


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
