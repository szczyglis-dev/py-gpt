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




def test_append_tabs_contains_auto_update_and_clear_truncate(mock_window):
    settings = Settings(mock_window)

    assert settings.append_tabs() == ["update", "clear_truncate"]


def test_truncate_selected_opens_destructive_confirmation(mock_window):
    settings = Settings(mock_window)
    combo = MagicMock()
    combo.count.return_value = 1
    combo.currentData.return_value = "base"
    mock_window.ui.nodes = {"idx.settings.truncate.combo": combo}
    mock_window.ui.dialogs.confirm = MagicMock()

    settings.truncate_selected()

    kwargs = mock_window.ui.dialogs.confirm.call_args.kwargs
    assert kwargs["type"] == "idx.settings.truncate"
    assert kwargs["id"] == "base"
    assert "base" in kwargs["msg"]
