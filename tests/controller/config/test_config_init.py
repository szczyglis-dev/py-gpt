#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.config import Config


def test_load_options(mock_window):
    """Test load options"""
    cfg = Config(mock_window)
    option = {
        'type': 'int',
        'slider': True
    }
    options = {
        'key': option
    }
    cfg.apply = MagicMock()
    cfg.load_options("parent_id", options)
    cfg.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_int(mock_window):
    """Test apply int"""
    option = {
        'type': 'int',
        'slider': True
    }
    cfg = Config(mock_window)
    cfg.slider.apply = MagicMock()
    cfg.input.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.slider.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_float(mock_window):
    """Test apply float"""
    option = {
        'type': 'float',
        'slider': True
    }
    cfg = Config(mock_window)
    cfg.slider.apply = MagicMock()
    cfg.input.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.slider.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_value(mock_window):
    """Test apply value"""
    option = {
        'type': 'int',
        'slider': True
    }
    cfg = Config(mock_window)
    cfg.slider.apply = MagicMock()
    cfg.input.apply = MagicMock()
    cfg.apply_value("parent_id", "key", option, 1)
    cfg.slider.apply.assert_called_once_with("parent_id", "key", option)


def test_get_value(mock_window):
    """Test get value"""
    option = {
        'type': 'int',
        'slider': True
    }
    cfg = Config(mock_window)
    cfg.slider.get_value = MagicMock(return_value=1)
    cfg.input.get_value = MagicMock(return_value=2)
    assert cfg.get_value("parent_id", "key", option) == 1
    cfg.slider.get_value.assert_called_once_with("parent_id", "key", option)
    cfg.input.get_value.assert_not_called()