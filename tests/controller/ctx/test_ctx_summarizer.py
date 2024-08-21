#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.21 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.ctx.summarizer import Summarizer
from pygpt_net.item.ctx import CtxItem


def test_summarize(mock_window):
    """Test summarize ctx"""
    summarizer = Summarizer(mock_window)
    summarizer.start_worker = MagicMock()

    item = CtxItem()

    summarizer.summarize(3, item)
    summarizer.start_worker.assert_called_once()


def test_summarizer(mock_window):
    """Test summarizer worker"""
    summarizer = Summarizer(mock_window)
    mock_window.core.gpt.summarizer = MagicMock()

    signal = MagicMock()
    mock_window.core.gpt.summarizer.summary_ctx = MagicMock(return_value='test_title')

    item = CtxItem()
    summarizer.summarizer(3, item, mock_window, signal)
    signal.emit.assert_called_once_with(3, item, 'test_title')


def test_start_worker(mock_window):
    """Test start worker"""
    summarizer = Summarizer(mock_window)
    item = CtxItem()
    summarizer.start_worker(3, item)
    mock_window.threadpool.start.assert_called_once()


def test_handle_update(mock_window):
    """Test handle update"""
    summarizer = Summarizer(mock_window)
    ctx = CtxItem()
    summarizer.handle_update(3, ctx, 'test_title')
    mock_window.controller.ctx.update_name.assert_called_once_with(3, 'test_title', refresh=True)
