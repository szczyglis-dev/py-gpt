#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, call, patch

import PySide6

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller import Files


def test_delete(mock_window, monkeypatch):
    """Test delete"""
    files = Files(mock_window)
    remove_mock = MagicMock()
    monkeypatch.setattr(os, 'remove', remove_mock)

    files.delete('test', force=True)
    remove_mock.assert_called_once_with('test')


def test_rename(mock_window):
    """Test rename"""
    files = Files(mock_window)
    mock_window.ui.dialog['rename'] = MagicMock()
    files.rename('test')
    assert mock_window.ui.dialog['rename'].id == 'output_file'
    assert mock_window.ui.dialog['rename'].current == 'test'


def test_update_name(mock_window, monkeypatch):
    """Test update name"""
    files = Files(mock_window)
    rename_mock = MagicMock()
    monkeypatch.setattr(os, 'rename', rename_mock)
    monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
    mock_window.update_status = MagicMock()
    files.update_name('test', 'test2')
    rename_mock.assert_called_once_with('test', os.path.join(os.path.dirname('test'), 'test2'))
    mock_window.ui.dialog['rename'].close.assert_called_once_with()


def test_open_dir(mock_window):
    """Test open dir"""
    files = Files(mock_window)
    files.open_in_file_manager = MagicMock()
    files.open_dir('test')
    files.open_in_file_manager.assert_called_once_with('test', False)


def test_open(mock_window, monkeypatch):
    """Test open"""
    files = Files(mock_window)
    mock_window.core.platforms.is_snap = MagicMock(return_value=False)
    open_url_mock = MagicMock()
    monkeypatch.setattr(PySide6.QtGui.QDesktopServices, "openUrl", open_url_mock)
    files.open('test')
    open_url_mock.assert_called_once()


def test_open_in_file_manager(mock_window):
    """Test open in file manager"""
    files = Files(mock_window)
    files.open_in_file_manager = MagicMock()
    files.open_dir('test')
    files.open_in_file_manager.assert_called_once_with('test', False)
