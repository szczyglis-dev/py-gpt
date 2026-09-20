#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.17 13:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.core.image import Image


def test_install(mock_window, monkeypatch):
    """Test install"""
    image = Image(mock_window)
    exists_mock = MagicMock(return_value=False)
    makedirs_mock = MagicMock()
    monkeypatch.setattr(os.path, "exists", exists_mock)
    monkeypatch.setattr(os, "makedirs", makedirs_mock)
    image.install()
    makedirs_mock.assert_called()


def test_handle_finished(mock_window):
    """Test handle finished"""
    image = Image(mock_window)
    image.window.controller.chat.image.handle_response = MagicMock()
    ctx = CtxItem()
    image.handle_finished(ctx, ['test'], 'test')
    image.window.controller.chat.image.handle_response.assert_called_once()


def test_handle_finished_inline(mock_window):
    """Test handle finished_inline"""
    image = Image(mock_window)
    image.window.controller.chat.image.handle_response_inline = MagicMock()
    ctx = CtxItem()
    image.handle_finished_inline(ctx, ['test'], 'test')
    image.window.controller.chat.image.handle_response_inline.assert_called_once()


def test_handle_status(mock_window):
    """Test handle status"""
    image = Image(mock_window)
    image.window.ui.status = MagicMock()
    image.handle_status('test')


def test_handle_error(mock_window):
    """Test handle error"""
    image = Image(mock_window)
    image.window.ui.status = MagicMock()
    image.window.core.debug.log = MagicMock()
    image.handle_error('test')
    image.window.core.debug.log.assert_called_once()
