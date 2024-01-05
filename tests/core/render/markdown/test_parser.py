#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.05 11:00:00                  #
# ================================================== #

from tests.mocks import mock_window
from pygpt_net.core.render.markdown.parser import Parser


def test_init():
    parser = Parser()
    assert parser.md is None
    parser.init()
    assert parser.md is not None


def test_parse_markdown_to_html():
    parser = Parser()
    parser.init()

    markdown_input_ul = """
- Item 1
- Item 2
- Item 3
"""

    expected_html_output_ul = """
<p class="list">- Item 1</p>
<p class="list">- Item 2</p>
<p class="list">- Item 3</p>
"""

    markdown_input_ol = """
1. Item 1
2. Item 2
3. Item 3
"""

    expected_html_output_ol = """
<p class="list">1. Item 1</p>
<p class="list">2. Item 2</p>
<p class="list">3. Item 3</p>
"""

    actual_html_output_ul = parser.parse(markdown_input_ul)
    actual_html_output_ol = parser.parse(markdown_input_ol)

    assert ''.join(actual_html_output_ul.split()) == ''.join(expected_html_output_ul.split())
    assert ''.join(actual_html_output_ol.split()) == ''.join(expected_html_output_ol.split())


def test_parse_headers():
    parser = Parser()
    parser.init()

    markdown_input = "# Header 1\n## Header 2\n### Header 3"
    expected_html_output = "<h1>Header 1</h1><h2>Header 2</h2><h3>Header 3</h3>"
    actual_html_output = parser.parse(markdown_input).replace("\n", "")
    assert actual_html_output == expected_html_output


def test_parse_emphasis():
    parser = Parser()
    parser.init()

    markdown_input = "*italic* **bold** `code`"
    expected_html_output = "<p><em>italic</em> <strong>bold</strong> <code>code</code></p>"
    actual_html_output = parser.parse(markdown_input).replace("\n", "")
    assert actual_html_output == expected_html_output


def test_parse_links():
    parser = Parser()
    parser.init()

    markdown_input = "[PYGPT](https://pygpt.net)"
    expected_html_output = '<p><a href="https://pygpt.net">PYGPT</a></p>'
    actual_html_output = parser.parse(markdown_input).replace("\n", "")
    assert actual_html_output == expected_html_output


def test_parse_code_blocks():
    parser = Parser()
    parser.init()

    markdown_input = "```\ndef example():\n    return 'example'\n```"
    expected_html_output = "<pre><code>def example():    return 'example'</code></pre>"
    actual_html_output = parser.parse(markdown_input).replace("\n", "")
    assert actual_html_output == expected_html_output


def test_parse_block_quotes():
    parser = Parser()
    parser.init()

    markdown_input = "> This is a block quote."
    expected_html_output = "<blockquote><p>This is a block quote.</p></blockquote>"
    actual_html_output = parser.parse(markdown_input).replace("\n", "")
    assert actual_html_output == expected_html_output


def test_parse_images():
    parser = Parser()
    parser.init()

    markdown_input = "![Alt text](/path/to/img.jpg)"
    expected_html_output = '<p><img alt="Alt text" src="/path/to/img.jpg"/></p>'
    actual_html_output = parser.parse(markdown_input).replace("\n", "")
    assert actual_html_output == expected_html_output