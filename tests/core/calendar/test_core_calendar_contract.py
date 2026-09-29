import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

from packaging.version import Version

import pygpt_net.core.calendar.calendar as mod
from pygpt_net.core.calendar.calendar import Calendar
from pygpt_net.item.calendar_note import CalendarNoteItem


FIXED_NOW = dt.datetime(2025, 1, 2, 3, 4, 5)


class FixedDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FIXED_NOW
        return FIXED_NOW.replace(tzinfo=dt.timezone.utc).astimezone(tz)


def make_calendar():
    calendar = Calendar.__new__(Calendar)
    calendar.window = SimpleNamespace()
    calendar.provider = MagicMock()
    calendar.items = {}
    return calendar


def make_note(year=2025, month=1, day=2, content="note"):
    note = CalendarNoteItem()
    note.year = year; note.month = month; note.day = day; note.content = content
    return note


def test_install_and_patch_delegate_to_provider():
    calendar = make_calendar()
    calendar.install()
    calendar.provider.install.assert_called_once_with()
    version = Version("2.8.4")
    calendar.patch(version)
    calendar.provider.patch.assert_called_once_with(version)


def test_build_get_by_date_and_get_all():
    calendar = make_calendar()
    built = calendar.build()
    assert isinstance(built, CalendarNoteItem)
    note = make_note()
    calendar.items["2025-01-02"] = note
    assert calendar.get_by_date(2025, 1, 2) is note
    assert calendar.get_by_date(2025, 1, 3) is None
    assert calendar.get_all() is calendar.items


def test_add_creates_stores_and_saves_note():
    calendar = make_calendar()
    note = make_note()
    calendar.save = MagicMock(return_value=True)
    assert calendar.add(note) is True
    calendar.provider.create.assert_called_once_with(note)
    assert calendar.items["2025-01-02"] is note
    calendar.save.assert_called_once_with(2025, 1, 2)


def test_update_requires_existing_note_and_uses_fixed_time(monkeypatch):
    calendar = make_calendar()
    note = make_note()
    calendar.save = MagicMock()
    assert calendar.update(note) is False
    calendar.items["2025-01-02"] = note
    monkeypatch.setattr(mod.datetime, "datetime", FixedDateTime)
    assert calendar.update(note) is True
    assert note.updated == "2025-01-02T03:04:05"
    calendar.save.assert_called_once_with(2025, 1, 2)


def test_load_and_load_note_delegate_and_handle_missing():
    calendar = make_calendar()
    note = make_note(content="abc")
    calendar.provider.load.side_effect = [note, note, None]
    calendar.load(2025, 1, 2)
    assert calendar.items["2025-01-02"] is note
    assert calendar.load_note(2025, 1, 2) == "abc"
    assert calendar.load_note(2025, 1, 3) == ""


def test_append_to_note_creates_or_appends_content():
    calendar = make_calendar()
    existing = make_note(content="old")
    calendar.provider.load.side_effect = [None, existing]
    calendar.load = MagicMock()

    assert calendar.append_to_note(2025, 2, 3, "new") is True
    created = calendar.provider.save.call_args_list[0].args[0]
    assert (created.year, created.month, created.day, created.content) == (2025, 2, 3, "new")

    assert calendar.append_to_note(2025, 2, 3, "next") is True
    assert calendar.provider.save.call_args_list[1].args[0].content == "old\nnext"
    assert calendar.load.call_count == 2


def test_update_note_creates_missing_or_replaces_existing():
    calendar = make_calendar()
    existing = make_note(content="old")
    calendar.provider.load.side_effect = [None, existing]
    calendar.load = MagicMock()

    assert calendar.update_note(2025, 2, 3, "first") is True
    created = calendar.provider.save.call_args_list[0].args[0]
    assert (created.year, created.month, created.day, created.content) == (2025, 2, 3, "first")

    assert calendar.update_note(2025, 1, 2, "replacement") is True
    assert existing.content == "replacement"


def test_remove_load_collections_and_existence_delegation():
    calendar = make_calendar()
    calendar.items["2025-01-02"] = make_note()
    assert calendar.remove_note(2025, 1, 2) is True
    calendar.provider.remove.assert_called_once_with(2025, 1, 2)
    assert "2025-01-02" not in calendar.items

    calendar.provider.load_all.return_value = {"a": 1}
    calendar.load_all()
    assert calendar.items == {"a": 1}
    calendar.provider.load_by_month.return_value = {"b": 2}
    calendar.load_by_month(2025, 1)
    assert calendar.items == {"b": 2}
    calendar.provider.get_notes_existence_by_day.return_value = {"days": {1: 1}}
    assert calendar.get_notes_existence_by_day(2025, 1) == {"days": {1: 1}}


def test_save_returns_false_for_missing_and_current_production_result_for_existing():
    calendar = make_calendar()
    assert calendar.save(2025, 1, 2) is False
    note = make_note()
    calendar.items["2025-01-02"] = note
    # Production currently returns False even after a successful provider.save; keep the contract explicit.
    assert calendar.save(2025, 1, 2) is False
    calendar.provider.save.assert_called_once_with(note)


def test_save_all_delegates_entire_mapping():
    calendar = make_calendar()
    calendar.items = {"2025-01-02": make_note()}
    calendar.save_all()
    calendar.provider.save_all.assert_called_once_with(calendar.items)
