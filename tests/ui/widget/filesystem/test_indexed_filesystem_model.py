from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.filesystem.explorer import IndexedFileSystemModel


def _index(column):
    idx = MagicMock()
    idx.column.return_value = column
    idx.siblingAtColumn.return_value = "path-index"
    return idx


def test_index_status_is_cached_by_file_id():
    files = MagicMock()
    files.get_id.return_value = 10
    idx_core = MagicMock()
    idx_core.files = files
    idx_core.get_file_index_status.return_value = {"indexed": True}
    widget = SimpleNamespace(window=SimpleNamespace(core=SimpleNamespace(idx=idx_core)), _status_cache={})

    first = IndexedFileSystemModel.get_index_status(widget, "/a")
    second = IndexedFileSystemModel.get_index_status(widget, "/a")

    assert first == {"indexed": True}
    assert second is first
    idx_core.get_file_index_status.assert_called_once_with("/a")


def test_refresh_path_clears_cache_and_emits_only_for_valid_index():
    valid = MagicMock()
    valid.isValid.return_value = True
    widget = SimpleNamespace(index=MagicMock(return_value=valid), _status_cache={1: "x"}, dataChanged=MagicMock())

    IndexedFileSystemModel.refresh_path(widget, "/a")

    assert widget._status_cache == {}
    widget.dataChanged.emit.assert_called_once_with(valid, valid)


def test_indexed_column_timestamp_rendering_uses_mocked_conversion_not_host_timezone():
    index = _index(4)
    status = {"indexed": True, "last_index_at": 1700000000, "indexed_in": ["docs", "chat"]}
    widget = SimpleNamespace(
        columnCount=lambda: 5,
        filePath=MagicMock(return_value="/a"),
        get_index_status=MagicMock(return_value=status),
    )
    fixed = datetime(2026, 9, 7, 12, 34, 56)

    with patch("pygpt_net.ui.widget.filesystem.explorer.datetime.datetime") as dt_cls, \
            patch("pygpt_net.ui.widget.filesystem.explorer.datetime.date") as date_cls:
        dt_cls.fromtimestamp.return_value = fixed
        date_cls.today.return_value = fixed.date()
        value = IndexedFileSystemModel.data(widget, index, Qt.DisplayRole)

    assert value == "12:34 (docs,chat)"
    dt_cls.fromtimestamp.assert_called_once_with(1700000000)


def test_indexed_column_nonindexed_value_is_dash_without_clock_conversion():
    index = _index(4)
    widget = SimpleNamespace(
        columnCount=lambda: 5,
        filePath=MagicMock(return_value="/a"),
        get_index_status=MagicMock(return_value={"indexed": False}),
    )
    with patch("pygpt_net.ui.widget.filesystem.explorer.datetime.datetime") as dt_cls:
        assert IndexedFileSystemModel.data(widget, index, Qt.DisplayRole) == "-"
    dt_cls.fromtimestamp.assert_not_called()


def test_modified_column_marks_file_newer_than_last_index_using_mocked_timestamp_conversion():
    index = _index(3)
    modified = MagicMock()
    modified.toSecsSinceEpoch.return_value = 200
    status = {"indexed": True, "last_index_at": 100}
    widget = SimpleNamespace(
        columnCount=lambda: 5,
        lastModified=MagicMock(return_value=modified),
        filePath=MagicMock(return_value="/a"),
        get_index_status=MagicMock(return_value=status),
    )
    fixed = datetime(2026, 9, 6, 23, 0, 0)

    with patch("pygpt_net.ui.widget.filesystem.explorer.datetime.datetime") as dt_cls, \
            patch("pygpt_net.ui.widget.filesystem.explorer.datetime.date") as date_cls:
        dt_cls.fromtimestamp.return_value = fixed
        date_cls.today.return_value = datetime(2026, 9, 7).date()
        value = IndexedFileSystemModel.data(widget, index, Qt.DisplayRole)

    assert value == "2026-09-06 23:00*"
    dt_cls.fromtimestamp.assert_called_once_with(200)
