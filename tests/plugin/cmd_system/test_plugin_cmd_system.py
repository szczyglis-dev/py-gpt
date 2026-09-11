from types import ModuleType
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.cmd_system import Plugin
from pygpt_net.plugin.cmd_system.output import Output
from pygpt_net.plugin.cmd_system.worker import Worker
from tests.mocks import mock_window


def test_system_defaults_include_new_attach_output_option(mock_window):
    plugin = Plugin(window=mock_window)
    options = plugin.setup()
    assert options["sandbox_docker"]["value"] is False
    assert options["attach_output"]["value"] is True
    assert options["winapi_enabled"]["value"] is True
    assert plugin.has_cmd("sys_exec") is True


def test_migrate_docker_defaults_delegates(mock_window):
    plugin = Plugin(window=mock_window)
    with patch("pygpt_net.plugin.cmd_system.plugin.migrate_default_dockerfile", return_value=True) as migrate:
        assert plugin.migrate_docker_defaults() is True
    migrate.assert_called_once()
    assert migrate.call_args.args[0] is plugin
    assert migrate.call_args.args[1] == "dockerfile"


def test_cmd_syntax_linux_hides_winapi_and_appends_cwd(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.platforms.get_as_string.return_value = "Linux"
    mock_window.core.config.get_user_dir = MagicMock(return_value="/tmp/data")
    mock_window.core.filesystem.get_data_dir = MagicMock(return_value="/tmp/data")
    plugin.set_option_value("auto_cwd", True)
    plugin.set_option_value("sandbox_docker", False)
    with patch("pygpt_net.plugin.cmd_system.plugin.platform.system", return_value="Linux"):
        data = {"cmd": []}
        plugin.cmd_syntax(data)
    assert [x["cmd"] for x in data["cmd"]] == ["sys_exec"]
    assert "Current workdir is: /tmp/data" in data["cmd"][0]["instruction"]
    assert "Current OS is: Linux" in data["cmd"][0]["instruction"]


def test_cmd_syntax_windows_includes_enabled_winapi_commands(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.platforms.get_as_string.return_value = "Windows"
    mock_window.core.config.get_user_dir = MagicMock(return_value=r"C:\\data")
    plugin.set_option_value("winapi_enabled", True)
    with patch("pygpt_net.plugin.cmd_system.plugin.platform.system", return_value="Windows"):
        data = {"cmd": []}
        plugin.cmd_syntax(data)
    names = [x["cmd"] for x in data["cmd"]]
    assert "sys_exec" in names
    assert "win_list" in names
    assert "win_monitors" in names


def test_cmd_syntax_sandbox_instruction_reflects_root_mode(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.platforms.get_as_string.return_value = "Linux"
    mock_window.core.config.get_user_dir = MagicMock(return_value="/data")
    plugin.set_option_value("sandbox_docker", True)
    plugin.set_option_value("docker_run_as_root", True)
    with patch("pygpt_net.plugin.cmd_system.plugin.platform.system", return_value="Linux"):
        data = {"cmd": []}
        plugin.cmd_syntax(data)
    assert "sudo is not required" in data["cmd"][0]["instruction"]


def test_handle_routes_execute_and_tool_output(mock_window):
    plugin = Plugin(window=mock_window)
    ctx = CtxItem()
    plugin.cmd = MagicMock()
    event = Event()
    event.name = Event.CMD_EXECUTE
    event.ctx = ctx
    event.data = {"commands": [{"cmd": "sys_exec", "params": {}}], "silent": True}
    plugin.handle(event)
    plugin.cmd.assert_called_once_with(ctx, event.data["commands"], True)

    plugin.output.handle = MagicMock(return_value="<html>")
    event.name = Event.TOOL_OUTPUT_RENDER
    event.data = {"tool": plugin.id, "content": {"code": {}}, "html": ""}
    plugin.handle(event)
    assert event.data["html"] == ""
    plugin.output.handle.assert_not_called()


def test_cmd_ignores_unrelated_commands(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_prepare = MagicMock()
    plugin.cmd(CtxItem(), [{"cmd": "other", "params": {}}])
    plugin.cmd_prepare.assert_not_called()


def test_cmd_sandbox_requires_docker_without_starting_worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox_docker", True)
    plugin.docker.is_docker_installed = MagicMock(return_value=False)
    mock_window.core.platforms.is_snap.return_value = False
    plugin.error = MagicMock()
    with patch("pygpt_net.plugin.cmd_system.plugin.trans", side_effect=lambda x: x):
        plugin.cmd(CtxItem(), [{"cmd": "sys_exec", "params": {"command": "echo x"}}])
    plugin.error.assert_called_once_with("docker.install")
    mock_window.update_status.assert_called_once_with("docker.install")


def test_cmd_sandbox_builds_missing_image(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox_docker", True)
    plugin.docker.is_docker_installed = MagicMock(return_value=True)
    plugin.docker.is_image = MagicMock(return_value=False)
    plugin.docker.build = MagicMock()
    plugin.error = MagicMock()
    with patch("pygpt_net.plugin.cmd_system.plugin.trans", side_effect=lambda x: x):
        plugin.cmd(CtxItem(), [{"cmd": "sys_exec", "params": {"command": "echo x"}}])
    plugin.docker.build.assert_called_once_with()
    plugin.error.assert_called_once_with("docker.image.build")


def test_cmd_routes_sync_worker_and_connects_output_signals(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox_docker", False)
    plugin.is_async = MagicMock(return_value=False)
    plugin.cmd_prepare = MagicMock()
    plugin.runner.attach_signals = MagicMock()
    ctx = CtxItem()
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.cmd_system.worker")
    fake_mod.Worker = MagicMock(return_value=worker)
    request = {"cmd": "sys_exec", "params": {"command": "echo x"}}
    with patch.dict("sys.modules", {"pygpt_net.plugin.cmd_system.worker": fake_mod}):
        plugin.cmd(ctx, [request])
    worker.from_defaults.assert_called_once_with(plugin)
    worker.signals.output.connect.assert_called_once_with(plugin.handle_interpreter_output)
    worker.signals.output_begin.connect.assert_called_once_with(plugin.handle_interpreter_output_begin)
    worker.signals.output_end.connect.assert_called_once_with(plugin.handle_interpreter_output_end)
    plugin.runner.attach_signals.assert_called_once_with(worker.signals)
    worker.run.assert_called_once_with()


def test_force_command_uses_async_path_even_when_context_is_sync(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox_docker", False)
    plugin.is_async = MagicMock(return_value=False)
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.cmd_system.worker")
    fake_mod.Worker = MagicMock(return_value=worker)
    request = {"cmd": "sys_exec", "params": {"command": "echo x"}, "force": True}
    with patch.dict("sys.modules", {"pygpt_net.plugin.cmd_system.worker": fake_mod}):
        plugin.cmd(CtxItem(), [request])
    worker.run_async.assert_called_once_with()
    worker.run.assert_not_called()


def test_silent_command_does_not_mark_busy(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox_docker", False)
    plugin.is_async = MagicMock(return_value=False)
    plugin.cmd_prepare = MagicMock()
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.cmd_system.worker")
    fake_mod.Worker = MagicMock(return_value=worker)
    with patch.dict("sys.modules", {"pygpt_net.plugin.cmd_system.worker": fake_mod}):
        plugin.cmd(CtxItem(), [{"cmd": "sys_exec", "params": {"command": "x"}}], silent=True)
    plugin.cmd_prepare.assert_not_called()


def test_interpreter_forwarding_respects_attach_output(mock_window):
    plugin = Plugin(window=mock_window)
    interpreter = MagicMock()
    mock_window.tools.get.return_value = interpreter

    plugin.set_option_value("attach_output", False)
    plugin.handle_interpreter_output("x", "stdout")
    plugin.handle_interpreter_output_begin("stdout")
    plugin.handle_interpreter_output_end("stdout")
    mock_window.tools.get.assert_not_called()

    plugin.set_option_value("attach_output", True)
    plugin.handle_interpreter_output("x", "stdout")
    plugin.handle_interpreter_output_begin("stdout")
    plugin.handle_interpreter_output_end("stdout")
    interpreter.append_output.assert_called_once_with("x", "stdout")
    interpreter.output_begin.assert_called_once_with("stdout")
    interpreter.output_end.assert_called_once_with("stdout")


def test_output_renderer_renders_input_and_output_blocks(mock_window):
    plugin = Plugin(window=mock_window)
    parser = mock_window.controller.chat.render.instance().parser
    parser.parse_code.side_effect = ["IN", "OUT"]
    output = Output(plugin)
    html = output.handle(CtxItem(), {
        "code": {
            "input": {"lang": "bash", "content": "echo x"},
            "output": {"lang": "text", "content": "x"},
        }
    })
    assert "Input" in html and "IN" in html
    assert "Output" in html and "OUT" in html
    assert parser.parse_code.call_count == 2


def test_worker_prepare_extra_preserves_code_and_context():
    worker = Worker()
    extra = worker.prepare_extra(
        {"cmd": "sys_exec", "params": {"command": "echo x"}},
        {"result": "x", "context": "ctx"},
    )
    assert extra == {
        "plugin": "cmd_system",
        "cmd": "sys_exec",
        "code": {
            "input": {"lang": "bash", "content": "echo x"},
            "output": {"lang": "bash", "content": "x"},
        },
        "context": "ctx",
    }


def test_worker_wrap_calls_runner_and_adapts_response():
    worker = Worker()
    fn = MagicMock(return_value={"result": "ok", "context": "ctx"})
    item = {"cmd": "win_list", "params": {"limit": 5}}
    response = worker._wrap(item, fn, item["params"])
    fn.assert_called_once_with(limit=5)
    assert response["result"] == {"result": "ok", "context": "ctx"}
    assert response["cmd"] == "win_list"
    assert response["code"]["output"]["lang"] == "json"


def test_worker_cmd_sys_exec_chooses_host_or_sandbox():
    plugin = MagicMock()
    worker = Worker()
    worker.plugin = plugin
    worker.ctx = CtxItem()
    item = {"cmd": "sys_exec", "params": {"command": "echo x"}}

    plugin.runner.is_sandbox.return_value = False
    plugin.runner.sys_exec_host.return_value = {"result": "host"}
    response = worker.cmd_sys_exec(item)
    plugin.runner.sys_exec_host.assert_called_once()
    assert response["result"] == {"result": "host"}

    plugin.reset_mock()
    plugin.runner.is_sandbox.return_value = True
    plugin.runner.sys_exec_sandbox.return_value = {"result": "sandbox"}
    response = worker.cmd_sys_exec(item)
    plugin.runner.sys_exec_sandbox.assert_called_once()
    assert response["result"] == {"result": "sandbox"}


def test_worker_run_executes_enabled_sys_exec_and_cleans_up():
    plugin = MagicMock()
    plugin.allowed_cmds = ["sys_exec"]
    plugin.has_cmd.return_value = True
    worker = Worker()
    worker.plugin = plugin
    worker.cmds = [{"cmd": "sys_exec", "params": {"command": "x"}}]
    worker.is_stopped = MagicMock(return_value=False)
    worker.cmd_sys_exec = MagicMock(return_value={"result": "ok"})
    worker.reply_more = MagicMock()
    worker.cleanup = MagicMock()
    worker.run()
    worker.reply_more.assert_called_once_with([{"result": "ok"}])
    worker.cleanup.assert_called_once_with()
