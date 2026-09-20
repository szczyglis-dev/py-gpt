from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.lists.debug import DebugList


def test_parse_view_formats_python_literal_mapping_and_list_as_json():
    widget = SimpleNamespace()

    mapping = DebugList.parse_view(widget, "{'b': 2, 'a': 1}")
    values = DebugList.parse_view(widget, "[1, 2]")

    assert '"b": 2' in mapping
    assert mapping.startswith("{\n")
    assert values == "[\n    1,\n    2\n]"


def test_parse_view_leaves_plain_or_invalid_data_untouched():
    widget = SimpleNamespace()
    assert DebugList.parse_view(widget, "plain") == "plain"
    assert DebugList.parse_view(widget, "{bad json") == "{bad json"


def test_data_begin_adjusts_columns_then_disables_updates():
    widget = SimpleNamespace(adjustColumns=MagicMock(), setUpdatesEnabled=MagicMock())
    DebugList.on_data_begin(widget)
    widget.adjustColumns.assert_called_once()
    widget.setUpdatesEnabled.assert_called_once_with(False)


def test_data_end_refreshes_viewer_only_when_value_changed():
    model = MagicMock()
    model.data.return_value = "{'a': 1}"
    viewer = MagicMock()
    widget = SimpleNamespace(
        viewer_index=object(),
        viewer_current="old",
        viewer=viewer,
        model=lambda: model,
        parse_view=lambda value: DebugList.parse_view(SimpleNamespace(), value),
        setUpdatesEnabled=MagicMock(),
    )

    DebugList.on_data_end(widget)

    viewer.setPlainText.assert_called_once()
    assert widget.viewer_current == "{'a': 1}"
    widget.setUpdatesEnabled.assert_called_once_with(True)


def test_item_click_updates_viewer_tracking_state():
    model = MagicMock()
    model.data.return_value = "value"
    viewer = MagicMock()
    index = object()
    widget = SimpleNamespace(
        model=lambda: model,
        viewer=viewer,
        viewer_index=None,
        viewer_current=None,
        parse_view=lambda value: value.upper(),
    )

    DebugList.onItemClicked(widget, index)

    viewer.setPlainText.assert_called_once_with("VALUE")
    assert widget.viewer_index is index
    assert widget.viewer_current == "value"
