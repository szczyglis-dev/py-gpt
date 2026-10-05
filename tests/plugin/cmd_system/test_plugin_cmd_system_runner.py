import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.filesystem.os.runner import Runner
from pygpt_net.plugin.filesystem.python.runner import Runner as PythonRunner
from pygpt_net.plugin.filesystem.python.execution.host import HostBackend
from pygpt_net.plugin.filesystem.python.execution.docker import DockerBackend
from tests.mocks import mock_window


def make_runner(mock_window, runtime=False):
    plugin = MagicMock()
    plugin.window = mock_window
    plugin.get_option_value.side_effect = lambda name: {
        "sandbox": "disabled",
        "winapi_enabled": True,
    }.get(name)
    plugin.docker = MagicMock()
    plugin.is_ipython_enabled.return_value = False
    runner = PythonRunner(plugin) if runtime else Runner(plugin)
    plugin.runner = runner
    backend = HostBackend(plugin)
    plugin.get_execution_backend.return_value = backend
    return runner, plugin


def test_attach_and_interpreter_signal_helpers(mock_window):
    runner, _ = make_runner(mock_window)
    signals = MagicMock()
    runner.attach_signals(signals)
    runner.send_interpreter_input("echo x")
    signals.output_begin.emit.assert_called_once_with("stdin")
    signals.output.emit.assert_called_once_with("echo x", "stdin")
    signals.output_end.emit.assert_called_once_with("stdin")


def test_handle_result_combines_stdout_stderr_and_handles_empty(mock_window):
    runner, _ = make_runner(mock_window)
    runner.send_interpreter_output = MagicMock()
    runner.log = MagicMock()
    assert runner.handle_result(b"out", b"err") == "out\nerr"
    assert runner.handle_result(None, None) == "No result (STDOUT/STDERR empty)"


def test_handle_result_docker_decodes_and_logs(mock_window):
    runner, _ = make_runner(mock_window)
    runner.send_interpreter_output = MagicMock()
    runner.log = MagicMock()
    assert runner.handle_result_docker(b"hello") == "hello"
    runner.send_interpreter_output.assert_called_once_with("hello", "stdout")


def test_docker_backend_executes_in_isolated_runtime(mock_window):
    runner, plugin = make_runner(mock_window, runtime=True)
    backend = DockerBackend(plugin)
    plugin.get_execution_backend.return_value = backend
    plugin.docker.execute.return_value = (b"ok", b"")
    runner.handle_result = MagicMock(return_value="OK")
    runner.parse_result = MagicMock(return_value="PARSED")
    ctx = CtxItem()
    item = {"cmd": "shell_exec", "params": {"command": "echo x"}}

    result = backend.shell_exec(ctx, item, {"cmd": "shell_exec"})

    assert backend.sandboxed is True
    assert backend.get_runtime_workdir() == "/mnt/data"
    mock_window.core.security.ensure_command.assert_called_once_with(
        "echo x", sandbox=True, os_id="linux"
    )
    plugin.docker.execute.assert_called_once_with("echo x", ctx=ctx, demux=True)
    runner.handle_result.assert_called_once_with(b"ok", b"", log_category="exec")
    assert result["stdout"] == "ok"
    assert result["stderr"] == ""
    assert result["result"] is True
    assert result["context"].endswith("PARSED")


def test_docker_backend_converts_execution_exception_to_output(mock_window):
    runner, plugin = make_runner(mock_window, runtime=True)
    backend = DockerBackend(plugin)
    plugin.get_execution_backend.return_value = backend
    plugin.docker.execute.side_effect = RuntimeError("boom")
    runner.handle_result = MagicMock(return_value="boom")
    runner.parse_result = MagicMock(return_value="boom")

    with pytest.raises(RuntimeError, match="boom"):
        backend.shell_exec(CtxItem(), {"params": {"command": "x"}}, {"cmd": "shell_exec"})

def test_host_backend_mocks_subprocess_and_security(mock_window):
    runner, plugin = make_runner(mock_window, runtime=True)
    backend = plugin.get_execution_backend()
    runner.send_interpreter_input = MagicMock()
    runner.send_interpreter_output_begin = MagicMock()
    runner.send_interpreter_output_end = MagicMock()
    runner.handle_result = MagicMock(return_value="OUT")
    runner.parse_result = MagicMock(return_value="PARSED")
    runner.log = MagicMock()
    backend._communicate_subprocess = MagicMock(return_value=(b"out", b""))

    result = backend.shell_exec(
        CtxItem(),
        {"params": {"command": "echo x"}},
        {"cmd": "shell_exec"},
    )

    mock_window.core.security.ensure_command.assert_called_once_with("echo x", sandbox=False)
    backend._communicate_subprocess.assert_called_once()
    assert result["result"] is True
    assert result["context"].endswith("PARSED")


def test_docker_backend_uses_docker_without_host_subprocess(mock_window):
    runner, plugin = make_runner(mock_window, runtime=True)
    backend = DockerBackend(plugin)
    plugin.get_execution_backend.return_value = backend
    runner.send_interpreter_input = MagicMock()
    runner.send_interpreter_output_begin = MagicMock()
    runner.send_interpreter_output_end = MagicMock()
    backend._communicate_subprocess = MagicMock()
    runner.handle_result = MagicMock(return_value="OUT")
    runner.parse_result = MagicMock(return_value="PARSED")
    runner.log = MagicMock()
    plugin.docker.execute.return_value = (b"out", b"")
    ctx = CtxItem()

    result = backend.shell_exec(
        ctx, {"params": {"command": "echo x"}}, {"cmd": "shell_exec"}
    )

    plugin.docker.execute.assert_called_once_with("echo x", ctx=ctx, demux=True)
    backend._communicate_subprocess.assert_not_called()
    assert result["context"].endswith("PARSED")


def test_parse_result_is_timezone_independent_and_handles_image_path(mock_window, tmp_path):
    runner, plugin = make_runner(mock_window)
    image = tmp_path / "img.png"
    image.write_bytes(b"x")
    assert runner.parse_result(str(image)) == f"![Image](file://{image})"
    assert runner.parse_result(None) == ""
    assert runner.parse_result("plain") == "plain"


def test_prepare_path_respects_host_and_sandbox(mock_window):
    runner, plugin = make_runner(mock_window)
    mock_window.core.filesystem.get_data_dir = MagicMock(return_value="/work")
    assert runner.prepare_path("a.txt") == "/work/a.txt"
    assert runner.prepare_path("/abs/a.txt") == "/abs/a.txt"

    backend = DockerBackend(plugin)
    plugin.get_execution_backend.return_value = backend
    mock_window.core.filesystem.from_sandbox_data_path = MagicMock(side_effect=lambda path, ctx=None: path)
    assert runner.prepare_path("a.txt", on_host=False) == "a.txt"  # relative to runtime CWD
    assert runner.prepare_path("a.txt", on_host=True) == "/work/a.txt"
    mock_window.core.filesystem.from_sandbox_data_path.assert_called_once_with("a.txt", ctx=None)


def test_logging_helpers_emit_signals(mock_window):
    runner, _ = make_runner(mock_window)
    runner.signals = MagicMock()
    runner.error("e")
    runner.status("s")
    runner.debug("d")
    runner.log("l", sandbox=True)
    runner.signals.error.emit.assert_called_once_with("e")
    runner.signals.status.emit.assert_called_once_with("s")
    runner.signals.debug.emit.assert_called_once_with("d")
    runner.signals.log.emit.assert_called_once_with("[SANDBOX] l")


def test_windows_guard_checks_platform_and_option(mock_window):
    runner, plugin = make_runner(mock_window)
    with patch("pygpt_net.plugin.filesystem.os.runner.platform.system", return_value="Linux"):
        with pytest.raises(RuntimeError, match="Microsoft Windows"):
            runner._ensure_windows()

    plugin.get_option_value.side_effect = lambda name: False if name == "winapi_enabled" else None
    with patch("pygpt_net.plugin.filesystem.os.runner.platform.system", return_value="Windows"):
        with pytest.raises(RuntimeError, match="disabled"):
            runner._ensure_windows()


def test_to_json_keeps_unicode(mock_window):
    runner, _ = make_runner(mock_window)
    text = runner._to_json({"x": "żółć"})
    assert "żółć" in text
    assert json.loads(text) == {"x": "żółć"}


def test_resolve_window_covers_valid_missing_ambiguous_and_single(mock_window):
    runner, _ = make_runner(mock_window)
    api = MagicMock()
    runner._ensure_winapi = MagicMock(return_value=api)
    api.is_window.return_value = True
    assert runner._resolve_window(hwnd=10) == (10, None, None)

    api.is_window.return_value = False
    assert runner._resolve_window(hwnd=10)[2] == "Window handle not valid: 10"

    api.enum_windows.return_value = []
    assert runner._resolve_window(title="Editor")[2] == "No window matched."

    api.enum_windows.return_value = [
        {"hwnd": 1, "title": "Editor A", "class_name": "X", "exe": "/x/app.exe", "pid": 1},
        {"hwnd": 2, "title": "Editor B", "class_name": "X", "exe": "/x/app.exe", "pid": 2},
    ]
    handle, candidates, err = runner._resolve_window(title="Editor")
    assert handle is None and len(candidates) == 2 and "Ambiguous" in err

    handle, candidates, err = runner._resolve_window(title="Editor A", exact=True)
    assert (handle, candidates, err) == (1, None, None)
