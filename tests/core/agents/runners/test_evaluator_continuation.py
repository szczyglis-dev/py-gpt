import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from pygpt_net.controller.kernel.kernel import Kernel
from pygpt_net.core.agents.runners.loop import Loop
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem


@pytest.mark.parametrize("stop_before_delivery", [False, True])
def test_evaluator_resumes_on_gui_thread(stop_before_delivery):
    app = QApplication.instance() or QApplication([])
    ui_thread = threading.get_ident()
    events = []
    window = SimpleNamespace(core=SimpleNamespace(config={"agent.llama.loop.score": 100}))
    kernel = Kernel(window)
    window.controller = SimpleNamespace(kernel=kernel)

    def dispatch(event):
        assert threading.get_ident() == ui_thread
        events.append(event)
        if event.name == KernelEvent.AGENT_CONTINUE:
            kernel.queue(event.data["context"], event.data["extra"], event)

    window.dispatch = dispatch
    signals = BridgeSignals()
    # Use the same connection as Bridge.get_worker(), including the actual
    # non-QObject Kernel listener rather than a mocked signal receiver.
    signals.response.connect(kernel.listener)
    loop = Loop(window)
    loop.is_stopped = lambda: False
    loop.set_busy = Mock()
    loop.set_status = Mock()
    ctx = CtxItem()
    errors = []

    def evaluate():
        try:
            assert loop.handle_evaluation(ctx, "Add examples", 90, signals)
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=evaluate)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert not errors
    assert events == []  # worker only queues, never touches chat/UI directly
    kernel.halt = stop_before_delivery
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        app.processEvents()
        if stop_before_delivery or any(e.name == KernelEvent.INPUT_SYSTEM for e in events):
            break
    continuations = [e for e in events if e.name == KernelEvent.INPUT_SYSTEM]
    if stop_before_delivery:
        assert not continuations
        assert not kernel.stack.has()
    else:
        assert len(continuations) == 1
        event = continuations[0]
        assert event.data["context"].ctx is ctx
        assert event.data["context"].prompt == "Add examples"
        assert event.data["extra"]["agent_continue"] is True
        assert "Add examples" in event.data["extra"]["inline_message"]["text"]
        app.processEvents()
        assert len([e for e in events if e.name == KernelEvent.INPUT_SYSTEM]) == 1


def test_ordinary_continuation_waits_for_output_lifecycle():
    window = SimpleNamespace()
    kernel = Kernel(window)
    kernel.stack = Mock()
    context = SimpleNamespace(reply_context=object())
    kernel.queue(context, {}, KernelEvent(KernelEvent.AGENT_CONTINUE))
    kernel.stack.add.assert_called_once_with(context.reply_context)
    kernel.stack.handle.assert_not_called()
