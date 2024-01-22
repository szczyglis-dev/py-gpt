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
from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.db import Database


def test_init(mock_window):
    """Test initialize"""
    db = Database(mock_window)
    db.prepare = MagicMock()
    db.init()
    db.prepare.assert_called_once()


def test_prepare(mock_window):
    """Test prepare"""
    db = Database(mock_window)
    db.is_installed = MagicMock(return_value=True)
    db.prepare()
    db.is_installed.assert_called_once()
    assert db.engine is not None


def test_install(mock_window):
    """Test install"""
    db = Database(mock_window)
    db.engine = MagicMock()
    db.install()
    db.engine.begin.assert_called_once()


def test_get_version(mock_window):
    """Test get version"""
    db = Database(mock_window)
    db.engine = MagicMock()
    assert type(db.get_version()) == int


def test_get_db(mock_window):
    """Test get db"""
    db = Database(mock_window)
    db.engine = MagicMock()
    assert db.get_db() == db.engine


def test_is_installed(mock_window):
    """Test is installed"""
    db = Database(mock_window)
    with patch("os.path.exists") as os_path_exists:
        os_path_exists.return_value = False
        assert db.is_installed() is False


def test_apply_migration(mock_window):
    """Test apply migration"""
    db = Database(mock_window)
    db.engine = MagicMock()
    db.migrations = MagicMock()
    migration = MagicMock()
    migration.__class__.__name__ = "Version2"
    migration.up = MagicMock()
    conn = MagicMock()
    db.apply_migration(migration, conn, 1)
    migration.up.assert_called_once()


def test_migrate(mock_window):
    """Test migrate"""
    db = Database(mock_window)
    db.engine = MagicMock()
    db.migrations = MagicMock()
    db.migrations.get_migrations = MagicMock(return_value=[MagicMock()])
    db.get_version = MagicMock(return_value=1)
    db.apply_migration = MagicMock()
    db.migrate()
    db.apply_migration.assert_called()


def test_get_param(mock_window):
    """Test get param"""
    db = Database(mock_window)
    db.engine = MagicMock()
    db.engine.connect = MagicMock()
    db.prepare = MagicMock()
    db.is_installed = MagicMock(return_value=True)
    db.get_param("test")
    db.engine.connect.assert_called_once()


def test_set_param(mock_window):
    """Test set param"""
    db = Database(mock_window)
    db.engine = MagicMock()
    db.engine.connect = MagicMock()
    db.prepare = MagicMock()
    db.is_installed = MagicMock(return_value=True)
    db.set_param("test", "test")
    db.engine.begin.assert_called_once()


def test_set_param_execption(mock_window):
    """Test set param exception"""
    db = Database(mock_window)
    db.engine = MagicMock()
    db.engine.connect = MagicMock()
    db.prepare = MagicMock()
    db.is_installed = MagicMock(return_value=True)
    db.set_param("test", "test")
    db.engine.begin.assert_called_once()

