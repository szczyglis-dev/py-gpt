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
from pygpt_net.core.gpt import Gpt
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


def test_completion(mock_window):
    """
    Test completion
    """
    gpt = Gpt(mock_window)
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx.return_value = 2048
    gpt.window.core.ctx.get_prompt_items.return_value = []
    gpt.window.core.ctx.get_model_ctx.return_value = 2048
    gpt.build_chat_messages = MagicMock(return_value=[])

    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = 'test_response'
    client.completions.create.return_value = mock_response
    gpt.get_client = MagicMock(return_value=client)

    gpt.window.core.ctx.add_item = MagicMock()
    response = gpt.completion('test_prompt', 10)
    assert response.choices[0].text == 'test_response'


def test_chat(mock_window):
    """
    Test chat
    """
    gpt = Gpt(mock_window)
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx.return_value = 2048
    gpt.window.core.ctx.get_prompt_items.return_value = []
    gpt.window.core.ctx.get_model_ctx.return_value = 2048
    gpt.build_chat_messages = MagicMock(return_value=[])

    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = 'test_response'
    client.chat.completions.create.return_value = mock_response
    gpt.get_client = MagicMock(return_value=client)

    gpt.window.core.ctx.add_item = MagicMock()
    response = gpt.chat('test_prompt', 10)
    assert response.choices[0].message.content == 'test_response'


def test_vision(mock_window):
    """
    Test vision
    """
    gpt = Gpt(mock_window)
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx.return_value = 2048
    gpt.window.core.ctx.get_prompt_items.return_value = []
    gpt.window.core.ctx.get_model_ctx.return_value = 2048
    gpt.build_chat_messages = MagicMock(return_value=[])

    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = 'test_response'
    client.chat.completions.create.return_value = mock_response
    gpt.get_client = MagicMock(return_value=client)

    gpt.window.core.ctx.add_item = MagicMock()
    response = gpt.vision('test_prompt', 10)
    assert response.choices[0].message.content == 'test_response'


def test_reset_tokens(mock_window):
    """
    Test reset tokens
    """
    gpt = Gpt(mock_window)
    gpt.input_tokens = 10
    gpt.reset_tokens()
    assert gpt.input_tokens == 0


def test_build_chat_messages(mock_window):
    """
    Test build chat messages
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    gpt = Gpt(mock_window)
    gpt.system_prompt = 'test_system_prompt'
    gpt.count_used_tokens = MagicMock(return_value=4)
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    gpt.window.core.ctx.get_prompt_items.return_value = items
    gpt.window.core.ctx.get_model_ctx.return_value = 2048

    messages = gpt.build_chat_messages('test_prompt')
    assert len(messages) == 4
    assert messages[0]['content'] == 'test_system_prompt'
    assert messages[1]['content'] == 'user message'
    assert messages[2]['content'] == 'AI message'
    assert messages[3]['content'] == 'test_prompt'


def test_build_completion(mock_window):
    """
    Test build completion
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    gpt = Gpt(mock_window)
    gpt.system_prompt = 'test_system_prompt'
    gpt.count_used_tokens = MagicMock(return_value=4)
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    gpt.window.core.ctx.get_prompt_items.return_value = items

    message = gpt.build_completion('test_prompt')
    assert message == 'test_system_prompt\nuser message\nAI message\ntest_prompt'


def test_build_completion_with_names(mock_window):
    """
    Test build completion with names
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    ctx_item.input_name = 'User'
    ctx_item.output_name = 'AI'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    ctx_item.input_name = 'User'
    ctx_item.output_name = 'AI'
    items.append(ctx_item)

    gpt = Gpt(mock_window)
    gpt.system_prompt = 'test_system_prompt'
    gpt.user_name = 'User'
    gpt.ai_name = 'AI'
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    gpt.window.core.ctx.get_prompt_items.return_value = items

    message = gpt.build_completion('test_prompt')
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'


def test_build_vision_content(mock_window):
    """
    Test build vision content
    """
    gpt = Gpt(mock_window)
    gpt.extract_urls = MagicMock(return_value=['https://test.com'])
    gpt.is_image = MagicMock(return_value=True)
    gpt.encode_image = MagicMock(return_value='test_base64')
    gpt.attachments = {'test_uuid': MagicMock()}
    gpt.attachments['test_uuid'].path = 'test_path'

    os.path.exists = MagicMock(return_value=True)
    content = gpt.build_vision_content('test_text', True)
    assert len(content) == 3
    assert content[0]['type'] == 'text'
    assert content[0]['text'] == 'test_text'
    assert content[1]['type'] == 'image_url'
    assert content[1]['image_url']['url'] == 'https://test.com'
    assert content[2]['type'] == 'image_url'
    assert content[2]['image_url']['url'] == 'data:image/jpeg;base64,test_base64'


def test_count_used_tokens(mock_window):
    """
    Test count used tokens
    """
    gpt = Gpt(mock_window)
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    tokens = gpt.count_used_tokens('test_text')
    assert tokens == 209
    tokens = gpt.count_used_tokens('test_text test_texttest_texttest_texttest_texttest_texttest_text')
    assert tokens == 209
    tokens = gpt.count_used_tokens('')
    assert tokens == 209


def test_quick_call(mock_window):
    """
    Test quick call
    """
    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = 'test_response'
    client.chat.completions.create.return_value = mock_response
    gpt = Gpt(mock_window)
    gpt.get_client = MagicMock(return_value=client)
    gpt.build_chat_messages = MagicMock(return_value='test_messages')
    gpt.window.core.config.get.side_effect = mock_get
    response = gpt.quick_call('test_prompt', 'test_system_prompt')
    assert response == 'test_response'


def test_prepare_ctx_name(mock_window):
    """
    Test prepare ctx name
    """
    gpt = Gpt(mock_window)
    gpt.quick_call = MagicMock(return_value='test_response')
    gpt.window.core.config.get.side_effect = mock_get
    gpt.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    gpt.window.core.ctx.get_prompt_items = MagicMock(return_value=[])
    response = gpt.prepare_ctx_name(CtxItem())
    assert response == 'test_response'


def test_extract_urls():
    """
    Test extract urls
    """
    gpt = Gpt()
    urls = gpt.extract_urls('test https://test.com test https://test2.com')
    assert urls == ['https://test.com', 'https://test2.com']
    urls = gpt.extract_urls('test https://test.com/img.png test https://test2.com ')
    assert urls == ['https://test.com/img.png', 'https://test2.com']


def test_is_image():
    """
    Test is image
    """
    gpt = Gpt()
    assert gpt.is_image('https://test.com/test.png')
    assert gpt.is_image('https://test.com/test.jpg')
    assert gpt.is_image('https://test.com/test.jpeg')
    assert gpt.is_image('https://test.com/test.tiff')
    assert gpt.is_image('https://test.com/test.bmp')
    assert gpt.is_image('https://test.com/test.gif')
    assert gpt.is_image('https://test.com/test.webp')
    assert not gpt.is_image('https://test.com/test.txt')
    assert not gpt.is_image('https://test.com/test.png.txt')
    assert not gpt.is_image('https://test.com/test.jpg.txt')
    assert not gpt.is_image('https://test.com/test.jpeg.txt')
    assert not gpt.is_image('https://test.com/test.tiff.txt')
    assert not gpt.is_image('https://test.com/test.bmp.txt')
    assert not gpt.is_image('https://test.com/test.gif.txt')
    assert not gpt.is_image('https://test.com/test.webp.txt')


def test_encode_image():
    """
    Test encode image
    """
    gpt = Gpt()
    fake_image_data = b'fake_image_binary_data'
    encoded_data = base64.b64encode(fake_image_data)
    image_path = 'tests/test.png'
    with patch('builtins.open', mock_open(read_data=fake_image_data)) as mock_file:
        with patch('base64.b64encode', return_value=encoded_data) as mock_base64:
            result = gpt.encode_image(image_path)
            mock_file.assert_called_once_with(image_path, "rb")
            mock_base64.assert_called_once_with(fake_image_data)
            assert result == encoded_data.decode('utf-8')
