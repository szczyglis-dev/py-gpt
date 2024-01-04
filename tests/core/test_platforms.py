#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 08:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.platforms import Platforms


def test_get_os():
    """Test get OS"""
    platforms = Platforms()
    assert type(platforms.get_os()) == str


def test_get_architecture():
    """Test get architecture"""
    platforms = Platforms()
    assert type(platforms.get_architecture()) == str


def test_is_linux():
    """Test is Linux"""
    platforms = Platforms()
    assert type(platforms.is_linux()) == bool


def test_is_mac():
    """Test is MacOS"""
    platforms = Platforms()
    assert type(platforms.is_mac()) == bool


def test_is_windows():
    """Test is Windows"""
    platforms = Platforms()
    assert type(platforms.is_windows()) == bool


def test_is_snap():
    """Test is snap"""
    platforms = Platforms()
    assert type(platforms.is_snap()) == bool
