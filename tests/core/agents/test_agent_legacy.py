#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.12 21:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.core.agents.legacy import Legacy


def test_get_idx_default_none():
    window = MagicMock()
    window.core.config.get.return_value = None
    legacy = Legacy(window)

    assert legacy.get_idx() is None
    window.core.config.get.assert_called_once_with("agent.idx")


def test_get_idx():
    window = MagicMock()
    window.core.config.get.return_value = "agent123"
    legacy = Legacy(window)

    assert legacy.get_idx() == "agent123"
    window.core.config.get.assert_called_once_with("agent.idx")
