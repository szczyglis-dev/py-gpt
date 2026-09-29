from unittest.mock import MagicMock

from PySide6.QtCore import QRect, QSize, Qt

from pygpt_net.ui.base.flow_layout import FlowLayout


def _layout_item(width, height, spacing=0):
    item = MagicMock()
    item.sizeHint.return_value = QSize(width, height)
    item.minimumSize.return_value = QSize(width, height)
    widget = item.widget.return_value
    widget.style.return_value.layoutSpacing.return_value = spacing
    return item


def test_flow_layout_add_take_and_bounds(qapp):
    layout = FlowLayout(spacing=5)
    first = _layout_item(10, 20)
    second = _layout_item(30, 15)

    layout.addItem(first)
    layout.addItem(second)

    assert layout.count() == 2
    assert layout.itemAt(0) is first
    assert layout.itemAt(-1) is None
    assert layout.itemAt(5) is None
    assert layout.takeAt(0) is first
    assert layout.count() == 1
    assert layout.takeAt(9) is None


def test_flow_layout_minimum_size_uses_largest_item_and_margins(qapp):
    layout = FlowLayout(spacing=5)
    layout.setContentsMargins(1, 2, 3, 4)
    layout.addItem(_layout_item(10, 20))
    layout.addItem(_layout_item(30, 15))

    size = layout.minimumSize()

    assert size.width() == 34
    assert size.height() == 26
    assert layout.sizeHint() == size
    assert layout.hasHeightForWidth() is True


def test_flow_layout_wraps_items_and_test_mode_does_not_set_geometry(qapp):
    layout = FlowLayout(spacing=5)
    first = _layout_item(40, 10)
    second = _layout_item(40, 20)
    layout.addItem(first)
    layout.addItem(second)

    height = layout.doLayout(QRect(0, 0, 60, 0), False)

    assert height == 35
    assert first.setGeometry.call_count == 1
    assert second.setGeometry.call_count == 1

    first.reset_mock()
    second.reset_mock()
    measured = layout.doLayout(QRect(0, 0, 60, 0), True)

    assert measured == 35
    first.setGeometry.assert_not_called()
    second.setGeometry.assert_not_called()
    assert layout.heightForWidth(60) == 35


def test_flow_layout_reports_no_expanding_directions(qapp):
    layout = FlowLayout()
    assert layout.expandingDirections() == Qt.Orientations(0)


def test_flow_layout_set_geometry_applies_item_geometry(qapp):
    layout = FlowLayout(spacing=0)
    item = _layout_item(20, 10)
    layout.addItem(item)

    layout.setGeometry(QRect(0, 0, 100, 40))

    item.setGeometry.assert_called_once()
