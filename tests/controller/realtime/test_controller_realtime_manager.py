from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.realtime.manager import Manager


def test_realtime_manager_start_stores_state_and_starts_worker():
    window = MagicMock()
    manager = Manager(window)
    ctx = MagicMock(name="ctx")
    opts = SimpleNamespace(provider="openai", model="gpt-test")
    worker = MagicMock(name="worker")

    with patch("pygpt_net.controller.realtime.manager.RealtimeWorker", return_value=worker) as worker_cls:
        manager.start(ctx, opts)

    worker_cls.assert_called_once_with(window, ctx, opts)
    assert manager.ctx is ctx
    assert manager.opts is opts
    assert manager.provider == "openai"
    assert manager.worker is worker
    window.core.debug.info.assert_called_once_with("[realtime] Begin: provider=openai, model=gpt-test")
    window.threadpool.start.assert_called_once_with(worker)


def test_realtime_manager_shutdown_drops_worker_reference_only():
    manager = Manager(MagicMock())
    manager.worker = MagicMock()
    manager.ctx = MagicMock()

    manager.shutdown()

    assert manager.worker is None
    assert manager.ctx is not None
