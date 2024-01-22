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

from pygpt_net.item.attachment import AttachmentItem


def test_integrity():
    """Test AttachmentItem integrity"""
    item = AttachmentItem()

    assert item.name is None
    assert item.id is None
    assert item.path is None
    assert item.remote is None
    assert item.send is False
