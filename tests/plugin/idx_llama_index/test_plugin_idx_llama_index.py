#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

from pygpt_net.plugin.idx_llama_index import Plugin
from tests.mocks import mock_window


def test_project_index_option_defaults_to_enabled(mock_window):
    plugin = Plugin(window=mock_window)

    assert plugin.get_option_value("use_project_index") is True


def test_get_effective_idx_prefers_current_project(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("use_project_index", True)
    plugin.set_option_value("idx", "base,docs")
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value="__project__")

    assert plugin.get_effective_idx() == "__project__"


def test_get_effective_idx_falls_back_to_global_indexes_outside_project(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("use_project_index", True)
    plugin.set_option_value("idx", "base,docs")
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value=None)

    assert plugin.get_effective_idx() == "base,docs"


def test_get_effective_idx_explicit_index_has_priority(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("use_project_index", True)
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value="__project__")

    assert plugin.get_effective_idx("manual") == "manual"
    mock_window.core.idx.get_current_project_idx.assert_not_called()


def test_retrieval_uses_project_virtual_index(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("use_project_index", True)
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value="__project__")
    mock_window.core.idx.chat.query_retrieval = MagicMock(return_value="context")

    assert plugin.get_from_retrieval("query") == "context"
    mock_window.core.idx.chat.query_retrieval.assert_called_once_with("query", "__project__")
