#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from pygpt_net.item.assistant import AssistantItem


def test_integrity():
    """Test AssistantItem integrity"""
    item = AssistantItem()

    assert item.id is None
    assert item.name is None
    assert item.description is None
    assert item.instructions is None
    assert item.model is None
    assert item.meta == {}
    assert item.files == {}
    assert item.attachments == {}
    assert item.tools == {
        "code_interpreter": False,
        "file_search": False,
        "function": [],
    }
