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

import json
import pytest
from unittest.mock import MagicMock
from pygpt_net.provider.api.openai.tools import Tools

def test_prepare_with_functions_none():
    t = Tools()
    model = MagicMock()
    result = t.prepare(model, None)
    assert result == []

def test_prepare_with_empty_list():
    t = Tools()
    model = MagicMock()
    result = t.prepare(model, [])
    assert result == []

def test_prepare_skips_invalid_names():
    t = Tools()
    model = MagicMock(provider="test")
    funcs = [
        {"name": "  ", "params": '{"a": "1"}', "desc": "desc"},
        {"name": None, "params": '{"a": "1"}', "desc": "desc"},
        {"name": "valid", "params": '', "desc": "desc"}
    ]
    result = t.prepare(model, funcs)
    expected = [{"type": "function", "function": {"name": "valid", "parameters": {}, "description": "desc"}}]
    assert result == expected

def test_prepare_basic():
    t = Tools()
    model = MagicMock(provider="other")
    funcs = [
        {"name": "func1", "params": '{"key": "value"}', "desc": "description1"}
    ]
    result = t.prepare(model, funcs)
    expected = [{"type": "function", "function": {"name": "func1", "parameters": {"key": "value"}, "description": "description1"}}]
    assert result == expected

def test_prepare_params_none():
    t = Tools()
    model = MagicMock(provider="other")
    funcs = [{"name": "func_none", "params": None, "desc": "desc"}]
    result = t.prepare(model, funcs)
    expected = [{"type": "function", "function": {"name": "func_none", "parameters": {}, "description": "desc"}}]
    assert result == expected

def test_prepare_google_modification():
    t = Tools()
    model = MagicMock(provider="google")
    funcs = [
        {"name": "google_func", "params": '{"properties": {"a": {"type": "integer", "enum": [1,2]}, "b": {"type": "string", "enum": ["x","y"]}}}', "desc": "desc_google"}
    ]
    result = t.prepare(model, funcs)
    expected_params = {"properties": {"a": {"type": "integer"}, "b": {"type": "string", "enum": ["x", "y"]}}}
    expected = [{"type": "function", "function": {"name": "google_func", "parameters": expected_params, "description": "desc_google"}}]
    assert result == expected

def test_prepare_responses_api_with_functions_none():
    t = Tools()
    model = MagicMock()
    result = t.prepare_responses_api(model, None)
    assert result == []

def test_prepare_responses_api_with_empty_list():
    t = Tools()
    model = MagicMock()
    result = t.prepare_responses_api(model, [])
    assert result == []

def test_prepare_responses_api_skips_invalid_names():
    t = Tools()
    model = MagicMock(provider="test")
    funcs = [
        {"name": "   ", "params": '{"a": "1"}', "desc": "desc"},
        {"name": None, "params": '{"a": "1"}', "desc": "desc"},
        {"name": "valid", "params": '', "desc": "desc"}
    ]
    result = t.prepare_responses_api(model, funcs)
    expected = [{"type": "function", "name": "valid", "parameters": {}, "description": "desc"}]
    assert result == expected

def test_prepare_responses_api_basic():
    t = Tools()
    model = MagicMock(provider="other")
    funcs = [
        {"name": "func1", "params": '{"key": "value"}', "desc": "description1"}
    ]
    result = t.prepare_responses_api(model, funcs)
    expected = [{"type": "function", "name": "func1", "parameters": {"key": "value"}, "description": "description1"}]
    assert result == expected

def test_prepare_responses_api_params_none():
    t = Tools()
    model = MagicMock(provider="other")
    funcs = [{"name": "func_none", "params": None, "desc": "desc"}]
    result = t.prepare_responses_api(model, funcs)
    expected = [{"type": "function", "name": "func_none", "parameters": {}, "description": "desc"}]
    assert result == expected