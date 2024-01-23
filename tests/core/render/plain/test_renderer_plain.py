#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch
import platform

from tests.mocks import mock_window
from pygpt_net.core.render.plain.renderer import Renderer as Render
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.filesystem import Filesystem


def test_reset(mock_window):
    """Test reset render"""
    render = Render(mock_window)
    render.reset()
    assert render.images_appended == []
    assert render.urls_appended == []


def test_clear_output(mock_window):
    """Test clear render"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    render.clear_output()

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
    mock_window.controller.ctx.refresh_output = MagicMock()
    render.reload()
    mock_window.controller.ctx.refresh_output.assert_called_once()


def test_append_context(mock_window):
    """Test append context items"""
    render = Render(mock_window)
    render.append_context_item = MagicMock()
    item1 = CtxItem()
    item2 = CtxItem()
    item3 = CtxItem()
    items = [item1, item2, item3]
    render.append_context(items)
    render.append_context_item.assert_any_call(item1)
    render.append_context_item.assert_any_call(item2)
    render.append_context_item.assert_any_call(item3)


def test_append_input(mock_window):
    """Test append input"""
    render = Render(mock_window)
    render.append_raw = MagicMock()
    item = CtxItem()
    item.input = "test"
    render.append_input(item)
    render.append_raw.assert_called_once_with("> test")


def test_append_output(mock_window):
    """Test append output"""
    render = Render(mock_window)
    render.append_raw = MagicMock()
    item = CtxItem()
    item.output = "test"
    render.append_output(item)
    render.append_raw.assert_called_once_with("test")


def test_append_extra(mock_window):
    """Test append extra"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    render.append_raw = MagicMock()
    mock_window.core.filesystem = Filesystem(mock_window)
    render.images_appended = []
    item = CtxItem()
    item.images = ["test1"]
    item.files = ["test2"]
    item.urls = ["test3"]
    render.append_extra(item)
    render.append_raw.assert_called()

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
    render.append_raw("test")
    render.get_output_node().setText.assert_called_once()


def test_append_chunk_start(mock_window):
    """Test append chunk start"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_output_node().textCursor = MagicMock(return_value=cursor)

    render.append_chunk_start()
    render.get_output_node().textCursor.assert_called_once()
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


def test_get_image_html(mock_window):
    """Test get image html"""
    mock_window.core.config.set("lang", "en")
    mock_window.core.filesystem = Filesystem(mock_window)
    work_dir = mock_window.core.config.get_user_path()
    url = "%workdir%/test.png"
    render = Render(mock_window)
    html = render.get_image_html(url)
    if platform.system() == 'Windows':
        assert html == \
               '\nImage: ' + work_dir + '\\test.png\n'
    else:
        assert html == \
               '\nImage: ' + work_dir + '/test.png\n'


def test_get_url_html(mock_window):
    """Test get url html"""
    mock_window.core.config.set("lang", "en")
    mock_window.core.filesystem = Filesystem(mock_window)
    url = "https://google.com"
    render = Render(mock_window)
    html = render.get_file_html(url)
    assert html == '\nFile: https://google.com\n'


def test_get_file_html(mock_window):
    """Test get file html"""
    mock_window.core.filesystem = Filesystem(mock_window)
    work_dir = mock_window.core.config.get_user_path()
    url = "%workdir%/test.txt"
    render = Render(mock_window)
    html = render.get_file_html(url)
    if platform.system() == 'Windows':
        assert html == \
               '\nFile: ' + work_dir + '\\test.txt\n'
    else:
        assert html == \
               '\nFile: ' + work_dir + '/test.txt\n'


def test_append(mock_window):
    """Test append"""
    render = Render(mock_window)
    render.get_output_node = MagicMock()
    cursor = MagicMock()
    cursor.movePosition = MagicMock()
    render.get_output_node().textCursor = MagicMock(return_value=cursor)
    render.append("test")
    render.get_output_node().textCursor.assert_called_once()


def test_append_timestamp(mock_window):
    """Test append timestamp"""
    render = Render(mock_window)
    render.is_timestamp_enabled = MagicMock(return_value=True)
    text = "test ~###~test~###~ test"
    ctx = CtxItem()
    ctx.input_timestamp = 1234567890
    assert render.append_timestamp(text, ctx).startswith("00:31:30: test") is True


def test_pre_format_text(mock_window):
    """Test pre format text"""
    render = Render(mock_window)
    text = "test ~###~test~###~ test"
    expected = "test ~###~test~###~ test"
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
    expected = " test ~###~test~###~ test "  # no strip here
    assert render.format_user_text(text) == expected


def test_format_chunk(mock_window):
    """Test format chunk"""
    render = Render(mock_window)
    text = " abc "
    expected = " abc "
    assert render.format_chunk(text) == expected


def test_is_timestamp_enabled(mock_window):
    """Test is timestamp enabled"""
    render = Render(mock_window)
    mock_window.core.config.data['output_timestamp'] = True
    assert render.is_timestamp_enabled() is True


def test_get_output_node(mock_window):
    """Test get output node"""
    render = Render(mock_window)
    mock_window.ui.nodes['output'] = MagicMock()
    assert render.get_output_node() == mock_window.ui.nodes['output']


def test_get_input_node(mock_window):
    """Test get input node"""
    render = Render(mock_window)
    mock_window.ui.nodes['input'] = MagicMock()
    assert render.get_input_node() == mock_window.ui.nodes['input']
