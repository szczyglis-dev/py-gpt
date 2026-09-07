from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.lists.db import DatabaseList


def test_parse_view_pretty_prints_dict_and_list_literals():
    widget = SimpleNamespace()
    parsed = DatabaseList.parse_view(widget, "{'a': 1, 'b': [2]}")
    assert '"a": 1' in parsed
    assert '"b": [' in parsed
    assert DatabaseList.parse_view(widget, "plain") == "plain"


def test_on_data_end_does_nothing_without_viewer():
    widget = SimpleNamespace(viewer=None)
    DatabaseList.on_data_end(widget)


def test_on_data_end_refreshes_viewer_only_when_value_changed():
    viewer = MagicMock()
    model = MagicMock()
    model.data.return_value = "{'a': 2}"
    widget = SimpleNamespace(
        viewer=viewer, viewer_index=object(), viewer_current="old",
        model=lambda: model,
        parse_view=lambda data: DatabaseList.parse_view(SimpleNamespace(), data),
    )
    DatabaseList.on_data_end(widget)
    assert '"a": 2' in viewer.setPlainText.call_args.args[0]
    assert widget.viewer_current == "{'a': 2}"


def test_item_click_updates_viewer_metadata():
    viewer = MagicMock()
    model = MagicMock()
    index = MagicMock()
    index.row.return_value = 4
    index.column.return_value = 2
    index.sibling.return_value.data.return_value = "17"
    model.data.return_value = "value"
    model.headerData.return_value = "field"
    widget = SimpleNamespace(
        viewer=viewer, model=lambda: model,
        parse_view=lambda data: data,
        viewer_index=None, viewer_current=None, viewer_current_id=None, viewer_current_field=None,
    )
    DatabaseList.onItemClicked(widget, index)
    viewer.setPlainText.assert_called_once_with("value")
    assert widget.viewer_index is index
    assert widget.viewer_current == "value"
    assert widget.viewer_current_id == "17"
    assert widget.viewer_current_field == "field"
    model.headerData.assert_called_once_with(2, Qt.Horizontal, Qt.DisplayRole)
