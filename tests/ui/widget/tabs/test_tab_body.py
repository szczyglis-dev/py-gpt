from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.tabs.body import TabBody


def test_cleanup_calls_delete_callback_and_deletes_refs():
    widget = SimpleNamespace(on_delete=MagicMock(), delete_refs=MagicMock())
    TabBody.cleanup(widget)
    widget.on_delete.assert_called_once_with(widget)
    widget.delete_refs.assert_called_once()


def test_add_ref_deduplicates_and_delete_ref_removes_identity_match():
    ref = object()
    widget = SimpleNamespace(refs=[])
    TabBody.add_ref(widget, ref)
    TabBody.add_ref(widget, ref)
    assert widget.refs == [ref]
    TabBody.delete_ref(widget, ref)
    assert widget.refs == []


def test_delete_refs_calls_cleanup_hooks_and_clears_list_even_on_errors():
    good = MagicMock()
    bad = MagicMock()
    bad.on_delete.side_effect = RuntimeError("ignored")
    widget = SimpleNamespace(refs=[None, good, bad])

    TabBody.delete_refs(widget)

    good.on_delete.assert_called_once()
    good.deleteLater.assert_called_once()
    bad.on_delete.assert_called_once()
    bad.deleteLater.assert_called_once()
    assert widget.refs == []


def test_unwrap_removes_widget_and_reference():
    layout = MagicMock()
    child = object()
    widget = SimpleNamespace(layout=lambda: layout, delete_ref=MagicMock())

    TabBody.unwrap(widget, child)

    layout.removeWidget.assert_called_once_with(child)
    widget.delete_ref.assert_called_once_with(child)


def test_unwrap_all_drains_layout_and_unpins_each_widget():
    first = object()
    second = object()
    layout = MagicMock()
    layout.count.side_effect = [2, 1, 0]
    layout.takeAt.side_effect = [SimpleNamespace(widget=lambda: first), SimpleNamespace(widget=lambda: second)]
    widget = SimpleNamespace(layout=lambda: layout, delete_ref=MagicMock())

    TabBody.unwrap_all(widget)

    assert layout.removeWidget.call_count == 2
    assert widget.delete_ref.call_count == 2


def test_body_append_get_attach_and_owner():
    body1 = MagicMock()
    body2 = object()
    widget = SimpleNamespace(body=[], owner=None)

    TabBody.append(widget, body1)
    TabBody.append(widget, body2)
    assert TabBody.get_body(widget) == [body1, body2]

    owner = SimpleNamespace(column_idx=1)
    TabBody.attach_tab(widget, owner)
    body1.set_tab.assert_called_once_with(owner)

    widget.attach_tab = MagicMock()
    TabBody.setOwner(widget, owner)
    assert TabBody.getOwner(widget) is owner
    widget.attach_tab.assert_called_once_with(owner)


def test_to_dict_serializes_refs_body_and_layout_count():
    layout = MagicMock()
    layout.count.return_value = 3
    widget = SimpleNamespace(refs=[1, "a"], body=[2], layout=lambda: layout)

    assert TabBody.to_dict(widget) == {
        "refs": ["1", "a"],
        "body": ["2"],
        "len(layout)": 3,
    }
