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
from pygpt_net.tools.files import Files


def test_delete(mock_window, monkeypatch):
    """Test delete"""
    files = _tool(mock_window)
    remove_mock = MagicMock()
    monkeypatch.setattr(os, 'remove', remove_mock)

    files.operations.delete('test', force=True)
    remove_mock.assert_called_once_with('test')


def test_rename(mock_window):
    """Test rename"""
    files = _tool(mock_window)
    mock_window.ui.dialog['rename'] = MagicMock()
    files.operations.rename('test')
    assert mock_window.ui.dialog['rename'].id == 'output_file'
    assert mock_window.ui.dialog['rename'].current == 'test'


def test_update_name(mock_window, monkeypatch):
    """Test update name"""
    files = _tool(mock_window)
    rename_mock = MagicMock()
    monkeypatch.setattr(os, 'rename', rename_mock)
    monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=False))
    mock_window.update_status = MagicMock()
    files.operations.apply_name('test', 'test2')
    rename_mock.assert_called_once_with('test', os.path.join(os.path.dirname('test'), 'test2'))
    mock_window.ui.dialog['rename'].close.assert_called_once_with()


def test_open_dir(mock_window):
    files = _tool(mock_window)
    mock_window.core.filesystem.get_path.return_value = '/tmp/test'
    with patch('pygpt_net.tools.files.core.paths.os.path.exists', return_value=True), \
         patch('pygpt_net.tools.files.core.paths.Opener.open_path') as opener:
        files.paths.reveal('test')
    opener.assert_called_once_with('/tmp/test', reveal=False)


def test_open(mock_window, monkeypatch):
    """Test open"""
    files = _tool(mock_window)
    mock_window.core.platforms.is_snap = MagicMock(return_value=False)
    open_url_mock = MagicMock()
    monkeypatch.setattr(PySide6.QtGui.QDesktopServices, "openUrl", open_url_mock)
    files.paths.open('test')
    open_url_mock.assert_called_once()


def test_reveal_selects_in_file_manager(mock_window):
    files = _tool(mock_window)
    mock_window.core.filesystem.get_path.return_value = '/tmp/test'
    with patch('pygpt_net.tools.files.core.paths.os.path.exists', return_value=True), \
         patch('pygpt_net.tools.files.core.paths.Opener.open_path') as opener:
        files.paths.reveal('test', True)
    opener.assert_called_once_with('/tmp/test', reveal=True)


def test_reload_explorer_without_removed_workdir_label():
    from types import SimpleNamespace
    explorer = SimpleNamespace(directory='/old', index_data=None,
                               update_view=MagicMock(), model=MagicMock(),
                               refresh_empty_state=MagicMock())
    window = SimpleNamespace(
        controller=SimpleNamespace(tabs=MagicMock()),
        core=SimpleNamespace(tabs=MagicMock(), filesystem=MagicMock()),
    )
    window.core.filesystem.get_data_dir.return_value = '/new/workdir'
    tool = _tool(window)
    tool.explorer = explorer
    tool.refresh(reload=True)
    assert explorer.directory == '/new/workdir'
    explorer.update_view.assert_called_once_with()
    explorer.model.update_idx_status.assert_called_once_with({})
    explorer.refresh_empty_state.assert_called_once_with()



def _tool(window):
    tool = Files()
    tool.attach(window)
    return tool
