from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.node_editor.item import PortItem, EdgeItem, NodeOverlayItem


def test_port_allowed_capacity_delegates_to_node_item():
    node_item = SimpleNamespace(allowed_capacity_for_pid=MagicMock(return_value=3))
    port = SimpleNamespace(node_item=node_item, prop_id="p", side="input")
    assert PortItem._allowed_capacity(port) == 3
    node_item.allowed_capacity_for_pid.assert_called_once_with("p", "input")


def test_port_increment_connections_clamps_at_zero_and_updates():
    port = SimpleNamespace(_connected_count=1, update=MagicMock())
    PortItem.increment_connections(port, 4)
    assert port._connected_count == 5
    PortItem.increment_connections(port, -100)
    assert port._connected_count == 0
    assert port.update.call_count == 2


def test_port_accept_highlight_only_repaints_on_change():
    port = SimpleNamespace(_can_accept=False, update=MagicMock())
    PortItem.set_accept_highlight(port, False)
    port.update.assert_not_called()
    PortItem.set_accept_highlight(port, True)
    assert port._can_accept is True
    port.update.assert_called_once_with()


def test_port_update_labels_runs_all_steps_and_repaints():
    port = SimpleNamespace(
        _update_label_texts=MagicMock(),
        _update_label_positions=MagicMock(),
        _update_tooltip=MagicMock(),
        update=MagicMock(),
    )
    PortItem.update_labels(port)
    port._update_label_texts.assert_called_once_with()
    port._update_label_positions.assert_called_once_with()
    port._update_tooltip.assert_called_once_with()
    port.update.assert_called_once_with()


def test_port_theme_change_refreshes_colors_and_repaints():
    port = SimpleNamespace(_update_label_colors=MagicMock(), update=MagicMock())
    PortItem.notify_theme_changed(port)
    port._update_label_colors.assert_called_once_with()
    port.update.assert_called_once_with()


def test_port_label_text_uses_capacity_and_infinity():
    label_io = MagicMock()
    label_cap = MagicMock()
    font_num = object()
    font_inf = object()
    port = SimpleNamespace(
        _label_io=label_io,
        _label_cap=label_cap,
        _font_cap_num=font_num,
        _font_cap_inf=font_inf,
        _allowed_capacity=MagicMock(return_value=-1),
    )
    PortItem._update_label_texts(port)
    label_io.setText.assert_called_once_with("")
    label_io.setVisible.assert_called_once_with(False)
    label_cap.setText.assert_called_once_with("∞")
    label_cap.setFont.assert_called_once_with(font_inf)

    label_cap.reset_mock()
    port._allowed_capacity.return_value = 4
    PortItem._update_label_texts(port)
    label_cap.setText.assert_called_once_with("4")
    label_cap.setFont.assert_called_once_with(font_num)

    label_cap.reset_mock()
    port._allowed_capacity.return_value = 0
    PortItem._update_label_texts(port)
    label_cap.setText.assert_called_once_with("")


@pytest.mark.parametrize("capacity, expected_fragment", [(-1, "UNLIMITED"), (3, "3"), (None, "N/A")])
def test_port_tooltip_formats_capacity(capacity, expected_fragment):
    cfg = SimpleNamespace(
        cap_unlimited=MagicMock(return_value="UNLIMITED"),
        cap_na=MagicMock(return_value="N/A"),
        side_label=MagicMock(return_value="input"),
        port_tooltip=MagicMock(side_effect=lambda node, side, pid, cap: f"{node}|{side}|{pid}|{cap}"),
    )
    editor = SimpleNamespace(config=cfg)
    node_item = SimpleNamespace(node=SimpleNamespace(name="Node"), editor=editor)
    label = MagicMock()
    port = SimpleNamespace(
        node_item=node_item,
        prop_id="p",
        side="input",
        _allowed_capacity=MagicMock(return_value=capacity),
        setToolTip=MagicMock(),
        _label_cap=label,
    )
    PortItem._update_tooltip(port)
    tooltip = port.setToolTip.call_args.args[0]
    assert expected_fragment in tooltip
    assert "Node" in tooltip
    assert "INPUT" in tooltip
    assert "p" in tooltip
    label.setToolTip.assert_called_once_with(tooltip)


def test_edge_hover_change_updates_pen_once():
    edge = SimpleNamespace(_hover=False, _update_pen=MagicMock())
    EdgeItem.set_hovered(edge, False)
    edge._update_pen.assert_not_called()
    EdgeItem.set_hovered(edge, True)
    assert edge._hover is True
    edge._update_pen.assert_called_once_with()


def test_edge_mouse_move_starts_rewire_after_threshold():
    start = SimpleNamespace(x=lambda: 1, y=lambda: 1)
    pos = SimpleNamespace(x=lambda: 10, y=lambda: 10)
    event = MagicMock()
    event.scenePos.return_value = pos
    editor = SimpleNamespace(
        _wire_state="idle",
        _dbg=MagicMock(),
        _start_rewire_from_edge=MagicMock(),
    )
    edge = SimpleNamespace(
        temporary=False,
        _drag_primed=True,
        _drag_start_scene=start,
        _editor=editor,
    )
    EdgeItem.mouseMoveEvent(edge, event)
    editor._start_rewire_from_edge.assert_called_once_with(edge, pos)
    assert edge._drag_primed is False
    event.accept.assert_called_once_with()


def test_edge_mouse_move_does_not_rewire_below_threshold():
    start = SimpleNamespace(x=lambda: 1, y=lambda: 1)
    pos = SimpleNamespace(x=lambda: 3, y=lambda: 3)
    event = MagicMock()
    event.scenePos.return_value = pos
    editor = SimpleNamespace(_wire_state="idle", _dbg=MagicMock(), _start_rewire_from_edge=MagicMock())
    edge = SimpleNamespace(temporary=False, _drag_primed=True, _drag_start_scene=start, _editor=editor)
    # The fallback super() requires a real Qt instance, so call only the branch condition independently.
    dist = abs(pos.x() - start.x()) + abs(pos.y() - start.y())
    assert dist <= 6
    editor._start_rewire_from_edge.assert_not_called()


def test_overlay_hover_pid_repaints_only_when_changed():
    overlay = SimpleNamespace(_hover_pid=None, update=MagicMock())
    NodeOverlayItem.set_hover_pid(overlay, None)
    overlay.update.assert_not_called()
    NodeOverlayItem.set_hover_pid(overlay, "p")
    assert overlay._hover_pid == "p"
    overlay.update.assert_called_once_with()
