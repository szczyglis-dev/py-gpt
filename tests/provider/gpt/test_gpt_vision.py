#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import base64
import os
import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from pygpt_net.provider.gpt.vision import Vision

@pytest.fixture
def dummy_window():
    mw = MagicMock()
    mw.core = MagicMock()
    client = MagicMock()
    client.chat.completions.create.return_value = "response"
    mw.core.gpt.get_client.return_value = client
    tokens = MagicMock()
    tokens.from_user.return_value = 10
    tokens.from_messages.return_value = 50
    mw.core.tokens = tokens
    config = MagicMock()
    config.get.side_effect = lambda key: {"max_total_tokens": 100, "use_context": True}.get(key, None)
    mw.core.config = config
    ctx = MagicMock()
    def get_history(history, model_id, mode, used_tokens, max_ctx_tokens):
        return history or []
    ctx.get_history.side_effect = get_history
    mw.core.ctx = ctx
    filesystem = MagicMock()
    filesystem.make_local_list.side_effect = lambda lst: lst
    mw.core.filesystem = filesystem
    return mw

@pytest.fixture
def vision(dummy_window):
    return Vision(dummy_window)

def test_init(dummy_window):
    v = Vision(dummy_window)
    assert v.window == dummy_window
    assert v.attachments == {}
    assert v.urls == []
    assert v.input_tokens == 0

def test_send(vision):
    model = SimpleNamespace(id="test-model", ctx=80)
    context = SimpleNamespace(prompt="test prompt", stream=False, max_tokens=20, system_prompt="sys prompt", attachments={}, model=model, history=[])
    response = vision.send(context)
    assert response == "response"
    vision.window.core.gpt.get_client.return_value.chat.completions.create.assert_called_once()

def test_build_with_context(vision):
    model = SimpleNamespace(id="test-model", ctx=80)
    history_item = SimpleNamespace(final_input="history input", final_output="history output")
    messages = vision.build(prompt="new prompt", system_prompt="system text", model=model, history=[history_item], attachments=None)
    assert messages[0] == {"role": "system", "content": "system text"}
    assert messages[1] == {"role": "user", "content": "history input"}
    assert messages[2] == {"role": "assistant", "content": "history output"}
    assert messages[3] == {"role": "user", "content": [{"type": "text", "text": "new prompt"}]}
    assert vision.input_tokens == 50

def test_build_without_context(dummy_window):
    dummy_window.core.config.get.side_effect = lambda key: {"max_total_tokens": 100, "use_context": False}.get(key, None)
    v = Vision(dummy_window)
    model = SimpleNamespace(id="test-model", ctx=80)
    messages = v.build(prompt="prompt", system_prompt="system", model=model, history=[SimpleNamespace(final_input="input", final_output="output")], attachments=None)
    assert messages[0] == {"role": "system", "content": "system"}
    assert messages[1] == {"role": "user", "content": [{"type": "text", "text": "prompt"}]}
    assert v.input_tokens == 50

def test_build_content_no_url(vision):
    content = vision.build_content("hello", None)
    assert content == [{"type": "text", "text": "hello"}]

def test_build_content_with_url(vision):
    content = vision.build_content("http://example.com/image.jpg", None)
    assert content[0] == {"type": "text", "text": "http://example.com/image.jpg"}
    assert content[1] == {"type": "image_url", "image_url": {"url": "http://example.com/image.jpg"}}
    assert vision.urls == ["http://example.com/image.jpg"]

def test_build_content_with_attachment(vision, monkeypatch):
    dummy = SimpleNamespace(path="/fake/path/image.jpg", consumed=False)
    monkeypatch.setattr(os.path, "exists", lambda path: True)
    monkeypatch.setattr(Vision, "encode_image", lambda self, p: "dummy_encoded")
    content = vision.build_content("test", {"att1": dummy})
    assert content[0] == {"type": "text", "text": "test"}
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,dummy_encoded"}}
    assert vision.attachments == {"att1": "/fake/path/image.jpg"}
    assert dummy.consumed is True

def test_build_agent_input(vision, monkeypatch):
    dummy = SimpleNamespace(path="/fake/path/image.jpg", consumed=False)
    monkeypatch.setattr(os.path, "exists", lambda path: True)
    monkeypatch.setattr(Vision, "encode_image", lambda self, p: "dummy_encoded")
    items = vision.build_agent_input("http://example.com/image.jpg prompt", {"att1": dummy})
    assert items[0]["role"] == "user"
    contents = items[0]["content"]
    assert {"type": "input_image", "image_url": "http://example.com/image.jpg"} in contents
    assert {"type": "input_image", "detail": "auto", "image_url": "data:image/jpeg;base64,dummy_encoded"} in contents
    assert items[1] == {"role": "user", "content": "http://example.com/image.jpg prompt"}
    assert vision.urls == ["http://example.com/image.jpg"]
    assert vision.attachments == {"att1": "/fake/path/image.jpg"}
    assert dummy.consumed is True

def test_get_attachment(vision, monkeypatch):
    dummy = SimpleNamespace(path="/fake/path/image.jpg", consumed=False)
    attachments = {"att1": dummy}
    monkeypatch.setattr(os.path, "exists", lambda path: True)
    monkeypatch.setattr(Vision, "encode_image", lambda self, p: "dummy_encoded")
    result = vision.get_attachment(attachments)
    assert result == "dummy_encoded"
    assert dummy.consumed is True

def test_get_attachment_empty(vision):
    result = vision.get_attachment({})
    assert result is None

def test_extract_urls(vision):
    res = vision.extract_urls("http://example.com/image.jpg")
    assert res == ["http://example.com/image.jpg"]
    res = vision.extract_urls("Check this image http://example.com/image.jpg")
    assert res == ["http://example.com/image.jpg"]
    res = vision.extract_urls("Text with non-image http://example.com/file.txt")
    assert res == []

def test_is_image(vision):
    assert vision.is_image("image.jpg") is True
    assert vision.is_image("image.PNG") is True
    assert vision.is_image("document.pdf") is False

def test_encode_image(vision, tmp_path):
    file = tmp_path / "test.jpg"
    file.write_bytes(b"testdata")
    encoded = vision.encode_image(str(file))
    expected = base64.b64encode(b"testdata").decode('utf-8')
    assert encoded == expected

def test_reset_tokens(vision):
    vision.input_tokens = 100
    vision.reset_tokens()
    assert vision.input_tokens == 0

def test_get_attachments(vision):
    vision.attachments = {"a": "p"}
    assert vision.get_attachments() == {"a": "p"}

def test_get_urls(vision):
    vision.urls = ["u"]
    assert vision.get_urls() == ["u"]

def test_get_used_tokens(vision):
    vision.input_tokens = 42
    assert vision.get_used_tokens() == 42

def test_append_images(vision):
    ctx = SimpleNamespace()
    vision.attachments = {"a": "path1"}
    vision.urls = ["url1"]
    vision.window.core.filesystem.make_local_list = lambda lst: lst
    vision.append_images(ctx)
    assert ctx.images == ["url1"]
    assert ctx.urls == ["url1"]