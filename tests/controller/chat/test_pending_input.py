from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from pygpt_net.controller.chat.input import Input
from pygpt_net.ui.layout.chat.input import PendingInputBar


def make_input():
    window = MagicMock()
    window.controller.realtime.is_enabled.return_value = False
    window.core.plugins.get.return_value.handler_simple.is_recording = False
    window.ui.nodes = {'input': MagicMock(), 'input.pending': MagicMock()}
    window.ui.nodes['input'].toPlainText.return_value = 'change direction'
    window.ui.nodes['input'].serialize_mentions.return_value = 'durable direction'
    window.controller.tabs.get_effective_current_pid.return_value = 7
    controller = Input(window)
    controller.generating = True
    return controller, window


def test_busy_send_stages_without_stopping_or_claiming_request():
    controller, window = make_input()
    controller.send_input()
    assert controller.pending == {'display': 'change direction', 'text': 'durable direction', 'pid': 7}
    window.ui.nodes['input'].clear.assert_called_once()
    window.controller.kernel.stop.assert_not_called()
    window.dispatch.assert_not_called()
    window.core.ctx.output.begin_request.assert_not_called()


def test_second_send_does_not_overwrite_pending_or_clear_new_draft():
    controller, window = make_input()
    controller.send_input()
    first = controller.pending.copy()
    window.ui.nodes['input'].toPlainText.return_value = 'another draft'
    controller.send_input()
    assert controller.pending == first
    assert window.ui.nodes['input'].clear.call_count == 1
    controller.cancel_pending()
    assert controller.pending is None


def test_send_pending_waits_for_bridge_and_stream_before_resuming():
    controller, window = make_input()
    controller.send_input()
    bridge_done, stream_done = Event(), Event()
    window.core.bridge.worker = SimpleNamespace(execution_done=bridge_done)
    window.controller.chat.stream.pids = {7: {'worker': SimpleNamespace(execution_done=stream_done)}}
    ctx = SimpleNamespace(mode='agent_v2', extra={})
    window.core.ctx.get_last_item.return_value = ctx
    scheduled = []
    controller.send_input = MagicMock()
    with patch('pygpt_net.controller.chat.input.QTimer.singleShot', side_effect=lambda ms, cb: scheduled.append(cb)):
        controller.send_pending()
        controller.send_pending()
        window.controller.kernel.stop.assert_called_once()
        assert ctx.extra['user_steered'] is True
        assert controller._pending_sending
        bridge_done.set()
        scheduled.pop(0)()
        controller.send_input.assert_not_called()
        stream_done.set()
        scheduled.pop(0)()
        controller.send_input.assert_not_called()
        scheduled.pop(0)()
    controller.send_input.assert_called_once_with(_submission={
        'display': 'change direction', 'text': 'durable direction', 'pid': 7})
    assert controller.pending is None


def test_pending_bar_elides_and_can_cancel(qt_application):
    controller, window = make_input()
    window.controller.chat.input = controller
    bar = PendingInputBar(window)
    window.ui.nodes['input.pending'] = bar
    bar.resize(340, 40)
    controller.pending = {'display': '<long message> ' * 40}
    controller._show_pending()
    bar.layout().activate()
    bar._elide()
    assert bar.isVisible()
    assert len(bar.preview.text()) < len(controller.pending['display'])
    assert bar.preview.toolTip() == controller.pending['display']
    bar.cancel.click()
    assert controller.pending is None
    assert not bar.isVisible()
    bar.close()


def test_pending_submit_keeps_new_draft_and_uses_original_chat_and_durable_text():
    from pygpt_net.core.events import KernelEvent
    controller, window = make_input()
    controller.generating = False
    window.core.ctx.output.has_request.return_value = False
    window.controller.kernel.stopped.return_value = False
    window.ui.nodes['input'].toPlainText.return_value = 'new draft'
    controller._pin_user_chat = MagicMock(return_value=SimpleNamespace(id=11))
    controller._start_preprocessing = MagicMock()
    events = []

    def dispatch(event):
        events.append(event)
        if event.name == KernelEvent.SEND_INIT:
            controller.generating = True
            window.core.ctx.output.has_request.return_value = True

    window.dispatch.side_effect = dispatch
    controller.send_input(_submission={'display': 'queued', 'text': 'durable queued', 'pid': 7})
    controller._pin_user_chat.assert_called_once_with(7)
    assert controller._start_preprocessing.call_args.args[1] == 'durable queued'
    init = next(event for event in events if event.name == KernelEvent.SEND_INIT)
    assert init.data['clear'] is False
    window.ui.nodes['input'].clear.assert_not_called()


def test_pending_overlay_positions_above_composer_without_resizing_splitter(qt_application, monkeypatch):
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtWidgets import QSplitter, QWidget
    from pygpt_net.ui.layout.chat.input import ChatInputContainer

    controller, window = make_input()
    host = QWidget()
    splitter = QSplitter(Qt.Vertical, host)
    splitter.addWidget(QWidget())
    root = QWidget()
    splitter.addWidget(root)
    # Real hidden widgets provide parent relationships; visibility and content
    # coordinates are controlled without showing windows or processing events.
    monkeypatch.setattr(root, 'isVisible', lambda: True)
    content = SimpleNamespace(mapTo=lambda parent, point: QPoint(40, 300), width=lambda: 500)
    composer = ChatInputContainer(window, QWidget())
    composer.content_widget = content
    window.ui.nodes.update({'input.root': root, 'input.container': composer})
    bar = PendingInputBar(window)
    bar.active = True
    original_sizes = splitter.sizes()
    original_root_geometry = root.geometry()
    bar.sync_position()
    assert bar.parentWidget() is host
    assert bar.x() == 40
    assert bar.y() + bar.height() == 300
    assert bar.width() == 500
    assert splitter.sizes() == original_sizes
    assert splitter.count() == 2
    assert root.geometry() == original_root_geometry
    bar.close()
    composer.close()
    host.close()
