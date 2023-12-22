#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 02:00:00                  #
# ================================================== #

import os

import pytest
from unittest.mock import MagicMock

import requests
from PySide6.QtWidgets import QMainWindow

from pygpt_net.core.config import Config
from pygpt_net.core.image import Image


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.config = MagicMock(spec=Config)
    window.config.path = 'test'
    return window


def mock_get(key):
    if key == "img_prompt":
        return 'test'
    elif key == "img_raw":
        return True


def mock_has(key):
    """
    Mock has
    """
    if key == "img_prompt":
        return True


def test_get_prompt(mock_window):
    """
    Test get prompt
    """
    img = Image(window=mock_window)
    img.window.config.get = mock_get
    img.window.config.has = mock_has
    assert img.get_prompt(True) == 'test'


def test_generate(mock_window):
    """
    Test generate
    """
    img = Image(window=mock_window)

    data = []
    item = MagicMock()
    item.url = 'https://test.com/image.png'
    data.append(item)
    response = MagicMock()
    response.data = data

    client = MagicMock()
    client.images.generate.return_value = response
    os.path.join = MagicMock(return_value='test.png')

    data = MagicMock()
    data.content = 'test'
    requests.get = MagicMock(return_value=data)

    img.get_client = MagicMock(return_value=client)
    img.save_image = MagicMock(return_value=True)
    img.window.config.get = mock_get
    img.window.config.has = mock_has
    assert img.generate('test') == (['test.png'], 'test')


def test_make_safe_filename(mock_window):
    """
    Test make safe filename
    """
    img = Image(window=mock_window)
    name = 'Generate an image of a cat with a hat on its head %^5\\dsd___///#42fdsfsdf'
    assert img.make_safe_filename(name) == 'Generate_an_image_of_a_cat_wit'
