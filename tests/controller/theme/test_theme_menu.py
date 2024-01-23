#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_update_list(mock_window):
    """Test update list"""
    theme = Theme(mock_window)
    mock_window.core.config.data['theme'] = 'test'
    mock_window.ui.menu = {'theme': {'test': MagicMock()}}
    theme.menu.update_list()
    theme.window.ui.menu['theme']['test'].setChecked.assert_called()
