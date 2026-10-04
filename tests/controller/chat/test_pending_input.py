from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

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


def test_pending_bar_elides_and_can_cancel():
    app = QApplication.instance() or QApplication([])
    controller, window = make_input()
    window.controller.chat.input = controller
    bar = PendingInputBar(window)
    window.ui.nodes['input.pending'] = bar
    bar.resize(340, 40)
    controller.pending = {'display': '<long message> ' * 40}
    controller._show_pending()
    app.processEvents()
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


def test_pending_overlay_preserves_real_composer_geometry_and_splitter_sizes():
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout, QTextEdit
    from pygpt_net.ui.layout.chat.input import ChatInputContainer, ChatInputRootContainer
    from pygpt_net.ui.widget.tabs.Input import ChatComposer

    app = QApplication.instance() or QApplication([])
    controller, window = make_input()
    host = QWidget()
    host_layout = QVBoxLayout(host)
    splitter = QSplitter(Qt.Vertical)
    host_layout.addWidget(splitter)
    splitter.addWidget(QWidget())
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    editor = QTextEdit()
    editor.setMinimumHeight(100)
    page = QWidget()
    QVBoxLayout(page).addWidget(editor)
    layout.addWidget(ChatComposer(None, page, QWidget()))
    composer = ChatInputContainer(window, content)
    composer._ensure_columns_splitter_hook = lambda: None
    composer._active_chat_column_idx = lambda: 0
    composer._column_area = lambda col, width: (0, width)
    composer._is_wide_style = lambda: True
    root = ChatInputRootContainer(composer)
    root.setMaximumHeight(220)
    input_host = QWidget()
    input_layout = QVBoxLayout(input_host)
    input_layout.setContentsMargins(0, 0, 0, 0)
    input_layout.addWidget(root)
    splitter.addWidget(input_host)
    window.ui.splitters = {'main.output': splitter}
    window.ui.nodes.update({'input': editor, 'input.root': root, 'input.container': composer})
    bar = PendingInputBar(window)
    window.ui.nodes['input.pending'] = bar
    host.resize(700, 600)
    splitter.setSizes([380, 220])
    host.show()
    app.processEvents()
    original_y = editor.mapToGlobal(QPoint()).y()
    original_height = editor.height()
    original_sizes = splitter.sizes()
    for payload in ({'display': 'queued message'}, {'display': 'updated'}, None):
        bar.set_pending(payload)
        app.processEvents()
        app.processEvents()
        assert editor.mapToGlobal(QPoint()).y() == original_y
        assert editor.height() == original_height
        assert splitter.sizes() == original_sizes
        assert splitter.count() == 2
        if payload:
            assert bar.parentWidget() is host
            assert bar.mapToGlobal(QPoint(0, bar.height())).y() <= editor.mapToGlobal(QPoint()).y()
    host.close()
