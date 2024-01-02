#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

from pygpt_net.item.mode import ModeItem


def test_integrity():
    """Test ModeItem integrity"""
    item = ModeItem()

    assert item.id is None
    assert item.name == ""
    assert item.label == ""
