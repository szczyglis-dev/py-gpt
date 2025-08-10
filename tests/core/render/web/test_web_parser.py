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
import os
import sys
import pytest
import markdown
from bs4 import BeautifulSoup, NavigableString
from pygpt_net.core.render.web.parser import Parser

@pytest.fixture(autouse=True)
def patch_trans(monkeypatch):
    module = sys.modules[Parser.__module__]
    monkeypatch.setattr(module, "trans", lambda s: s)

@pytest.fixture
def dummy_window():
    class DummyConfig:
        def get_app_path(self):
            return "/dummy/app"
        def get(self, key):
            if key == "render.code_syntax":
                return "python"
            return None
    class DummyCore:
        config = DummyConfig()
    class DummyWindow:
        core = DummyCore()
    return DummyWindow()

@pytest.fixture
def parser_with_window(dummy_window):
    return Parser(window=dummy_window)

@pytest.fixture
def parser_no_window():
    return Parser()

def test_init(parser_no_window):
    parser_no_window.init()
    assert parser_no_window.md is not None

def test_reset(parser_no_window):
    parser_no_window.code_blocks = {1: "test"}
    parser_no_window.block_idx = 5
    parser_no_window.reset()
    assert parser_no_window.block_idx == 1

def test_prepare_paths(parser_no_window):
    text = "Link](file://example)"
    result = parser_no_window.prepare_paths(text)
    assert "](file://example)" in result

def test_parse(parser_with_window):
    input_text = "Test link](file://path)"
    result = parser_with_window.parse(input_text)
    assert "file://path" in result
    assert "<p>" in result

def test_parse_exception(parser_with_window, monkeypatch):
    parser_with_window.init()
    monkeypatch.setattr(parser_with_window.md, "convert", lambda x: (_ for _ in ()).throw(Exception("error")))
    result = parser_with_window.parse("   test   ")
    assert result == "test"

def test_parse_code(parser_with_window):
    input_text = "Sample **text**"
    result = parser_with_window.parse_code(input_text)
    assert "Sample" in result

def test_parse_code_exception(parser_with_window, monkeypatch):
    parser_with_window.init()
    monkeypatch.setattr(parser_with_window.md, "convert", lambda x: (_ for _ in ()).throw(Exception("error")))
    result = parser_with_window.parse_code("   code   ")
    assert result == "   code   "

def test_to_plain_text(parser_no_window):
    html = "<p>Hello World</p>"
    result = parser_no_window.to_plain_text(html)
    assert result.strip() == "Hello World"

def test_strip_whitespace_codeblocks(parser_no_window):
    soup = BeautifulSoup('<code>   hello  </code>', 'html.parser')
    parser_no_window.strip_whitespace_codeblocks(soup)
    code = soup.find('code')
    assert code.string == "hello"

def test_strip_whitespace_lists(parser_no_window):
    soup = BeautifulSoup('<li>    <strong>Test</strong>   </li>', 'html.parser')
    parser_no_window.strip_whitespace_lists(soup)
    li = soup.find('li')
    for item in li.contents:
        if isinstance(item, NavigableString):
            assert item.strip() == ""

def test_parse_code_blocks(parser_no_window):
    html = '<pre><code class="language-python">print("hello")</code></pre>'
    soup = BeautifulSoup(html, 'html.parser')
    parser_no_window.parse_code_blocks(soup)
    div = soup.find('div', class_="code-wrapper")
    assert div is not None
    assert div.get("data-index") == "1"

def test_highlight_code_blocks_python(parser_with_window):
    html = '<pre><code class="language-python">print("hello")</code></pre>'
    soup = BeautifulSoup(html, 'html.parser')
    parser_with_window.highlight_code_blocks(soup)
    div = soup.find('div', class_="code-wrapper")
    assert div is not None
    classes = div.get("class", [])
    assert "highlight" in classes
    assert div.get("data-index") == "1"
    code = div.find("code")
    assert code is not None
    assert "language-python" in code.get("class", [])
    assert code.string == 'print("hello")'

def test_highlight_code_blocks_html(parser_with_window):
    html = '<pre><code class="language-html"><div></div></code></pre>'
    soup = BeautifulSoup(html, 'html.parser')
    parser_with_window.highlight_code_blocks(soup)
    preview = soup.find("a", class_="code-header-action code-header-preview")
    assert preview is None

def test_convert_lists_to_paragraphs(parser_no_window):
    html = '<ul><li>Item 1</li><li>Item 2</li></ul><ol><li>First</li><li>Second</li></ol>'
    soup = BeautifulSoup(html, 'html.parser')
    parser_no_window.convert_lists_to_paragraphs(soup)
    assert not soup.find('ul')
    assert not soup.find('ol')
    ps = soup.find_all('p', class_="list")
    texts = [p.get_text() for p in ps]
    assert "- Item 1" in texts
    assert "- Item 2" in texts
    assert "1. First" in texts
    assert "2. Second" in texts

def test_convert_list(parser_no_window):
    soup = BeautifulSoup('<ul><li>Item1</li></ul>', 'html.parser')
    ul = soup.find('ul')
    parser_no_window.convert_list(soup, ul, ordered=False)
    p = ul.find_previous_sibling('p', class_="list")
    assert p is not None
    assert p.get_text() == "- Item1"

def test_format_images(parser_no_window):
    html = '<div><img src="image.png"><img src="photo.jpg"></div>'
    soup = BeautifulSoup(html, 'html.parser')
    parser_no_window.format_images(soup)
    imgs = soup.find_all('img')
    for img in imgs:
        assert img.get("width") == "400"