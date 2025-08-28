#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.plugin.openai_vision import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "prompt" in options
    assert "replace_prompt" in options
    assert "model" in options


def test_handle_ui_vision(mock_window):
    """Test handle event: ui.vision"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.vision.allowed_modes = ["chat"]
    ctx = CtxItem()
    event = Event()
    event.name = "ui.vision"
    event.data = {
        "mode": "chat",
        "value": False,
    }
    event.ctx = ctx
    plugin.handle(event)
    assert event.data["value"] is True


def test_handle_ui_attachments(mock_window):
    """Test handle event: ui.attachments"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.vision.allowed_modes = ["chat"]
    ctx = CtxItem()
    event = Event()
    event.name = "ui.attachments"
    event.data = {
        "mode": "chat",
        "value": False,
    }
    event.ctx = ctx
    plugin.handle(event)
    assert event.data["value"] is True


def test_handle_pre_prompt(mock_window):
    """Test handle event: pre.prompt"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.is_vision_provided = MagicMock(return_value=True)
    mock_window.controller.chat.vision.enabled = MagicMock(return_value=True)
    mock_window.controller.chat.vision.allowed_modes = ["chat"]
    ctx = CtxItem()
    event = Event()
    event.name = "pre.prompt"
    event.data = {
        "mode": "chat",
        "value": "prev prompt",
    }
    event.ctx = ctx
    plugin.options["prompt"]["value"] = "new prompt"
    plugin.options["replace_prompt"]["value"] = True
    plugin.handle(event)
    assert event.data["value"] == "new prompt"




def test_handle_ctx_select(mock_window):
    """Test handle events: ctx.select"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.vision = MagicMock()
    mock_window.controller.chat.vision.is_enabled = True
    ctx = CtxItem()
    event = Event()
    event.name = "ctx.select"
    event.data = {
        "value": False,
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.controller.chat.vision.is_enabled = False


def test_handle_mode_select(mock_window):
    """Test handle events: mode.select"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.vision = MagicMock()
    mock_window.controller.chat.vision.is_enabled = True
    ctx = CtxItem()
    event = Event()
    event.name = "mode.select"
    event.data = {
        "value": False,
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.controller.chat.vision.is_enabled = False


def test_handle_model_select(mock_window):
    """Test handle events: model.select"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.vision = MagicMock()
    mock_window.controller.chat.vision.is_enabled = True
    ctx = CtxItem()
    event = Event()
    event.name = "model.select"
    event.data = {
        "value": False,
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.controller.chat.vision.is_enabled = False


def test_is_vision_provided(mock_window):
    """Test is vision provided"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    mock_window.core.config.data['mode'] = "chat"

    mock_window.core.api.openai.vision = MagicMock()

    # no attachments
    mock_window.core.api.openai.vision.attachments = []
    assert plugin.is_vision_provided() is False

    # no images in URLs
    mock_window.core.api.openai.vision.urls = []
    assert plugin.is_vision_provided() is False

    # images in URLs
    mock_window.core.api.openai.vision.attachments = []
    mock_window.core.api.openai.vision.urls = ["https://example.com/image.jpg"]
    assert plugin.is_vision_provided() is True

    # images in attachments
    mock_window.core.api.openai.vision.urls = []
    mock_window.core.api.openai.vision.attachments = ["attachment.jpg"]
    assert plugin.is_vision_provided() is True

    # images in both
    mock_window.core.api.openai.vision.urls = ["https://example.com/image.jpg"]
    mock_window.core.api.openai.vision.attachments = ["attachment.jpg"]
    assert plugin.is_vision_provided() is True
