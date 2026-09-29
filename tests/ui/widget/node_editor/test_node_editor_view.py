from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.node_editor.view import NodeGraphicsView, NodeGraphicsScene


def _bar(value=0):
    bar = MagicMock()
    bar.value.return_value = value
    return bar


def test_apply_zoom_updates_scale_within_bounds():
    widget = SimpleNamespace(_zoom=1.0, _min_zoom=0.5, _max_zoom=2.0, scale=MagicMock())
    NodeGraphicsView._apply_zoom(widget, 1.5)
    assert widget._zoom == 1.5
    widget.scale.assert_called_once_with(1.5, 1.5)


def test_apply_zoom_ignores_factor_outside_bounds():
    widget = SimpleNamespace(_zoom=1.0, _min_zoom=0.5, _max_zoom=2.0, scale=MagicMock())
    NodeGraphicsView._apply_zoom(widget, 3.0)
    assert widget._zoom == 1.0
    widget.scale.assert_not_called()


def test_zoom_in_and_out_delegate_to_apply_zoom():
    widget = SimpleNamespace(_zoom_step=1.25, _apply_zoom=MagicMock())
    NodeGraphicsView.zoom_in(widget)
    NodeGraphicsView.zoom_out(widget)
    assert widget._apply_zoom.call_args_list[0].args == (1.25,)
    assert widget._apply_zoom.call_args_list[1].args == (0.8,)


def test_zoom_value_returns_float():
    assert NodeGraphicsView.zoom_value(SimpleNamespace(_zoom=2)) == 2.0


def test_set_zoom_value_clamps_and_applies_absolute_scale():
    widget = SimpleNamespace(
        _min_zoom=0.5,
        _max_zoom=2.0,
        _zoom=0.75,
        viewport=MagicMock(),
        mapToScene=MagicMock(),
        resetTransform=MagicMock(),
        scale=MagicMock(),
        centerOn=MagicMock(),
    )
    widget.viewport.return_value.rect.return_value.isValid.return_value = False

    NodeGraphicsView.set_zoom_value(widget, 9.0)

    widget.resetTransform.assert_called_once_with()
    widget.scale.assert_called_once_with(2.0, 2.0)
    assert widget._zoom == 2.0
    widget.centerOn.assert_not_called()


def test_set_zoom_value_can_keep_scene_center():
    center = object()
    scene_center = object()
    rect = MagicMock()
    rect.isValid.return_value = True
    rect.center.return_value = center
    viewport = MagicMock()
    viewport.rect.return_value = rect
    widget = SimpleNamespace(
        _min_zoom=0.5,
        _max_zoom=2.0,
        _zoom=1.0,
        viewport=MagicMock(return_value=viewport),
        mapToScene=MagicMock(return_value=scene_center),
        resetTransform=MagicMock(),
        scale=MagicMock(),
        centerOn=MagicMock(),
    )

    NodeGraphicsView.set_zoom_value(widget, 1.5, keep_center=True)

    widget.mapToScene.assert_called_once_with(center)
    widget.centerOn.assert_called_once_with(scene_center)


def test_scroll_values_read_and_write_both_scrollbars():
    h = _bar(10)
    v = _bar(20)
    widget = SimpleNamespace(
        horizontalScrollBar=MagicMock(return_value=h),
        verticalScrollBar=MagicMock(return_value=v),
    )
    assert NodeGraphicsView.get_scroll_values(widget) == (10, 20)
    NodeGraphicsView.set_scroll_values(widget, "7", 9.5)
    h.setValue.assert_called_once_with(7)
    v.setValue.assert_called_once_with(9)


def test_view_state_collects_zoom_and_scroll_values():
    widget = SimpleNamespace(_zoom=1.25, get_scroll_values=MagicMock(return_value=(3, 4)))
    assert NodeGraphicsView.view_state(widget) == {"zoom": 1.25, "h": 3, "v": 4}


@pytest.mark.parametrize(
    "state, zoom_call, scroll_call",
    [
        ({"zoom": 1.5, "h": 3, "v": 4}, 1.5, (3, 4)),
        ({"scale": 2, "hScroll": 8, "vScroll": 9}, 2.0, (8, 9)),
        ({"x": 5}, None, (5, 0)),
        ({"y": 6}, None, (11, 6)),
    ],
)
def test_set_view_state_supports_aliases(state, zoom_call, scroll_call):
    widget = SimpleNamespace(
        set_zoom_value=MagicMock(),
        set_scroll_values=MagicMock(),
        get_scroll_values=MagicMock(return_value=(11, 12)),
    )
    NodeGraphicsView.set_view_state(widget, state)
    if zoom_call is None:
        widget.set_zoom_value.assert_not_called()
    else:
        widget.set_zoom_value.assert_called_once_with(zoom_call, keep_center=False)
    widget.set_scroll_values.assert_called_once_with(*scroll_call)


def test_set_view_state_ignores_non_dict():
    widget = SimpleNamespace(set_zoom_value=MagicMock(), set_scroll_values=MagicMock())
    NodeGraphicsView.set_view_state(widget, None)
    widget.set_zoom_value.assert_not_called()
    widget.set_scroll_values.assert_not_called()


def test_begin_and_end_pan_manage_state_cursor_and_event():
    event = MagicMock()
    pos = object()
    event.position.return_value = pos
    viewport = MagicMock()
    widget = SimpleNamespace(
        _panning=False,
        _last_pan_pos=None,
        _global_grab_mode=False,
        viewport=MagicMock(return_value=viewport),
    )
    NodeGraphicsView._begin_pan(widget, event)
    assert widget._panning is True
    assert widget._last_pan_pos is pos
    event.accept.assert_called_once_with()

    event.accept.reset_mock()
    NodeGraphicsView._end_pan(widget, event)
    assert widget._panning is False
    event.accept.assert_called_once_with()


def test_clicked_on_empty_handles_hit_and_lookup_failure():
    pos = MagicMock()
    pos.x.return_value = 4.7
    pos.y.return_value = 8.2
    event = MagicMock()
    event.position.return_value = pos
    widget = SimpleNamespace(itemAt=MagicMock(return_value=None))
    assert NodeGraphicsView._clicked_on_empty(widget, event) is True
    widget.itemAt.assert_called_once_with(4, 8)

    widget.itemAt.side_effect = RuntimeError("boom")
    assert NodeGraphicsView._clicked_on_empty(widget, event) is False


def test_global_grab_mode_updates_state_and_cursor():
    viewport = MagicMock()
    widget = SimpleNamespace(_global_grab_mode=False, _panning=False, viewport=MagicMock(return_value=viewport))
    NodeGraphicsView.set_global_grab_mode(widget, True)
    assert widget._global_grab_mode is True
    assert viewport.setCursor.called

    viewport.setCursor.reset_mock()
    NodeGraphicsView.set_global_grab_mode(widget, False)
    assert widget._global_grab_mode is False
    assert viewport.setCursor.called


def test_scene_context_menu_emits_for_empty_scene_when_editing_allowed():
    event = MagicMock()
    scene_pos = object()
    event.scenePos.return_value = scene_pos
    editor = SimpleNamespace(editing_allowed=MagicMock(return_value=True))
    signal = MagicMock()
    widget = SimpleNamespace(
        views=MagicMock(return_value=[]),
        itemAt=MagicMock(return_value=None),
        parent=MagicMock(return_value=editor),
        sceneContextRequested=signal,
    )

    NodeGraphicsScene.contextMenuEvent(widget, event)

    signal.emit.assert_called_once_with(scene_pos)
    event.accept.assert_called_once_with()


def test_scene_context_menu_does_not_emit_when_editing_denied():
    event = MagicMock()
    editor = SimpleNamespace(editing_allowed=MagicMock(return_value=False))
    signal = MagicMock()
    widget = SimpleNamespace(
        views=MagicMock(return_value=[]),
        itemAt=MagicMock(return_value=None),
        parent=MagicMock(return_value=editor),
        sceneContextRequested=signal,
    )
    NodeGraphicsScene.contextMenuEvent(widget, event)
    signal.emit.assert_not_called()
    event.accept.assert_called_once_with()
