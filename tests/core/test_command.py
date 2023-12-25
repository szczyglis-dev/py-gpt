#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import json

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QMainWindow

from pygpt_net.config import Config
from pygpt_net.core.command import Command


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.app = MagicMock()
    window.app.config = MagicMock(spec=Config)
    return window


def test_get_prompt(mock_window):
    """
    Test get prompt
    """
    cmd = Command(window=mock_window)
    assert cmd.get_prompt().startswith('RUNNING COMMANDS:')


def test_append_syntax():
    """
    Test append syntax
    """
    cmd = Command()
    event_data = {'prompt': 'test', 'syntax': ['syntax1', 'syntax2']}
    assert cmd.append_syntax(event_data) == 'test\nsyntax1\nsyntax2'


def test_extract_cmds_only():
    """
    Test extract cmds only
    """
    cmd = Command()
    cmd1 = '{"cmd": "command1", "params": {"arg1": "some arg"}}'
    cmd2 = '{"cmd": "command2", "params": {"query": "some other arg"}}'
    response = '~###~ ' + cmd1 + ' ~###~ ' + cmd2

    json1 = json.loads(cmd1.strip())
    json2 = json.loads(cmd2.strip())
    assert cmd.extract_cmds(response) == [json1, json2]


def test_extract_cmds_with_text():
    """
    Test extract cmds with text
    """
    cmd = Command()
    cmd1 = '{"cmd": "command1", "params": {"arg1": "some arg"}}'
    cmd2 = '{"cmd": "command2", "params": {"query": "some other arg"}}'
    response = 'bla bla bla ~###~ ' + cmd1 + ' ~###~ ' + cmd2

    json1 = json.loads(cmd1.strip())
    json2 = json.loads(cmd2.strip())
    assert cmd.extract_cmds(response) == [json1, json2]
