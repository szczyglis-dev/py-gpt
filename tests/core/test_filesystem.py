#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 19:00:00                  #
# ================================================== #

import os
import platform
from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.filesystem import Filesystem


def test_install(mock_window):
    """Test install"""
    filesystem = Filesystem(mock_window)
    os.path.exists = MagicMock(return_value=False)
    os.mkdir = MagicMock()
    filesystem.install()
    os.path.exists.assert_called()
    os.mkdir.assert_called()


def test_make_local(mock_window):
    """Test make local"""
    filesystem = Filesystem(mock_window)
    filesystem.window.core.config.path = 'test_dir'

    path = filesystem.make_local('test_dir/test_file')
    assert path == '%workdir%/test_file'

    filesystem.window.core.config.path = 'C:\\test_dir'
    path = filesystem.make_local('C:\\test_dir\\test_file')
    assert path == '%workdir%\\test_file'

    filesystem.window.core.config.path = 'test_dir'
    path = filesystem.make_local('test_file')
    assert path == 'test_file'


def test_make_local_list(mock_window):
    """Test make local list"""
    filesystem = Filesystem(mock_window)
    filesystem.window.core.config.path = 'test_dir'

    file_list = ['test_dir/test_file', 'test_dir/test_file2']

    new_list = filesystem.make_local_list(file_list)
    assert new_list == ['%workdir%/test_file', '%workdir%/test_file2']


def test_get_url(mock_window):
    """Test get url"""
    filesystem = Filesystem(mock_window)
    filesystem.window.core.config.path = 'test_dir'

    mock_window.core.platforms.is_windows = MagicMock(return_value=False)
    url = filesystem.get_url('/home/test_dir/test_file')
    assert url.toString() == 'file:///home/test_dir/test_file'

    mock_window.core.platforms.is_windows = MagicMock(return_value=True)
    url = filesystem.get_url('C:\\test_dir\\test_file')
    assert url.toString() == 'file:///C:%5Ctest_dir%5Ctest_file'

    mock_window.core.platforms.is_windows = MagicMock(return_value=True)
    url = filesystem.get_url('file:///C:\\test_dir\\test_file')
    assert url.toString() == 'file:///C:%5Ctest_dir%5Ctest_file'


def test_get_path(mock_window):
    """Test get path"""
    filesystem = Filesystem(mock_window)
    filesystem.window.core.config.path = 'test_dir'

    if platform.system() == 'Windows':
        path = filesystem.get_path('C:\\test_dir\\test_file')
        assert path == 'C:\\test_dir\\test_file'
    else:
        path = filesystem.get_path('/home/test_dir/test_file')
        assert path == '/home/test_dir/test_file'


def test_to_workdir(mock_window):
    """Test to workdir"""
    filesystem = Filesystem(mock_window)

    if platform.system() == 'Windows':
        filesystem.window.core.config.path = 'C:\\Users\\new_user\\.config\\pygpt-net'
        mock_window.core.platforms.is_windows = MagicMock(return_value=True)
        path = filesystem.to_workdir('C:\\Users\\old_user\\.config\\pygpt-net\\data\\test_file')
        assert path == 'C:\\Users\\new_user\\.config\\pygpt-net\\data\\test_file'
    else:
        filesystem.window.core.config.path = '/home/new_user/.config/pygpt-net'
        mock_window.core.platforms.is_windows = MagicMock(return_value=False)
        path = filesystem.to_workdir('/home/old_user/.config/pygpt-net/data/test_file')
        assert path == '/home/new_user/.config/pygpt-net/data/test_file'


def test_extract_local_url(mock_window):
    """Test extract local url"""
    filesystem = Filesystem(mock_window)
    if platform.system() == 'Windows':
        filesystem.window.core.config.path = 'C:\\Users\\new_user\\.config\\pygpt-net'
        mock_window.core.platforms.is_windows = MagicMock(return_value=True)
        url, path = filesystem.extract_local_url('C:\\Users\\old_user\\.config\\pygpt-net\\data\\test_file')
        assert url == 'file:///C:\\Users\\new_user\\.config\\pygpt-net\\data\\test_file'
        assert path == 'C:\\Users\\new_user\\.config\\pygpt-net\\data\\test_file'
    else:
        filesystem.window.core.config.path = '/home/new_user/.config/pygpt-net'
        mock_window.core.platforms.is_windows = MagicMock(return_value=False)
        url, path = filesystem.extract_local_url('/home/old_user/.config/pygpt-net/data/test_file')
        assert url == 'file:///home/new_user/.config/pygpt-net/data/test_file'
        assert path == '/home/new_user/.config/pygpt-net/data/test_file'


def test_extract_local_url_none(mock_window):
    """Test extract local url"""
    filesystem = Filesystem(mock_window)
    mock_window.core.platforms.is_windows = MagicMock(return_value=False)
    filesystem.window.core.config.path = '/home/user/.config/pygpt-net'

    url, path = filesystem.extract_local_url('http://www.google.com/file.png')
    assert url == 'http://www.google.com/file.png'
    assert path == 'http://www.google.com/file.png'

    url, path = filesystem.extract_local_url('file://file.png')
    assert url == 'file://file.png'
    assert path == 'file://file.png'

    mock_window.core.platforms.is_windows = MagicMock(return_value=True)
    url, path = filesystem.extract_local_url('file:///file.png')
    assert url == 'file:///file.png'
    assert path == 'file:///file.png'


def test_is_schema(mock_window):
    """Test is schema"""
    filesystem = Filesystem(mock_window)
    result = filesystem.is_schema('file:///test_file')
    assert result is True

    result = filesystem.is_schema('http://www.google.com/test_file')
    assert result is True

    result = filesystem.is_schema('https://www.google.com/test_file')
    assert result is True

    result = filesystem.is_schema('test_file')
    assert result is False


