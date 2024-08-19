#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.19 23:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.prompt import Prompt


def test_build_final_system_prompt(mock_window):
    prompt = Prompt(mock_window)
    prompt.window.core.config = {
        'cmd': True,
        'func_call.native': False,
    }
    prompt.window.core.command.is_native_enabled = MagicMock(return_value=False)
    prompt.window.core.command.get_prompt = MagicMock(return_value='cmd_prompt')
    prompt.window.core.command.append_syntax = MagicMock(return_value='cmd_syntax')
    prompt.window.core.dispatcher.dispatch = MagicMock()

    result = prompt.build_final_system_prompt('prompt')
    assert result == 'cmd_syntax'
    prompt.window.core.command.append_syntax.assert_called_once()
    prompt.window.core.dispatcher.dispatch.assert_called()
