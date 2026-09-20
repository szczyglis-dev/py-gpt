#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.notepad import NotepadItem


def test_notepad_integrity_uses_mocked_timestamp():
    with patch("pygpt_net.item.notepad.time.time", return_value=1_700_000_321):
        item = NotepadItem()

    assert item.id == 0
    assert item.uuid is None
    assert item.idx == 0
    assert item.title == ""
    assert item.content == ""
    assert item.deleted is False
    assert item.created == 1_700_000_321
    assert item.updated == 1_700_000_321
    assert item.initialized is False
    assert item.highlights == []
    assert item.scroll_pos == -1


def test_notepad_to_dict_dump_and_str():
    with patch("pygpt_net.item.notepad.time.time", return_value=123):
        item = NotepadItem()
    item.uuid = "u1"
    item.idx = 4
    item.title = "Title"
    item.content = "Body"
    item.highlights = [{"start": 1, "end": 2}]
    item.scroll_pos = 15

    data = item.to_dict()
    assert data["uuid"] == "u1"
    assert data["created"] == 123
    assert data["highlights"] == [{"start": 1, "end": 2}]
    assert data["scroll_pos"] == 15
    assert json.loads(item.dump()) == data
    assert str(item) == item.dump()


def test_notepad_dump_returns_empty_string_on_serialization_error():
    with patch("pygpt_net.item.notepad.time.time", return_value=1), \
            patch("pygpt_net.item.notepad.json.dumps", side_effect=TypeError):
        assert NotepadItem().dump() == ""
