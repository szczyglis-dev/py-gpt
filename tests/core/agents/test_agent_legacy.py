#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from pygpt_net.core.agents.legacy import Legacy
from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_VISION,
    MODE_LLAMA_INDEX,
    MODE_AUDIO,
    MODE_RESEARCH,
)

def test_get_allowed_modes():
    # Check allowed modes list
    legacy = Legacy()
    expected = [MODE_CHAT, MODE_COMPLETION, MODE_LLAMA_INDEX, MODE_AUDIO, MODE_RESEARCH]
    assert legacy.get_allowed_modes() == expected

def test_get_mode_default():
    # When no mode is set, should return MODE_CHAT
    window = MagicMock()
    window.core.config.get.return_value = None
    legacy = Legacy(window)
    assert legacy.get_mode() == MODE_CHAT

def test_get_mode_valid():
    # When a valid mode is set, it should return that mode
    window = MagicMock()
    window.core.config.get.side_effect = lambda key: MODE_VISION if key == "agent.mode" else None
    legacy = Legacy(window)
    assert legacy.get_mode() == MODE_CHAT

def test_get_mode_invalid():
    # When an invalid mode is set, should return MODE_CHAT as default
    window = MagicMock()
    window.core.config.get.side_effect = lambda key: "invalid_mode" if key == "agent.mode" else None
    legacy = Legacy(window)
    assert legacy.get_mode() == MODE_CHAT

def test_get_idx():
    # Check agent index retrieval
    window = MagicMock()
    window.core.config.get.side_effect = lambda key: "agent123" if key == "agent.idx" else None
    legacy = Legacy(window)
    assert legacy.get_idx() == "agent123"