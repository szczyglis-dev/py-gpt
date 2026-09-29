from datetime import datetime
from unittest.mock import patch

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.lists.db import DatabaseTableModel


def test_database_model_returns_plain_values_without_timestamp_conversion():
    model = DatabaseTableModel(
        data=[[1700000000, "name"]],
        headers=["created", "name"],
        timestamp_columns=["created"],
        convert_timestamps=False,
    )

    assert model.data(model.index(0, 0), Qt.DisplayRole) == 1700000000
    assert model.data(model.index(0, 1), Qt.DisplayRole) == "name"


def test_database_model_formats_timestamp_with_mocked_clock_conversion():
    model = DatabaseTableModel(
        data=[[1700000000]],
        headers=["created"],
        timestamp_columns=["created"],
    )
    fixed = datetime(2023, 11, 14, 22, 13, 20)

    with patch("pygpt_net.ui.widget.lists.db.datetime") as dt:
        dt.fromtimestamp.return_value = fixed
        value = model.data(model.index(0, 0), Qt.DisplayRole)

    assert value == "2023-11-14 22:13:20"
    dt.fromtimestamp.assert_called_once_with(1700000000)


def test_database_model_empty_timestamp_values_are_blank():
    model = DatabaseTableModel(
        data=[[0], ["None"]],
        headers=["created"],
        timestamp_columns=["created"],
    )

    assert model.data(model.index(0, 0), Qt.DisplayRole) == ""
    assert model.data(model.index(1, 0), Qt.DisplayRole) == ""


def test_database_model_dimensions_and_headers():
    model = DatabaseTableModel(data=[[1, 2], [3, 4]], headers=["a", "b"])

    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "a"
    assert model.headerData(0, Qt.Vertical, Qt.DisplayRole) is None
