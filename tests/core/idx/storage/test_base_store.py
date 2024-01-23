#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 11:00:00                  #
# ================================================== #

from tests.mocks import mock_window
from pygpt_net.core.idx.storage.base import BaseStore


def test_attach(mock_window):
    """Test init"""
    store = BaseStore()
    store.attach(mock_window)
    assert store.window == mock_window


def test_exists(mock_window):
    """Test exists"""
    store = BaseStore()
    assert store.exists("test") is None


def test_create(mock_window):
    """Test create"""
    store = BaseStore()
    assert store.create("test") is None


def test_get(mock_window):
    """Test get"""
    store = BaseStore()
    assert store.get("test") is None


def test_store(mock_window):
    """Test store"""
    store = BaseStore()
    assert store.store("test") is None


def test_remove(mock_window):
    """Test remove"""
    store = BaseStore()
    assert store.remove("test") is None
