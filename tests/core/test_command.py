#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

import json
from unittest.mock import MagicMock

from tests.mocks import mock_window_conf, mock_window
from pygpt_net.core.command import Command


def test_get_prompt(mock_window_conf):
    """
    Test get prompt
    """
    cmd = Command(window=mock_window_conf)
    assert cmd.get_prompt().startswith('RUNNING COMMANDS:')


def test_append_syntax():
    """
    Test append syntax
    """
    window = MagicMock()
    cmd = Command(window=window)
    event_data = {'prompt': 'test', 'cmd': ['cmd1', 'cmd2']}
    assert cmd.append_syntax(event_data).startswith("test\n") is True


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


def test_extract_cmd():
    """
    Test extract cmd
    """
    cmd = Command()
    cmd1 = '{"cmd": "command1", "params": {"arg1": "some arg"}}   '
    assert cmd.extract_cmd(cmd1) == json.loads(cmd1.strip())


def test_extract_cmd_white_spaces():
    """
    Test extract cmd
    """
    cmd = Command()
    cmd1 = '   ' \
           '{"cmd": "command1", "params": {"arg1": "some arg"}}   '
    assert cmd.extract_cmd(cmd1) == json.loads(cmd1.strip())