import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.cmd_system.runner import Runner
from tests.mocks import mock_window


def make_runner(mock_window):
    plugin = MagicMock()
    plugin.window = mock_window
    plugin.get_option_value.side_effect = lambda name: {
        "sandbox_docker": False,
        "winapi_enabled": True,
    }.get(name)
    plugin.docker = MagicMock()
    return Runner(plugin), plugin


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


def test_sandbox_volumes_and_docker_run_are_isolated(mock_window):
    runner, plugin = make_runner(mock_window)
    plugin.get_option_value.side_effect = lambda name: name == "sandbox_docker"
    assert runner.is_sandbox() is True
    mock_window.core.config.get_user_dir = MagicMock(return_value="/data")
    mock_window.core.filesystem.get_data_dir = MagicMock(return_value="/data")
    assert runner.get_volumes() == {"/data": {"bind": "/data", "mode": "rw"}}
    plugin.docker.execute.return_value = b"ok"
    runner.get_docker = MagicMock(return_value=object())
    assert runner.run_docker("echo x") == b"ok"


def test_run_docker_converts_execution_exception_to_bytes(mock_window):
    runner, plugin = make_runner(mock_window)
    runner.get_docker = MagicMock(return_value=object())
    runner.get_volumes = MagicMock(return_value={})
    plugin.docker.execute.side_effect = RuntimeError("boom")
    assert runner.run_docker("x") == b"boom"


def test_sys_exec_host_mocks_subprocess_and_security(mock_window):
    runner, plugin = make_runner(mock_window)
    runner.send_interpreter_input = MagicMock()
    runner.send_interpreter_output_begin = MagicMock()
    runner.send_interpreter_output_end = MagicMock()
    runner.handle_result = MagicMock(return_value="OUT")
    runner.parse_result = MagicMock(return_value="PARSED")
    runner.log = MagicMock()
    proc = MagicMock()
    proc.communicate.return_value = (b"out", b"")
    with patch("pygpt_net.plugin.cmd_system.runner.subprocess.Popen", return_value=proc) as popen:
        result = runner.sys_exec_host(
            CtxItem(),
            {"params": {"command": "echo x"}},
            {"cmd": "sys_exec"},
        )
    mock_window.core.security.ensure_command.assert_called_once_with("echo x", sandbox=False)
    popen.assert_called_once()
    assert result["result"] == "OUT"
    assert result["context"].endswith("PARSED")


def test_sys_exec_sandbox_uses_docker_without_host_subprocess(mock_window):
    runner, _ = make_runner(mock_window)
    runner.send_interpreter_input = MagicMock()
    runner.send_interpreter_output_begin = MagicMock()
    runner.send_interpreter_output_end = MagicMock()
    runner.run_docker = MagicMock(return_value=b"out")
    runner.handle_result_docker = MagicMock(return_value="OUT")
    runner.parse_result = MagicMock(return_value="PARSED")
    runner.log = MagicMock()
    ctx = CtxItem()
    result = runner.sys_exec_sandbox(
        ctx, {"params": {"command": "echo x"}}, {"cmd": "sys_exec"}
    )
    runner.run_docker.assert_called_once_with("echo x", ctx=ctx)
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
    mock_window.core.config.get_user_dir = MagicMock(return_value="/work")
    mock_window.core.filesystem.get_data_dir = MagicMock(return_value="/work")
    runner.is_sandbox = MagicMock(return_value=False)
    assert runner.prepare_path("a.txt") == "/work/a.txt"
    assert runner.prepare_path("/abs/a.txt") == "/abs/a.txt"

    runner.is_sandbox.return_value = True
    mock_window.core.filesystem.from_sandbox_data_path = MagicMock(side_effect=lambda path, ctx=None: path)
    assert runner.prepare_path("a.txt", on_host=False) == "a.txt"
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
    runner.signals.log.emit.assert_called_once_with("[DOCKER] l")


def test_windows_guard_checks_platform_and_option(mock_window):
    runner, plugin = make_runner(mock_window)
    with patch("pygpt_net.plugin.cmd_system.runner.platform.system", return_value="Linux"):
        with pytest.raises(RuntimeError, match="Microsoft Windows"):
            runner._ensure_windows()

    plugin.get_option_value.side_effect = lambda name: False if name == "winapi_enabled" else None
    with patch("pygpt_net.plugin.cmd_system.runner.platform.system", return_value="Windows"):
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
