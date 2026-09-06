#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from unittest.mock import patch

from pygpt_net.item.calendar_note import CalendarNoteItem


def test_calendar_note_defaults_use_timestamp_not_local_datetime():
    with patch("pygpt_net.item.calendar_note.time.time", return_value=1_700_000_123):
        item = CalendarNoteItem()

    assert item.id == 0
    assert item.uuid is None
    assert (item.year, item.month, item.day) == (0, 0, 0)
    assert item.created == 1_700_000_123
    assert item.updated == 1_700_000_123
    assert item.deleted is False
    assert item.important is False
    assert item.initialized is False


def test_calendar_note_get_dt_and_serialization():
    with patch("pygpt_net.item.calendar_note.time.time", return_value=123):
        item = CalendarNoteItem()
    item.uuid = "abc"
    item.year, item.month, item.day = 2026, 9, 6
    item.title = "Release"
    item.content = "Ship"

    assert item.get_dt() == "2026-09-06"
    data = item.to_dict()
    assert data["uuid"] == "abc"
    assert data["created"] == 123
    assert data["updated"] == 123
    assert json.loads(item.dump()) == data
    assert str(item) == item.dump()


def test_calendar_note_dump_returns_empty_string_on_serialization_error():
    with patch("pygpt_net.item.calendar_note.time.time", return_value=1), \
            patch("pygpt_net.item.calendar_note.json.dumps", side_effect=TypeError):
        assert CalendarNoteItem().dump() == ""
