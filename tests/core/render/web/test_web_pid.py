#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #
import pytest
import importlib
from pygpt_net.core.render.web.pid import PidData

def fake_trans(key):
    return f"fake_{key}"

@pytest.fixture(autouse=True)
def override_trans(monkeypatch):
    mod = importlib.import_module(PidData.__module__)
    monkeypatch.setattr(mod, "trans", fake_trans)

def test_piddata_initialization_with_meta():
    pid = "pid_test"
    meta = {"key": "value"}
    obj = PidData(pid, meta)
    assert obj.pid == pid
    assert obj.meta == meta
    assert obj.images_appended == []
    assert obj.urls_appended == []
    assert obj.files_appended == []
    assert obj.buffer == ""
    assert obj.live_buffer == ""
    assert obj.is_cmd is False
    assert obj.html == ""
    assert obj.document == ""
    assert obj.initialized is False
    assert obj.loaded is False
    assert obj.item is None
    assert obj.use_buffer is False
    assert obj.name_user == "fake_chat.name.user"
    assert obj.name_bot == "fake_chat.name.bot"
    assert obj.last_time_called == 0
    assert obj.cooldown == 1 / 6
    assert obj.throttling_min_chars == 5000

def test_piddata_initialization_without_meta():
    pid = "pid_only"
    obj = PidData(pid)
    assert obj.pid == pid
    assert obj.meta is None