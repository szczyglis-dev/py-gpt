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

import re
import pytest
from unittest.mock import MagicMock
from pygpt_net.provider.gpt.utils import sanitize_name

def test_sanitize_name_none():
    assert sanitize_name(None) == ""

def test_sanitize_name_empty():
    assert sanitize_name("") == ""

def test_sanitize_name_no_special():
    assert sanitize_name("JohnDoe") == "johndoe"

def test_sanitize_name_with_spaces():
    assert sanitize_name("  John Doe   ") == "john_doe"

def test_sanitize_name_with_special_chars():
    assert sanitize_name("John!@#Doe") == "john___doe"

def test_sanitize_name_with_allowed_chars():
    assert sanitize_name("John_Doe-123") == "john_doe-123"

def test_sanitize_name_length_limit():
    long_name = "A" * 70
    expected = ("a" * 64)
    assert sanitize_name(long_name) == expected

def test_sanitize_name_mixed():
    input_str = "  Hello World! Test-Case_123 $$$ "
    expected = "hello_world__test-case_123____"
    assert sanitize_name(input_str) == expected

def test_re_sub_called(monkeypatch):
    original_sub = re.sub
    mock_sub = MagicMock(side_effect=original_sub)
    monkeypatch.setattr(re, "sub", mock_sub)
    sanitize_name("Example Test")
    mock_sub.assert_called_once_with(r'[^a-z0-9_-]', '_', "example test")