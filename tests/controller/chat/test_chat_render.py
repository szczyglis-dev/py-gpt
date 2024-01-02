#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.chat.render import Render
from pygpt_net.item.ctx import CtxItem


def test_reset(mock_window):
    """Test reset render"""
    render = Render(mock_window)
    render.reset()
    assert render.images_appended == []
    assert render.urls_appended == []


def test_clear(mock_window):
    """Test clear render"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    render.clear()

    assert render.images_appended == []
    assert render.urls_appended == []
    render.get_output_node().clear.assert_called_once()


def test_clear_input(mock_window):
    """Test clear input"""
    render = Render(mock_window)
    render.get_input_node = MagicMock()
    render.clear_input()
    render.get_input_node().clear.assert_called_once()


def test_reload(mock_window):
    """Test reload render"""
    render = Render(mock_window)
    render.reset = MagicMock()
    mock_window.controller.ctx.refresh_output = MagicMock()
    render.reload()
    render.reset.assert_called_once()
    mock_window.controller.ctx.refresh_output.assert_called_once()


def test_end_of_stream(mock_window):
    """Test end of stream render"""
    render = Render(mock_window)
    render.end_of_stream()


def test_append_context(mock_window):
    """Test append context items"""
    render = Render(mock_window)
    render.append_context_item = MagicMock()
    item1 = CtxItem()
    item2 = CtxItem()
    item3 = CtxItem()
    mock_window.core.ctx = MagicMock()
    mock_window.core.ctx.items = [item1, item2, item3]
    render.append_context()
    render.append_context_item.assert_any_call(item1)
    render.append_context_item.assert_any_call(item2)
    render.append_context_item.assert_any_call(item3)


def test_replace_code_tags(mock_window):
    """Test replace code cmd tags"""
    render = Render(mock_window)
    text = "test ~###~test~###~ test"
    expected = "test <span class=\"cmd\">test</span> test"
    assert render.replace_code_tags(text) == expected


def test_pre_format_text(mock_window):
    """Test pre format text"""
    render = Render(mock_window)
    text = "test ~###~test~###~ test"
    expected = "test <span class=\"cmd\">test</span> test"
    assert render.pre_format_text(text) == expected


def test_post_format_text(mock_window):
    """Test post format text"""
    render = Render(mock_window)
    text = " test ~###~test~###~ test "
    expected = "test ~###~test~###~ test"
    assert render.post_format_text(text) == expected


def test_format_user_text(mock_window):
    """Test format user text"""
    render = Render(mock_window)
    text = " test ~###~test~###~ test "
    expected = "test ~###~test~###~ test"
    assert render.format_user_text(text) == expected


def test_format_chunk(mock_window):
    """Test format chunk"""
    render = Render(mock_window)
    text = " abc "
    expected = " abc "
    assert render.format_chunk(text) == expected


def test_append_block(mock_window):
    """Test append block"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_output_node().textCursor = MagicMock(return_value=cursor)
    render.append_block()
    render.get_output_node().textCursor.assert_called_once()
    cursor.movePosition.assert_called_once()


def test_to_end(mock_window):
    """Test to end"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_output_node().textCursor = MagicMock(return_value=cursor)
    render.to_end()
    render.get_output_node().textCursor.assert_called_once()
    cursor.movePosition.assert_called_once()


def test_append_raw(mock_window):
    """Test append raw"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    render.append_raw("test", "msg-bot")
    render.get_output_node().append.assert_called_once_with('<div class="msg-bot"><p>test</p></div>')


def test_append_chunk_start(mock_window):
    """Test append chunk start"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_output_node().textCursor = MagicMock(return_value=cursor)

    render.append_chunk_start()
    render.get_output_node().textCursor.assert_called_once()
    cursor.insertHtml.assert_called_once_with('<div class="msg-bot">&nbsp;</div>')
    cursor.movePosition.assert_called_once()
    render.get_output_node().setTextCursor.assert_called_once()


def test_append_context_item(mock_window):
    """Test append context item"""
    render = Render(mock_window)
    render.append_input = MagicMock()
    render.append_output = MagicMock()
    render.append_extra = MagicMock()
    item = CtxItem()
    render.append_context_item(item)
    render.append_input.assert_called_once_with(item)
    render.append_output.assert_called_once_with(item)
    render.append_extra.assert_called_once_with(item)


def test_append_input(mock_window):
    """Test append input"""
    render = Render(mock_window)
    render.append_raw = MagicMock()
    item = CtxItem()
    item.input = "test"
    render.append_input(item)
    render.append_raw.assert_called_once_with("test", "msg-user")


def test_append_output(mock_window):
    """Test append output"""
    render = Render(mock_window)
    render.append_raw = MagicMock()
    item = CtxItem()
    item.output = "test"
    render.append_output(item)
    render.append_raw.assert_called_once_with("test", "msg-bot")


def test_append_extra(mock_window):
    """Test append extra"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    render.images_appended = []
    item = CtxItem()
    item.images = ["test1"]
    item.files = ["test2"]
    item.urls = ["test3"]
    render.append_extra(item)
    render.get_output_node().append.assert_called()

    assert render.images_appended == ["test1"]
    assert render.urls_appended == ["test3"]


def test_append_chunk(mock_window):
    """Test append chunk"""
    render = Render(mock_window)
    render.append_chunk_start = MagicMock()
    render.append_block = MagicMock()
    item = CtxItem()
    render.append_chunk(item, "test", True)
    render.append_chunk_start.assert_called_once()
    render.append_block.assert_called_once()


def test_append(mock_window):
    """Test append"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_output_node().textCursor = MagicMock(return_value=cursor)
    render.append("test")
    render.get_output_node().textCursor.assert_called_once()


def test_append_text(mock_window):
    """Test append text"""
    render = Render(mock_window)
    render.get_input_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_input_node().textCursor = MagicMock(return_value=cursor)
    render.append_text("test")
    render.get_input_node().textCursor.assert_called_once()


def test_append_to_input(mock_window):
    """Test append to input"""
    render = Render(mock_window)
    render.get_input_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_input_node().textCursor = MagicMock(return_value=cursor)
    render.append_to_input("test")
    cursor.insertText.assert_called_once_with("test")
    render.get_input_node().textCursor.assert_called_once()


def test_is_timestamp_enabled(mock_window):
    """Test is timestamp enabled"""
    render = Render(mock_window)
    mock_window.core.config.data['output_timestamp'] = True
    assert render.is_timestamp_enabled() is True


def test_get_output_node(mock_window):
    """Test get output node"""
    render = Render(mock_window)
    mock_window.ui.nodes['output'] = MagicMock()
    assert render.get_output_node() ==  mock_window.ui.nodes['output']


def test_get_input_node(mock_window):
    """Test get input node"""
    render = Render(mock_window)
    mock_window.ui.nodes['input'] = MagicMock()
    assert render.get_input_node() ==  mock_window.ui.nodes['input']
