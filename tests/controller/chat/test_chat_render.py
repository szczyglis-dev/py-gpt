#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.chat.render import Render


def test_get_renderer(mock_window):
    """Test get renderer"""
    render = Render(mock_window)
    assert render.web_renderer is not None
    assert render.markdown_renderer is not None


def test_begin(mock_window):
    """Test begin render"""
    render = Render(mock_window)
    render.web_renderer.begin = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.begin(meta, ctx)
    render.markdown_renderer.begin.assert_called_once()


def test_end(mock_window):
    """Test end render"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.end(meta, ctx)
    render.markdown_renderer.end.assert_called_once()


def test_stream_begin(mock_window):
    """Test stream begin render"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.stream_begin(meta, ctx)
    render.markdown_renderer.stream_begin.assert_called_once()


def test_stream_end(mock_window):
    """Test stream end render"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.stream_end(meta, ctx)
    render.markdown_renderer.stream_end.assert_called_once()


def test_clear_output(mock_window):
    """Test clear render"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.clear_output()
    render.markdown_renderer.clear_output.assert_called_once()


def test_clear_input(mock_window):
    """Test clear input"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.clear_input()
    render.markdown_renderer.clear_input.assert_called_once()


def test_reset(mock_window):
    """Test reset render"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.reset()
    render.markdown_renderer.reset.assert_called_once()


def test_reload(mock_window):
    """Test reload render"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    meta = MagicMock()
    ctx = MagicMock()
    render.reload()
    render.markdown_renderer.reload.assert_called_once()


def test_append_context(mock_window):
    """Test append context items"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    ctx = CtxItem()
    meta = MagicMock()
    items = [ctx]
    render.append_context(meta, items)
    render.markdown_renderer.append_context.assert_called_once()


def test_append_input(mock_window):
    """Test append input"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    ctx = CtxItem()
    meta = MagicMock()
    render.append_input(meta, ctx)
    render.markdown_renderer.append_input.assert_called_once()


def test_append_output(mock_window):
    """Test append output"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    ctx = CtxItem()
    meta = MagicMock()
    render.append_output(meta, ctx)
    render.markdown_renderer.append_output.assert_called_once()


def test_append_extra(mock_window):
    """Test append extra"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    ctx = CtxItem()
    meta = MagicMock()
    render.append_extra(meta, ctx)
    render.markdown_renderer.append_extra.assert_called_once()


def test_append_chunk(mock_window):
    """Test append chunk"""
    render = Render(mock_window)
    render.web_renderer = MagicMock()
    render.markdown_renderer = MagicMock()
    ctx = CtxItem()
    meta = MagicMock()
    render.append_chunk(meta, ctx, "test")
    render.markdown_renderer.append_chunk.assert_called_once()
