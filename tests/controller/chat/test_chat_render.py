#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.chat.render import Render


def _render_with_active_renderer(mock_window):
    render = Render(mock_window)
    active = MagicMock()
    render.renderer = active
    return render, active


def test_get_renderers(mock_window):
    """Only the supported plain-text and WebEngine renderers are created."""
    render = Render(mock_window)
    assert render.web_renderer is not None
    assert render.plaintext_renderer is not None
    assert not hasattr(render, "markdown_renderer")


def test_setup_selects_plaintext_or_web_renderer(mock_window):
    render = Render(mock_window)

    mock_window.core.config.set("render.plain", True)
    render.setup()
    assert render.renderer is render.plaintext_renderer

    mock_window.core.config.set("render.plain", False)
    render.setup()
    assert render.renderer is render.web_renderer


def test_begin(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    meta = MagicMock()
    ctx = MagicMock()

    render.begin(meta, ctx)

    mock_window.core.ctx.output.pin_render_pid.assert_called_once_with(meta)
    active.begin.assert_called_once_with(meta, ctx, False)


def test_end(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    meta = MagicMock()
    ctx = MagicMock()

    render.end(meta, ctx)

    active.end.assert_called_once_with(meta, ctx, False)


def test_stream_begin(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    meta = MagicMock()
    ctx = MagicMock()
    render.stream_begin(meta, ctx)
    active.stream_begin.assert_called_once_with(meta, ctx)


def test_stream_end(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    meta = MagicMock()
    ctx = MagicMock()
    render.stream_end(meta, ctx)
    active.stream_end.assert_called_once_with(meta, ctx)


def test_clear_output(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    render.clear_output()
    active.clear_output.assert_called_once_with(None)


def test_clear_input(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    render.clear_input()
    active.clear_input.assert_called_once_with()


def test_reset(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    render.reset()
    active.reset.assert_called_once_with(None)


def test_reload(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    render.reload()
    active.reload.assert_called_once_with(None)


def test_append_context(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    ctx = CtxItem()
    meta = MagicMock()
    items = [ctx]
    render.append_context(meta, items)
    active.append_context.assert_called_once_with(meta, items, True)


def test_append_input(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    ctx = CtxItem()
    meta = MagicMock()
    render.append_input(meta, ctx)
    active.append_input.assert_called_once_with(meta, ctx, flush=True, append=False)


def test_append_output(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    ctx = CtxItem()
    meta = MagicMock()
    render.append_output(meta, ctx)
    active.append_output.assert_called_once_with(meta, ctx)


def test_append_extra(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    ctx = CtxItem()
    meta = MagicMock()
    render.append_extra(meta, ctx)
    active.append_extra.assert_called_once_with(meta, ctx, False)


def test_append_chunk(mock_window):
    render, active = _render_with_active_renderer(mock_window)
    ctx = CtxItem()
    meta = MagicMock()
    render.append_chunk(meta, ctx, "test")
    active.append_chunk.assert_called_once_with(meta, ctx, "test", False)
