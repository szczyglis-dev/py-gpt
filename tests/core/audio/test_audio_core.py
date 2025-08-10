#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.14 00:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.audio import Audio


def test_clean_text():
    """Test clean text"""
    audio = Audio()
    text = 'speak this<tool>>ignore this</tool> only'
    res = audio.clean_text(text)
    assert res == 'speak this only'
