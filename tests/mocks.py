#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

import os
import shutil

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QMainWindow
from pygpt_net.config import Config


@pytest.fixture
def mock_window(tmp_path, monkeypatch):
    # Keep tests fully isolated from the developer/runner user profile.
    # Config itself stays real, but its base workdir points to pytest's temp dir.
    test_workdir = tmp_path / "pygpt-net"
    monkeypatch.setattr(
        Config,
        "get_base_workdir",
        staticmethod(lambda: str(test_workdir)),
    )

    # Some provider tests patch ``os.path.exists`` globally.  If the base
    # workdir does not already exist, that patch also changes the behaviour of
    # ``os.makedirs`` and can make creation of nested runtime directories fail.
    # Create the isolated workdir before such patches are active.
    test_workdir.mkdir(parents=True, exist_ok=True)

    window = MagicMock(spec=QMainWindow)
    window.STATE_IDLE = 'idle'
    window.STATE_BUSY = 'busy'
    window.STATE_ERROR = 'error'
    window.state = MagicMock()
    window.stateChanged = MagicMock()
    window.idx_logger_message = MagicMock()
    window.core = MagicMock()
    window.core.config = Config(window)  # real config object

    # Reproduce the small, already-installed part of a normal user workdir that
    # provider unit tests expect.  Keep it local to tmp_path so tests neither
    # read nor modify the developer's real ~/.config/pygpt-net directory.
    app_config_dir = os.path.join(window.core.config.get_app_path(), "data", "config")
    for filename in ("config.json", "models.json"):
        shutil.copyfile(
            os.path.join(app_config_dir, filename),
            test_workdir / filename,
        )
    for dirname in window.core.config.dirs.values():
        (test_workdir / dirname).mkdir(parents=True, exist_ok=True)

    window.core.config.initialized = True  # prevent initializing config
    window.core.config.init = MagicMock()  # mock init method to prevent init
    window.core.config.load = MagicMock()  # mock load method to prevent loading
    window.core.config.save = MagicMock()  # mock save method to prevent saving
    window.core.config.get_lang = MagicMock(return_value='en')
    window.core.filesystem.get_data_dir.side_effect = (
        lambda ctx=None, meta_id=None, group_id=None, create=True: window.core.config.get_user_dir('data')
    )
    window.core.filesystem.get_runtime_dir.side_effect = (
        lambda name, ctx=None, meta_id=None, group_id=None, create=True: window.core.config.get_user_dir(name)
    )
    window.core.debug = MagicMock()
    window.controller = MagicMock()
    window.tools = MagicMock()
    window.ui = MagicMock()
    window.threadpool = MagicMock()
    window.dispatch = MagicMock()
    window.update_status = MagicMock()
    window.update_state = MagicMock()
    return window


@pytest.fixture
def mock_window_conf():
    window = MagicMock(spec=QMainWindow)
    window.state = MagicMock()
    window.stateChanged = MagicMock()
    window.idx_logger_message = MagicMock()
    window.STATE_IDLE = 'idle'
    window.STATE_BUSY = 'busy'
    window.STATE_ERROR = 'error'
    window.core = MagicMock()
    window.core.models = MagicMock()
    window.core.config = MagicMock(spec=Config)  # mock config object
    window.core.config.path = 'test_path'
    window.core.config.get_lang = MagicMock(return_value='en')
    window.core.debug = MagicMock()
    window.tools = MagicMock()
    window.dispatch = MagicMock()
    window.update_status = MagicMock()
    window.update_state = MagicMock()
    return window
