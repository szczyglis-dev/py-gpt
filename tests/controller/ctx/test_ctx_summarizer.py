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
from pygpt_net.controller.ctx.summarizer import Summarizer
from pygpt_net.item.ctx import CtxItem


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
    window.threadpool = MagicMock()
    return window


def test_summarize(mock_window):
    """Test summarize ctx"""
    summarizer = Summarizer(mock_window)
    summarizer.start_worker = MagicMock()

    item = CtxItem()

    summarizer.summarize(3, item)
    summarizer.start_worker.assert_called_once_with(3, item)


def test_summarizer(mock_window):
    """Test summarizer worker"""
    summarizer = Summarizer(mock_window)
    mock_window.core.gpt.summarizer = MagicMock()

    signal = MagicMock()
    mock_window.core.gpt.summarizer.summary_ctx = MagicMock(return_value='test_title')

    item = CtxItem()
    summarizer.summarizer(3, item, mock_window, signal)
    signal.emit.assert_called_once_with(3, 'test_title')


def test_start_worker(mock_window):
    """Test start worker"""
    summarizer = Summarizer(mock_window)
    item = CtxItem()
    summarizer.start_worker(3, item)
    mock_window.threadpool.start.assert_called_once()


def test_handle_update(mock_window):
    """Test handle update"""
    summarizer = Summarizer(mock_window)
    summarizer.handle_update(3, 'test_title')
    mock_window.controller.ctx.update_name.assert_called_once_with(3, 'test_title')
