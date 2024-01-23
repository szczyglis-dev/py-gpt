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

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.idx.settings import Settings


def test_update_text_last_updated(mock_window):
    """Test update text last updated"""
    settings = Settings(mock_window)
    mock_window.ui.nodes['idx.db.last_updated'].setText = MagicMock()
    mock_window.core.config.set("llama.idx.db.last", 1234567)
    settings.update_text_last_updated()
    mock_window.ui.nodes['idx.db.last_updated'].setText.assert_called_once()


