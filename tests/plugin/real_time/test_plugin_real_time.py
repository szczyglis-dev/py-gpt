#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 05:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.real_time import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "hour" in options
    assert "date" in options
    assert "tpl" in options


def test_handle_system_prompt(mock_window):
    """Test handle event: system.prompt"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "system.prompt"
    event.data = {
        "value": "prev prompt"
    }
    event.ctx = ctx
    plugin.options["hour"]["value"] = True
    plugin.options["date"]["value"] = True
    plugin.options["tpl"]["value"] = "Current time is PLACEHOLDER_HERE"
    plugin.handle(event)
    assert event.data["value"] == "prev prompt\n\nCurrent time is PLACEHOLDER_HERE"

