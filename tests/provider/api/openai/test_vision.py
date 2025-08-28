#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

import base64
import os

from unittest.mock import MagicMock, mock_open, patch

from tests.mocks import mock_window_conf
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.api.openai.vision import Vision


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


def test_send(mock_window_conf):
    """
    Test vision
    """
    vision = Vision(mock_window_conf)
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
    vision.window.core.api.openai.get_client = MagicMock(return_value=client)

    model = ModelItem()
    vision.window.core.ctx.add_item = MagicMock()
    bridge_context = BridgeContext(
        prompt='test_prompt',
        model=model,
        max_tokens=10,
    )
    response = vision.send(
        context=bridge_context,
    )
    assert response.choices[0].message.content == 'test_response'


def test_reset_tokens(mock_window_conf):
    """
    Test reset tokens
    """
    vision = Vision(mock_window_conf)
    vision.input_tokens = 10
    vision.reset_tokens()
    assert vision.input_tokens == 0


def test_build(mock_window_conf):
    """
    Test build vision content
    """
    vision = Vision(mock_window_conf)
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
    assert urls == []
    urls = vision.extract_urls('test https://test.com/img.png test https://test2.com ')
    assert urls == ['https://test.com/img.png']


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
