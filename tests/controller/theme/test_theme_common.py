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

from unittest.mock import patch

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_get_theme_asset_paths(mock_window, tmp_path):
    """Theme CSS is resolved from global, bundled and profile layers."""
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    (builtin / "dark").mkdir(parents=True)
    (user / "dark").mkdir(parents=True)

    expected = [
        builtin / "app.css",
        builtin / "dark" / "app.css",
        user / "app.css",
        user / "dark" / "app.css",
    ]
    for path in expected:
        path.write_text("test", encoding="utf-8")

    theme = Theme(mock_window)
    with patch.object(theme.common, "get_builtin_css_dir", return_value=str(builtin)), \
            patch.object(theme.common, "get_user_css_dir", return_value=str(user)):
        paths = theme.common.get_theme_asset_paths("dark_teal", "app.css")

    assert paths == [str(path) for path in expected]


def test_translate(mock_window):
    name = 'dark_teal'
    theme = Theme(mock_window)
    mock_window.core.config.data['lang'] = 'en'
    assert theme.common.translate(name) == 'Dark'  # must have EN lang in config to pass!!!!!!!!


def test_get_themes_list(mock_window):
    theme = Theme(mock_window)
    assert type(theme.common.get_themes_list()) == list
