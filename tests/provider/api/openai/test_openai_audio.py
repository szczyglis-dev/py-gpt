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
import pytest
from unittest.mock import MagicMock
from pygpt_net.provider.api.openai.audio import Audio

@pytest.fixture
def audio_instance():
    return Audio()

def test_build_content_with_string_no_audio(audio_instance):
    ctx = MagicMock()
    ctx.is_audio_input = False
    result = audio_instance.build_content("hello", ctx)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["type"] == "text"
    assert result[0]["text"] == "hello"

def test_build_content_with_list_no_audio(audio_instance):
    ctx = MagicMock()
    ctx.is_audio_input = False
    content = [{"type": "text", "text": "existing"}]
    result = audio_instance.build_content(content, ctx)
    assert result == content

def test_build_content_with_none_no_audio(audio_instance):
    ctx = MagicMock()
    ctx.is_audio_input = False
    result = audio_instance.build_content(None, ctx)
    assert result == []

def test_build_content_with_string_with_audio(audio_instance):
    ctx = MagicMock()
    ctx.is_audio_input = True
    audio_bytes = b"audio_data"
    ctx.audio_data = audio_bytes
    ctx.audio_format = "wav"
    result = audio_instance.build_content("hello", ctx)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["type"] == "text"
    assert result[0]["text"] == "hello"
    expected_encoded = base64.b64encode(audio_bytes).decode("utf-8")
    assert result[1]["type"] == "input_audio"
    assert result[1]["input_audio"]["data"] == expected_encoded
    assert result[1]["input_audio"]["format"] == "wav"

def test_build_content_with_list_with_audio(audio_instance):
    ctx = MagicMock()
    ctx.is_audio_input = True
    audio_bytes = b"binary_audio"
    ctx.audio_data = audio_bytes
    ctx.audio_format = "mp3"
    content = [{"type": "text", "text": "initial"}]
    result = audio_instance.build_content(content, ctx)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == content[0]
    expected_encoded = base64.b64encode(audio_bytes).decode("utf-8")
    assert result[1]["type"] == "input_audio"
    assert result[1]["input_audio"]["data"] == expected_encoded
    assert result[1]["input_audio"]["format"] == "mp3"

def test_build_content_with_empty_string_with_audio(audio_instance):
    ctx = MagicMock()
    ctx.is_audio_input = True
    audio_bytes = b"oggdata"
    ctx.audio_data = audio_bytes
    ctx.audio_format = "ogg"
    result = audio_instance.build_content("", ctx)
    assert isinstance(result, list)
    assert len(result) == 1
    expected_encoded = base64.b64encode(audio_bytes).decode("utf-8")
    assert result[0]["type"] == "input_audio"
    assert result[0]["input_audio"]["data"] == expected_encoded
    assert result[0]["input_audio"]["format"] == "ogg"