#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.19 19:00:00                  #
# ================================================== #

from tests.mocks import mock_window
from pygpt_net.provider.vector_stores.base import BaseStore


def test_attach(mock_window):
    """Test init"""
    store = BaseStore()
    store.attach(mock_window)
    assert store.window == mock_window


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
