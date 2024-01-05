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

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.chat.render import Render


def test_get_renderer(mock_window):
    """Test get renderer"""
    render = Render(mock_window)
    assert render.renderer is not None


def test_begin(mock_window):
    """Test begin render"""
    render = Render(mock_window)
    render.renderer.begin = MagicMock()
    render.begin()
    render.renderer.begin.assert_called_once()


def test_end(mock_window):
    """Test end render"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.end()
    render.renderer.end.assert_called_once()


def test_stream_begin(mock_window):
    """Test stream begin render"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.stream_begin()
    render.renderer.stream_begin.assert_called_once()


def test_stream_end(mock_window):
    """Test stream end render"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.stream_end()
    render.renderer.stream_end.assert_called_once()


def test_clear_output(mock_window):
    """Test clear render"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.clear_output()
    render.renderer.clear_output.assert_called_once()


def test_clear_input(mock_window):
    """Test clear input"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.clear_input()
    render.renderer.clear_input.assert_called_once()


def test_reset(mock_window):
    """Test reset render"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.reset()
    render.renderer.reset.assert_called_once()


def test_reload(mock_window):
    """Test reload render"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.reload()
    render.renderer.reload.assert_called_once()


def test_append_context(mock_window):
    """Test append context items"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    ctx = CtxItem()
    items = [ctx]
    render.append_context(items)
    render.renderer.append_context.assert_called_once()


def test_append_input(mock_window):
    """Test append input"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    ctx = CtxItem()
    render.append_input(ctx)
    render.renderer.append_input.assert_called_once()


def test_append_output(mock_window):
    """Test append output"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    ctx = CtxItem()
    render.append_output(ctx)
    render.renderer.append_output.assert_called_once()


def test_append_extra(mock_window):
    """Test append extra"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    ctx = CtxItem()
    render.append_extra(ctx)
    render.renderer.append_extra.assert_called_once()


def test_append_chunk(mock_window):
    """Test append chunk"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    ctx = CtxItem()
    render.append_chunk(ctx, "test")
    render.renderer.append_chunk.assert_called_once()


def test_append_text(mock_window):
    """Test append text"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.append_text("test")
    render.renderer.append_text.assert_called_once()


def test_append_to_input(mock_window):
    """Test append to input"""
    render = Render(mock_window)
    render.renderer = MagicMock()
    render.append_to_input("test")
    render.renderer.append_to_input.assert_called_once()
