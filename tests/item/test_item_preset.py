#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 05:00:00                  #
# ================================================== #


from pygpt_net.item.preset import PresetItem


def test_integrity():
    """Test PresetItem integrity"""
    item = PresetItem()

    assert item.name == "*"
    assert item.ai_name == ""
    assert item.user_name == ""
    assert item.prompt == ""
    assert item.chat is False
    assert item.completion is False
    assert item.img is False
    assert item.vision is False
    assert item.langchain is False
    assert item.assistant is False
    assert item.temperature == 1.0
    assert item.filename is None
    assert item.version is None
