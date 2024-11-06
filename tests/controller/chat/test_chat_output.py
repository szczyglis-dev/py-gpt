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

from tests.mocks import mock_window
from pygpt_net.controller.chat.output import Output
from pygpt_net.item.ctx import CtxItem, CtxMeta


def test_handle(mock_window):
    """Test handle output"""
    output = Output(mock_window)
    output.handle_complete = MagicMock()

    ctx = CtxItem()
    meta = CtxMeta()
    ctx.meta = meta
    output.handle(ctx, 'chat', stream_mode=False)

    mock_window.core.dispatcher.dispatch.assert_called_once()  # should dispatch event: ctx.after
    mock_window.controller.chat.render.append_output.assert_called_once_with(meta, ctx)
    mock_window.controller.chat.render.append_extra.assert_called_once_with(meta, ctx, True)
    output.handle_complete.assert_called_once_with(ctx)


def test_handle_complete(mock_window):
    """Test handle complete"""
    output = Output(mock_window)
    mock_window.core.config.data['mode'] = 'chat'
    mock_window.core.config.data['store_history'] = True
    mock_window.core.ctx.post_update = MagicMock()
    mock_window.core.ctx.store = MagicMock()
    mock_window.controller.ctx.update_ctx = MagicMock()

    ctx = CtxItem()
    output.handle_complete(ctx)

    mock_window.core.ctx.post_update.assert_called_once()
    mock_window.core.ctx.store.assert_called_once()
    mock_window.controller.ctx.update_ctx.assert_called_once()
