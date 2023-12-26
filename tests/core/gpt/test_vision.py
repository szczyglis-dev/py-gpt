#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import base64
import os

import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from pygpt_net.config import Config
from pygpt_net.core.gpt.vision import Vision
from pygpt_net.item.ctx import CtxItem


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.models = MagicMock()
    window.core.config = MagicMock(spec=Config)
    window.core.config.path = 'test_path'
    return window


def mock_get(key):
    if key == "use_context":
        return True
    elif key == "model":
        return "gpt-3.5-turbo"
    elif key == "mode":
        return "chat"
    elif key == "max_total_tokens":
        return 2048
    elif key == "context_threshold":
        return 200


def test_send(mock_window):
    """
    Test vision
    """
    vision = Vision(mock_window)
    vision.window.core.config.get.side_effect = mock_get
    vision.window.core.models.get_num_ctx.return_value = 2048
    vision.window.core.ctx.get_prompt_items.return_value = []
    vision.window.core.ctx.get_model_ctx.return_value = 2048
    vision.build_chat_messages = MagicMock(return_value=[])

    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = 'test_response'
    client.chat.completions.create.return_value = mock_response
    vision.window.core.gpt.get_client = MagicMock(return_value=client)

    vision.window.core.ctx.add_item = MagicMock()
    response = vision.send('test_prompt', 10)
    assert response.choices[0].message.content == 'test_response'


def test_reset_tokens(mock_window):
    """
    Test reset tokens
    """
    vision = Vision(mock_window)
    vision.input_tokens = 10
    vision.reset_tokens()
    assert vision.input_tokens == 0


def test_build(mock_window):
    """
    Test build vision content
    """
    vision = Vision(mock_window)
    vision.extract_urls = MagicMock(return_value=['https://test.com'])
    vision.is_image = MagicMock(return_value=True)
    vision.encode_image = MagicMock(return_value='test_base64')
    attachments = {'test_uuid': MagicMock()}
    attachments['test_uuid'].path = 'test_path'

    os.path.exists = MagicMock(return_value=True)
    content = vision.build_content('test_text', attachments)
    assert len(content) == 3
    assert content[0]['type'] == 'text'
    assert content[0]['text'] == 'test_text'
    assert content[1]['type'] == 'image_url'
    assert content[1]['image_url']['url'] == 'https://test.com'
    assert content[2]['type'] == 'image_url'
    assert content[2]['image_url']['url'] == 'data:image/jpeg;base64,test_base64'


def test_extract_urls():
    """
    Test extract urls
    """
    vision = Vision()
    urls = vision.extract_urls('test https://test.com test https://test2.com')
    assert urls == ['https://test.com', 'https://test2.com']
    urls = vision.extract_urls('test https://test.com/img.png test https://test2.com ')
    assert urls == ['https://test.com/img.png', 'https://test2.com']


def test_is_image():
    """
    Test is image
    """
    vision = Vision()
    assert vision.is_image('https://test.com/test.png')
    assert vision.is_image('https://test.com/test.jpg')
    assert vision.is_image('https://test.com/test.jpeg')
    assert vision.is_image('https://test.com/test.tiff')
    assert vision.is_image('https://test.com/test.bmp')
    assert vision.is_image('https://test.com/test.gif')
    assert vision.is_image('https://test.com/test.webp')
    assert not vision.is_image('https://test.com/test.txt')
    assert not vision.is_image('https://test.com/test.png.txt')
    assert not vision.is_image('https://test.com/test.jpg.txt')
    assert not vision.is_image('https://test.com/test.jpeg.txt')
    assert not vision.is_image('https://test.com/test.tiff.txt')
    assert not vision.is_image('https://test.com/test.bmp.txt')
    assert not vision.is_image('https://test.com/test.gif.txt')
    assert not vision.is_image('https://test.com/test.webp.txt')


def test_encode_image():
    """
    Test encode image
    """
    vision = Vision()
    fake_image_data = b'fake_image_binary_data'
    encoded_data = base64.b64encode(fake_image_data)
    image_path = 'tests/test.png'
    with patch('builtins.open', mock_open(read_data=fake_image_data)) as mock_file:
        with patch('base64.b64encode', return_value=encoded_data) as mock_base64:
            result = vision.encode_image(image_path)
            mock_file.assert_called_once_with(image_path, "rb")
            mock_base64.assert_called_once_with(fake_image_data)
            assert result == encoded_data.decode('utf-8')
