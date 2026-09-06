from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from pygpt_net.item.calendar_note import CalendarNoteItem
from pygpt_net.provider.core.calendar.db_sqlite.provider import DbSqliteProvider


def make_window():
    return SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())))


def provider():
    p = DbSqliteProvider(make_window())
    p.storage = MagicMock()
    p.patcher = MagicMock()
    return p


def test_attach_and_patch_delegate():
    p = provider(); window = make_window()
    p.storage.attach = MagicMock()
    p.attach(window)
    assert p.window is window
    p.storage.attach.assert_called_once_with(window)
    p.patcher.execute.return_value = True
    version = Version("2.8.0")
    assert p.patch(version) is True
    p.patcher.execute.assert_called_once_with(version)


def test_create_id_is_mockable_and_create_inserts_only_new_note():
    p = provider()
    with patch("pygpt_net.provider.core.calendar.db_sqlite.provider.uuid.uuid4", return_value="uuid"):
        assert p.create_id() == "uuid"
    note = CalendarNoteItem(); note.id = None
    p.storage.insert.return_value = 7
    assert p.create(note) == 7
    p.storage.insert.assert_called_once_with(note)
    p.storage.insert.reset_mock(); note.id = 9
    assert p.create(note) == 9
    p.storage.insert.assert_not_called()


@pytest.mark.parametrize("method,args,target", [
    ("load_all", (), "get_all"),
    ("load_by_month", (2026, 9), "get_by_month"),
    ("load", (2026, 9, 6), "get_by_date"),
    ("get_notes_existence_by_day", (2026, 9), "get_notes_existence_by_day"),
    ("remove", (2026, 9, 6), "delete_by_date"),
    ("truncate", (), "truncate_all"),
])
def test_simple_storage_delegates(method, args, target):
    p = provider(); expected = object()
    getattr(p.storage, target).return_value = expected
    result = getattr(p, method)(*args)
    getattr(p.storage, target).assert_called_once_with(*args)
    if method != "remove":
        assert result is expected


def test_save_and_save_all_delegate_and_log_errors():
    p = provider(); note = CalendarNoteItem(); note.id = 1
    p.save(note)
    p.storage.save.assert_called_once_with(note)
    p.storage.save.reset_mock()
    other = CalendarNoteItem(); other.id = 2
    p.save_all({"a": note, "b": other})
    assert p.storage.save.call_args_list[0].args == (note,)
    assert p.storage.save.call_args_list[1].args == (other,)

    p.storage.save.side_effect = RuntimeError("db")
    p.save(note)
    p.window.core.debug.log.assert_called()
