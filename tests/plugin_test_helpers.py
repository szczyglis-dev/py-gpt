from types import ModuleType
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem


def assert_command_plugin_surface(plugin):
    """Exercise common command-plugin surface without touching its external worker."""
    assert plugin.id
    assert isinstance(plugin.setup(), dict)
    assert plugin.allowed_cmds

    enabled = [name for name in plugin.allowed_cmds if plugin.has_cmd(name)]
    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert [item["cmd"] for item in data["cmd"]] == enabled

    syntax_event = Event()
    syntax_event.name = Event.CMD_SYNTAX
    syntax_event.data = {"cmd": []}
    syntax_event.ctx = CtxItem()
    plugin.handle(syntax_event)
    assert [item["cmd"] for item in syntax_event.data["cmd"]] == enabled


def assert_command_plugin_worker_routing(plugin, worker_module_name):
    """Verify filtering plus sync/async worker routing using an in-memory worker module."""
    cmd = next(name for name in plugin.allowed_cmds if plugin.has_cmd(name))
    ctx = CtxItem()
    plugin.cmd_prepare = MagicMock()
    plugin.error = MagicMock()

    worker = MagicMock()
    worker_type = MagicMock(return_value=worker)
    fake_module = ModuleType(worker_module_name)
    fake_module.Worker = worker_type

    with patch.dict("sys.modules", {worker_module_name: fake_module}):
        plugin.is_async = MagicMock(return_value=False)
        plugin.cmd(ctx, [{"cmd": "foreign_command", "params": {}}])
        worker_type.assert_not_called()

        request = {"cmd": cmd, "params": {}}
        plugin.cmd(ctx, [request])
        worker_type.assert_called_once_with()
        worker.from_defaults.assert_called_once_with(plugin)
        assert worker.cmds == [request]
        assert worker.ctx is ctx
        worker.run.assert_called_once_with()
        worker.run_async.assert_not_called()
        plugin.cmd_prepare.assert_called_once_with(ctx, [request])

    worker_type.reset_mock()
    worker.reset_mock()
    plugin.cmd_prepare.reset_mock()

    with patch.dict("sys.modules", {worker_module_name: fake_module}):
        plugin.is_async = MagicMock(return_value=True)
        request = {"cmd": cmd, "params": {}}
        plugin.cmd(ctx, [request])
        worker.run_async.assert_called_once_with()
        worker.run.assert_not_called()


def assert_handle_execute_routes(plugin):
    plugin.cmd = MagicMock()
    ctx = CtxItem()
    commands = [{"cmd": "anything", "params": {}}]
    event = Event()
    event.name = Event.CMD_EXECUTE
    event.data = {"commands": commands}
    event.ctx = ctx
    plugin.handle(event)
    plugin.cmd.assert_called_once_with(ctx, commands)
