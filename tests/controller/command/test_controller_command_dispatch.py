from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.command.command import Command
from pygpt_net.core.events import Event, KernelEvent


def _command(ids=('a', 'b')):
    window = MagicMock()
    window.core.plugins.get_ids.return_value = list(ids)
    window.controller.plugins.is_enabled.return_value = True
    window.core.debug.enabled.return_value = False
    return Command(window), window


def test_command_dispatch_flushes_reply_stack_and_applies_enabled_plugins():
    ctrl, window = _command()
    event = Event(Event.CMD_EXECUTE)

    ctrl.dispatch(event)

    window.controller.kernel.replies.clear.assert_called_once_with()
    assert window.core.dispatcher.apply.call_count == 2
    window.controller.kernel.replies.flush.assert_called_once_with()


def test_command_dispatch_all_execute_only_forces_disabled_plugins_only_for_execute():
    ctrl, window = _command(('disabled',))
    window.controller.plugins.is_enabled.return_value = False

    ctrl.dispatch(Event(Event.CMD_EXECUTE), all=True, execute_only=True)
    window.core.dispatcher.apply.assert_called_once()

    window.core.dispatcher.apply.reset_mock()
    ctrl.dispatch(Event(Event.CMD_INLINE), all=True, execute_only=True)
    window.core.dispatcher.apply.assert_not_called()


def test_command_dispatch_only_ignores_plugin_enabled_state():
    ctrl, window = _command(('a', 'b'))
    event = Event(Event.CMD_EXECUTE)
    ctrl.dispatch_only(event)
    assert window.core.dispatcher.apply.call_count == 2


def test_command_worker_emits_and_disconnects_finished_signal():
    ctrl, window = _command(('a',))
    signal = MagicMock()
    event = Event(Event.CMD_EXECUTE)

    ctrl.worker(event, window, signal)

    window.core.dispatcher.apply.assert_called_once_with('a', event, is_async=True)
    signal.emit.assert_called_once_with(event)
    signal.disconnect.assert_called_once_with()


def test_command_dispatch_async_builds_external_worker_without_running_it():
    ctrl, window = _command()
    worker = MagicMock()
    worker.kwargs = {}
    worker.signals = MagicMock()
    with patch('pygpt_net.controller.command.command.Worker', return_value=worker), \
         patch('pygpt_net.controller.command.command.WorkerSignals', return_value=MagicMock()):
        event = Event(Event.CMD_EXECUTE)
        ctrl.dispatch_async(event)
    window.threadpool.start.assert_called_once_with(worker)
    assert worker.kwargs['event'] is event
    assert worker.kwargs['window'] is window


def test_command_handle_finished_dispatches_kernel_reply_context():
    ctrl, window = _command()
    ctx = SimpleNamespace(reply=True, results={'ok': True}, extra_ctx='', internal=True)
    event = SimpleNamespace(ctx=ctx)
    previous = object()
    window.core.ctx.as_previous.return_value = previous

    ctrl.handle_finished(event)

    dispatched = window.dispatch.call_args.args[0]
    assert isinstance(dispatched, KernelEvent)
    assert dispatched.name == KernelEvent.INPUT_SYSTEM
    assert dispatched.data['context'].ctx is previous
    assert dispatched.data['context'].prompt == '{"ok": true}'
    assert dispatched.data['extra'] == {'force': True, 'internal': True}


def test_command_stop_and_debug_helpers():
    ctrl, window = _command()
    ctrl.stop = True
    assert ctrl.is_stop() is True
    ctrl.handle_debug('x')
    window.core.debug.info.assert_called_with('x')
