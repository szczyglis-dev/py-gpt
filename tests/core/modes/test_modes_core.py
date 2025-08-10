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

from unittest.mock import MagicMock, patch

from pygpt_net.item.mode import ModeItem
from tests.mocks import mock_window
from pygpt_net.core.modes import Modes


def test_get_by_idx(mock_window):
    """Test get_by_idx"""
    modes = Modes(mock_window)
    modes.items = {"test": ModeItem()}
    assert modes.get_by_idx(0) == "test"


def test_get_idx_by_name(mock_window):
    """Test get_idx_by_name"""
    modes = Modes(mock_window)
    modes.items = {"test": ModeItem()}
    assert modes.get_idx_by_name("test") == 0


def test_get_all(mock_window):
    """Test get_all"""
    modes = Modes(mock_window)
    item = ModeItem()
    modes.items = {"test": item}
    assert modes.get_all() == {"test": item}


def test_get_default(mock_window):
    """Test get_default"""
    modes = Modes(mock_window)
    item = ModeItem()
    item.default = True
    modes.items = {"test": item}
    assert modes.get_default() == "test"


def test_load(mock_window):
    """Test load"""
    modes = Modes(mock_window)
    item = ModeItem()
    modes.provider.load = MagicMock(return_value={"test": item})
    modes.load()
    assert modes.items == {"test": item}


def test_save(mock_window):
    """Test save"""
    modes = Modes(mock_window)
    item = ModeItem()
    modes.items = {"test": item}
    modes.provider.save = MagicMock()
    modes.save()
    modes.provider.save.assert_called_once_with({"test": item})
