from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.element.status import BottomStatus


def test_status_text_uses_mocked_clock_not_local_timezone():
    timer = MagicMock()
    msg = MagicMock()
    widget = SimpleNamespace(timer=timer, msg=msg)
    fixed = datetime(2026, 9, 6, 12, 34, 56)

    with patch("pygpt_net.ui.widget.element.status.datetime") as dt:
        dt.now.return_value = fixed
        BottomStatus.set_text(widget, "Ready")

    msg.setText.assert_called_once_with("Ready")
    timer.setText.assert_called_once_with("12:34")


def test_empty_status_clears_timer_without_reading_clock():
    timer = MagicMock()
    msg = MagicMock()
    widget = SimpleNamespace(timer=timer, msg=msg)

    with patch("pygpt_net.ui.widget.element.status.datetime") as dt:
        BottomStatus.set_text(widget, "")

    dt.now.assert_not_called()
    timer.setText.assert_called_once_with("")


def test_status_settext_alias_and_text_accessor():
    widget = SimpleNamespace(set_text=MagicMock(), msg=MagicMock())
    widget.msg.text.return_value = "Current"

    BottomStatus.setText(widget, "Next")

    widget.set_text.assert_called_once_with("Next")
    assert BottomStatus.text(widget) == "Current"


def test_status_layout_places_right_aligned_message_before_time(qapp, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget
    monkeypatch.setattr('pygpt_net.ui.widget.element.status.trans', lambda key: key)
    window = QWidget()
    status = BottomStatus(window)
    widget = status.setup()
    assert widget.layout().itemAt(0).widget() is status.msg
    assert widget.layout().itemAt(1).widget() is status.timer
    assert status.msg.alignment() & Qt.AlignRight
    assert widget.layout().spacing() == 12
    widget.deleteLater()
    window.deleteLater()


def test_plugin_counters_are_separate_from_composer_metadata(qapp):
    from PySide6.QtWidgets import QLabel
    from pygpt_net.ui.layout.chat.input import Input
    keys = ('chat.plugins', 'chat.mcp', 'chat.skills', 'chat.annotations', 'inline.vision')
    nodes = {key: QLabel(key) for key in keys}
    schedule = QLabel('schedule')
    builder = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(
        nodes=nodes, plugin_addon={'schedule': schedule})), STATUS_ITEM_SPACING=8)
    metadata = Input._setup_footer_metadata(builder)
    assert metadata.itemAt(0).widget() is schedule
    assert metadata.count() == 2  # schedule plus its spacing
    counters = Input._setup_status_counters(builder)
    assert counters.layout().spacing() == 8
    assert [counters.layout().itemAt(i).widget() for i in range(5)] == [nodes[key] for key in keys]
    counters.deleteLater()
