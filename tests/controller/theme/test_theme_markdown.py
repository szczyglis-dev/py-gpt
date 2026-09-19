#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 19:20:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.controller import Theme
from pygpt_net.core.events import RenderEvent


def _configure_theme(mock_window, theme="light", style="standard"):
    def config_get(key, default=None):
        return {
            "theme": theme,
            "theme.style": style,
        }.get(key, default)

    mock_window.core.config.get = MagicMock(side_effect=config_get)


def _create_theme(mock_window, theme="light", style="standard"):
    _configure_theme(mock_window, theme=theme, style=style)
    controller = Theme(mock_window)
    # Markdown intentionally resolves Common through the active theme
    # controller, just like it does in the real application.
    mock_window.controller.theme = controller
    return controller


def test_update(mock_window):
    """Test renderer style update."""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.markdown.load = MagicMock()
    theme.markdown.apply = MagicMock()

    theme.markdown.update(force=True)

    theme.window.controller.ui.store_state.assert_called_once_with()
    theme.markdown.load.assert_called_once_with()
    theme.markdown.apply.assert_called_once_with()
    theme.window.controller.ui.restore_state.assert_called_once_with()


def test_get_legacy_css(mock_window):
    """Legacy renderer CSS is generated in Python; markdown*.css assets are no longer used."""
    theme = _create_theme(mock_window, theme="light")

    css = theme.markdown.get_legacy_css()

    assert ".msg-user" in css
    assert "#e9e9e9" in css
    assert "markdown.css" not in css


def test_apply(mock_window):
    """Apply generated legacy CSS and notify the current renderer about a theme change."""
    theme = _create_theme(mock_window, theme="light")
    output = MagicMock()
    mock_window.ui.nodes = {"output": {1: output}}

    theme.markdown.apply()

    output.setStyleSheet.assert_called_once()
    css = output.setStyleSheet.call_args.args[0]
    assert ".msg-bot" in css
    events = [args[0] for args, _ in mock_window.dispatch.call_args_list if args]
    assert any(
        isinstance(event, RenderEvent) and event.name == RenderEvent.ON_THEME_CHANGE
        for event in events
    )


def test_load(mock_window):
    """Load the standard WebEngine CSS base plus the active color theme."""
    theme = _create_theme(mock_window, theme="light", style="standard")
    theme.common.normalize_theme = MagicMock(return_value="light")
    theme.common.normalize_style = MagicMock(return_value="standard")
    theme.common.get_theme_asset_paths = MagicMock(
        return_value=["chat.css", "light/chat.css"]
    )

    with patch("builtins.open", mock_open(read_data="test")) as mock_file:
        theme.markdown.load()

    assert theme.markdown.css["web"] == "testtest"
    assert theme.markdown.web_style == "standard"
    theme.common.get_theme_asset_paths.assert_called_once_with("light", "chat.css")
    assert mock_file.call_count == 2


def test_load_wide_appends_width_override(mock_window):
    """Wide style reuses standard CSS and appends only the width override."""
    theme = _create_theme(mock_window, theme="ocean", style="wide")
    theme.common.normalize_theme = MagicMock(return_value="ocean")
    theme.common.normalize_style = MagicMock(return_value="wide")
    theme.common.get_theme_asset_paths = MagicMock(
        return_value=["chat.css", "ocean/chat.css"]
    )
    theme.common.get_global_asset_paths = MagicMock(
        return_value=["chat.wide.css"]
    )

    with patch("builtins.open", mock_open(read_data="x")) as mock_file:
        theme.markdown.load()

    assert theme.markdown.css["web"] == "xxx"
    assert theme.markdown.web_style == "wide"
    theme.common.get_theme_asset_paths.assert_called_once_with("ocean", "chat.css")
    theme.common.get_global_asset_paths.assert_called_once_with("chat.wide.css")
    assert mock_file.call_count == 3
