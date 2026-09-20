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
from pygpt_net.core.camera import Camera


def test_install(mock_window, monkeypatch):
    """Test install"""
    camera = Camera(mock_window)
    exists_mock = MagicMock(return_value=False)
    makedirs_mock = MagicMock()
    monkeypatch.setattr(os.path, "exists", exists_mock)
    monkeypatch.setattr(os, "makedirs", makedirs_mock)
    camera.install()
    makedirs_mock.assert_called()
