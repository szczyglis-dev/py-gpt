from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.worker.worker import Worker


def test_worker_run_calls_function_and_cleans_signals():
    fn = MagicMock()
    worker = Worker(fn, 1, key=2)
    signal_obj = SimpleNamespace(deleteLater=MagicMock())
    worker.signals = signal_obj
    worker.run()
    fn.assert_called_once_with(1, key=2)
    signal_obj.deleteLater.assert_called_once_with()
    assert worker.signals is None


def test_worker_run_swallows_function_exception_and_still_cleans():
    worker = Worker(MagicMock(side_effect=RuntimeError("boom")))
    signal_obj = SimpleNamespace(deleteLater=MagicMock())
    worker.signals = signal_obj
    worker.run()
    signal_obj.deleteLater.assert_called_once_with()
    assert worker.signals is None


def test_cleanup_tolerates_runtime_error_from_qobject_delete():
    worker = Worker(lambda: None)
    signal_obj = SimpleNamespace(deleteLater=MagicMock(side_effect=RuntimeError("already deleted")))
    worker.signals = signal_obj
    worker.cleanup()
    assert worker.signals is None
