#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
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


def test_apply_text(mock_window):
    """Test apply text"""
    option = {
        'type': 'text',
    }
    cfg = Config(mock_window)
    cfg.input.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.input.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_textarea(mock_window):
    """Test apply textarea"""
    option = {
        'type': 'textarea',
    }
    cfg = Config(mock_window)
    cfg.textarea.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.textarea.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_bool(mock_window):
    """Test apply bool"""
    option = {
        'type': 'bool',
    }
    cfg = Config(mock_window)
    cfg.checkbox.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.checkbox.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_dict(mock_window):
    """Test apply dict"""
    option = {
        'type': 'dict',
    }
    cfg = Config(mock_window)
    cfg.dictionary.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.dictionary.apply.assert_called_once_with("parent_id", "key", option)


def test_apply_combo(mock_window):
    """Test apply combo"""
    option = {
        'type': 'combo',
    }
    cfg = Config(mock_window)
    cfg.combo.apply = MagicMock()
    cfg.apply("parent_id", "key", option)
    cfg.combo.apply.assert_called_once_with("parent_id", "key", option)


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