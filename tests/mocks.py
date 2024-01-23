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

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QMainWindow
from pygpt_net.config import Config


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.config = Config(window)  # real config object
    window.core.config.initialized = True  # prevent initializing config
    window.core.config.init = MagicMock()  # mock init method to prevent init
    window.core.config.load = MagicMock()  # mock load method to prevent loading
    window.core.config.save = MagicMock()  # mock save method to prevent saving
    window.core.config.get_lang = MagicMock(return_value='en')
    window.controller = MagicMock()
    window.ui = MagicMock()
    window.threadpool = MagicMock()
    return window


@pytest.fixture
def mock_window_conf():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.models = MagicMock()
    window.core.config = MagicMock(spec=Config)  # mock config object
    window.core.config.path = 'test_path'
    window.core.config.get_lang = MagicMock(return_value='en')
    return window
