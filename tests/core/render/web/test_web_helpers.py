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
import html
import pytest
from unittest.mock import MagicMock
from pygpt_net.core.render.web.helpers import Helpers

@pytest.fixture
def dummy_window():
    window = MagicMock()
    fs = MagicMock()
    fs.get_workdir_prefix.return_value = "/tmp"
    window.core.filesystem = fs
    config = MagicMock()
    config.get.return_value = False
    window.core.config = config
    return window

@pytest.fixture
def helper(dummy_window):
    return Helpers(window=dummy_window)

def test_init(dummy_window):
    h = Helpers(window=dummy_window)
    assert h.window == dummy_window

def test_replace_code_tags_tool():
    h = Helpers()
    inp = "<p class=\"cmd\">print(<hello>)</p>"
    exp = '<p class=\"cmd\">print(<hello>)</p>'
    out = h.replace_code_tags(inp)
    assert out == exp

def test_replace_code_tags_math():
    h = Helpers()
    inp = r"Math: \(a < b>\)"
    exp = "Math: \\(a < b>\\)"
    out = h.replace_code_tags(inp)
    assert out == exp

def test_pre_format_text(helper):
    inp = "   <think>Test</think> and (file:///home/test) and <p class=\"ccc\">print(<hello>)   "
    exp = "<think>Test</think> and (file:///home/test) and &lt;p class=\"ccc\"&gt;print(&lt;hello&gt;)"
    out = helper.pre_format_text(inp)
    assert out == exp

def test_post_format_text_true(dummy_window):
    dummy_window.core.config.get.return_value = True
    h = Helpers(window=dummy_window)
    inp = " __agent_begin__ content __agent_end__ "
    exp = '<div class="msg-agent"> content </div>'
    out = h.post_format_text(inp)
    assert out == exp

def test_post_format_text_false(dummy_window):
    dummy_window.core.config.get.return_value = False
    h = Helpers(window=dummy_window)
    inp = " __agent_begin__ content __agent_end__ "
    exp = "__agent_begin__ content __agent_end__"
    out = h.post_format_text(inp)
    assert out == exp

def test_format_user_text_condition():
    h = Helpers()
    inp = "[Hello]"
    esc = html.escape(inp).replace("\n", "<br>")
    exp = '<div class="cmd">&gt; {}</div>'.format(esc)
    out = h.format_user_text(inp)
    assert out == exp

def test_format_user_text_no_condition():
    h = Helpers()
    inp = "Hello <world>"
    exp = html.escape(inp).replace("\n", "<br>")
    out = h.format_user_text(inp)
    assert out == exp

def test_format_cmd_text():
    h = Helpers()
    inp = "Hello <cmd>"
    exp = html.escape(inp)
    out = h.format_cmd_text(inp)
    assert out == exp

def test_format_chunk():
    h = Helpers()
    inp = "line1\nline2"
    exp = "line1<br/>line2"
    out = h.format_chunk(inp)
    assert out == exp