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
import json
import os
import ssl

from packaging.version import parse as parse_version, Version
from unittest.mock import MagicMock, patch
from urllib.request import urlopen, Request
from tests.mocks import mock_window
from pygpt_net.core.updater import Updater


def test_patch(mock_window):
    """Test patch"""
    updater = Updater(mock_window)
    updater.get_app_version = MagicMock(return_value=parse_version("1.0.0"))
    updater.migrate_db = MagicMock()
    updater.patch_config = MagicMock()
    updater.patch_models = MagicMock()
    updater.patch_presets = MagicMock()
    updater.patch_ctx = MagicMock()
    updater.patch_assistants = MagicMock()
    updater.patch_attachments = MagicMock()
    updater.patch_notepad = MagicMock()

    updater.patch()

    updater.migrate_db.assert_called_once()
    updater.patch_config.assert_called_once()
    updater.patch_models.assert_called_once()
    updater.patch_presets.assert_called_once()
    updater.patch_ctx.assert_called_once()
    updater.patch_assistants.assert_called_once()
    updater.patch_attachments.assert_called_once()
    updater.patch_notepad.assert_called_once()


def test_migrate_db(mock_window):
    """Test migrate_db"""
    updater = Updater(mock_window)
    mock_window.core.db.migrate = MagicMock()
    updater.migrate_db()
    mock_window.core.db.migrate.assert_called_once()


def test_patch_config(mock_window):
    """Test patch_config"""
    updater = Updater(mock_window)
    mock_window.core.config.patch = MagicMock(return_value=True)
    updater.patch_config(parse_version("1.0.0"))
    mock_window.core.config.patch.assert_called_once()


def test_patch_models(mock_window):
    """Test patch_models"""
    updater = Updater(mock_window)
    mock_window.core.models.patch = MagicMock(return_value=True)
    updater.patch_models(parse_version("1.0.0"))
    mock_window.core.models.patch.assert_called_once()


def test_patch_presets(mock_window):
    """Test patch_presets"""
    updater = Updater(mock_window)
    mock_window.core.presets.patch = MagicMock(return_value=True)
    updater.patch_presets(parse_version("1.0.0"))
    mock_window.core.presets.patch.assert_called_once()


def test_patch_ctx(mock_window):
    """Test patch_ctx"""
    updater = Updater(mock_window)
    mock_window.core.ctx.patch = MagicMock(return_value=True)
    updater.patch_ctx(parse_version("1.0.0"))
    mock_window.core.ctx.patch.assert_called_once()


def test_patch_assistants(mock_window):
    """Test patch_assistants"""
    updater = Updater(mock_window)
    mock_window.core.assistants.patch = MagicMock(return_value=True)
    updater.patch_assistants(parse_version("1.0.0"))
    mock_window.core.assistants.patch.assert_called_once()


def test_patch_attachments(mock_window):
    """Test patch_attachments"""
    updater = Updater(mock_window)
    mock_window.core.attachments.patch = MagicMock(return_value=True)
    updater.patch_attachments(parse_version("1.0.0"))
    mock_window.core.attachments.patch.assert_called_once()


def test_patch_notepad(mock_window):
    """Test patch_notepad"""
    updater = Updater(mock_window)
    mock_window.core.notepad.patch = MagicMock(return_value=True)
    updater.patch_notepad(parse_version("1.0.0"))
    mock_window.core.notepad.patch.assert_called_once()


def test_patch_dir(mock_window):
    """Test patch_dir"""
    updater = Updater(mock_window)

    with patch('shutil.copyfile') as mock_copyfile:
        os.listdir = MagicMock(return_value=["test_file"])
        os.path.exists = MagicMock(return_value=False)
        os.path.join = MagicMock(return_value="/tmp/test_file")
        mock_window.core.config.path = "/tmp"
        mock_window.core.config.get_app_path = MagicMock(return_value="/tmp")
        updater.patch_dir("test_dir", True)
        mock_window.core.config.get_app_path.assert_called_once()
        mock_window.core.config.get_app_path = MagicMock(return_value="/tmp")


def test_patch_file(mock_window):
    """Test patch_file"""
    updater = Updater(mock_window)

    with patch('shutil.copyfile') as mock_copyfile:
        os.listdir = MagicMock(return_value=["test_file"])
        os.path.exists = MagicMock(return_value=False)
        os.path.join = MagicMock(return_value="/tmp/test_file")
        mock_window.core.config.path = "/tmp"
        mock_window.core.config.get_app_path = MagicMock(return_value="/tmp")
        updater.patch_file("test_file", True)
        mock_window.core.config.get_app_path.assert_called_once()
        mock_window.core.config.get_app_path = MagicMock(return_value="/tmp")


def test_get_app_version(mock_window):
    """Test get_app_version"""
    updater = Updater(mock_window)
    mock_window.meta = {'version': '1.0.0'}
    assert updater.get_app_version() == parse_version("1.0.0")


def test_check(mock_window):
    """Test check"""
    mock_window.meta = {'version': '1.0.0', 'website': 'https://example.com'}
    fake_response_data = {
        "version": "1.0.1",
        "build": 101,
        "changelog": "test",
    }
    fake_read = MagicMock()
    fake_read.return_value = json.dumps(fake_response_data).encode('utf-8')
    fake_urlopen = MagicMock(return_value=MagicMock(read=fake_read))

    with patch('pygpt_net.core.updater.urlopen', fake_urlopen), \
         patch('pygpt_net.core.updater.Request', MagicMock()), \
         patch('ssl.create_default_context', return_value=MagicMock()) as fake_ctx:

        fake_ctx.return_value.check_hostname = False
        fake_ctx.return_value.verify_mode = ssl.CERT_NONE
        updater = Updater(mock_window)
        updater.show_version_dialog = MagicMock()
        assert updater.check() is True


def test_show_version_dialog(mock_window):
    """Test show_version_dialog"""
    updater = Updater(mock_window)
    mock_window.meta = {'version': '1.0.0', 'website': 'https://example.com'}
    mock_window.ui.dialog = {'update': MagicMock()}
    updater.show_version_dialog("1.0.0", "2024-01-01", "test", True)
    mock_window.ui.dialog['update'].info.setText.assert_called_once()
    mock_window.ui.dialogs.open('update')


def test_post_check_config(mock_window):
    """Test post_check_config"""
    updater = Updater(mock_window)
    mock_window.core.config.get_base = MagicMock(return_value={'test': 'test', 'extra': 'extra'})
    mock_window.core.config.all = MagicMock(return_value={'test': 'test'})
    mock_window.core.config.data = {'test': 'test'}
    mock_window.core.config.save = MagicMock()
    assert updater.post_check_config() is True  # updated, added extra key
