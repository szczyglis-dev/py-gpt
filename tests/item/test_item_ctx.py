#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 01:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxMeta, CtxItem


def test_integrity_ctx_item():
    """Test CtxItem integrity"""
    item = CtxItem()

    assert item.id is None
    assert item.meta_id is None
    assert item.external_id is None
    assert item.stream is None
    assert item.cmds == []
    assert item.results == []
    assert item.urls == []
    assert item.images == []
    assert item.files == []
    assert item.attachments == []
    assert item.reply is False
    assert item.input is None
    assert item.output is None
    assert item.mode is None
    assert item.model is None
    assert item.thread is None
    assert item.msg_id is None
    assert item.run_id is None
    assert item.input_name is None
    assert item.output_name is None
    assert item.input_timestamp is None
    assert item.output_timestamp is None
    assert item.input_tokens == 0
    assert item.output_tokens == 0
    assert item.total_tokens == 0
    assert item.extra == {}
    assert item.current is False
    assert item.internal is False
    assert item.is_vision is False


def test_integrity_ctx_meta():
    """Test CtxMeta integrity"""
    item = CtxMeta()

    assert item.id is None
    assert item.external_id is None
    assert item.uuid is None
    assert item.name is None
    assert item.date is not None
    assert item.created is not None
    assert item.updated is not None
    assert item.mode is None
    assert item.model is None
    assert item.last_mode is None
    assert item.last_model is None
    assert item.thread is None
    assert item.assistant is None
    assert item.preset is None
    assert item.run is None
    assert item.status is None
    assert item.extra is None
    assert item.initialized is False
    assert item.deleted is False
    assert item.important is False
    assert item.archived is False

    assert type(item.created) == int
    assert type(item.updated) == int
