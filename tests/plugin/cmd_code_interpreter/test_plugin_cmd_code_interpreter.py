#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 17:20:00                  #
# ================================================== #

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_code_interpreter import Plugin
from pygpt_net.plugin.cmd_code_interpreter.worker import Worker
from pygpt_net.plugin.cmd_code_interpreter.ipython.docker_kernel import DockerKernel


def test_options(mock_window):
    """Test current interpreter/backend options and commands."""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "python_cmd_tpl" in options
    assert "cmd.python_exec" in options
    assert "cmd.python_exec_file" in options
    assert "cmd.python_sys_exec" in options
    assert "cmd.ipython_exec" in options
    assert "cmd.ipython_sys_exec" in options
    assert options["sandbox"]["value"] == "builtin"
    assert options["use_ipython"]["value"] is True


def test_handle_cmd_syntax(mock_window):
    """Default config exposes only commands owned by Code Interpreter."""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.syntax"
    event.data = {"cmd": []}
    event.ctx = ctx

    plugin.handle(event)

    names = [item["cmd"] for item in event.data["cmd"]]
    assert names == [
        "ipython_exec",
        "ipython_sys_exec",
        "ipython_kernel_restart",
    ]


def test_ipython_sys_exec_syntax_describes_same_sandbox_container(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.set_option_value("sandbox", "docker")
    plugin.set_option_value("use_ipython", True)
    plugin.set_option_value("ipython_run_as_root", False)
    mock_window.core.filesystem.get_data_dir.return_value = "/host/data"

    data = {"cmd": []}
    plugin.cmd_syntax(data)

    cmd = next(item for item in data["cmd"] if item["cmd"] == "ipython_sys_exec")
    assert "same Docker container as the current IPython kernel" in cmd["instruction"]
    assert "Directory /mnt/data" in cmd["instruction"]
    assert "passwordless sudo" in cmd["instruction"]


def test_ipython_sys_exec_host_uses_host_security_and_shell(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox", "disabled")
    backend = plugin.get_execution_backend()
    item = {"cmd": "ipython_sys_exec", "params": {"command": "echo hello"}}
    request = {"cmd": "ipython_sys_exec", "command": "echo hello"}

    process = MagicMock()
    process.communicate.return_value = (b"hello\n", b"")
    with patch(
        "pygpt_net.plugin.cmd_code_interpreter.execution.host.subprocess.Popen",
        return_value=process,
    ) as popen:
        result = backend.ipython_sys_exec(CtxItem(), item, request)

    mock_window.core.security.ensure_command.assert_called_once_with("echo hello", sandbox=False)
    popen.assert_called_once_with(
        "echo hello",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    assert result["request"] == request
    assert result["result"] == "hello\n"
    assert "SYS OUTPUT" in result["context"]


def test_ipython_sys_exec_sandbox_uses_ipython_container(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("sandbox", "docker")
    backend = plugin.get_execution_backend()
    plugin.ipython_docker.execute_system = MagicMock(return_value=b"sandbox\n")
    item = {"cmd": "ipython_sys_exec", "params": {"command": "pwd"}}
    request = {"cmd": "ipython_sys_exec", "command": "pwd"}

    ctx = CtxItem()
    result = backend.ipython_sys_exec(ctx, item, request)

    mock_window.core.security.ensure_command.assert_called_once_with(
        "pwd", sandbox=True, os_id="linux"
    )
    plugin.ipython_docker.execute_system.assert_called_once_with("pwd", ctx=ctx)
    assert result["request"] == request
    assert result["result"] == "sandbox\n"
    assert "SYS OUTPUT" in result["context"]


def test_worker_routes_ipython_sys_exec_to_matching_environment():
    worker = Worker()
    worker.ctx = CtxItem()
    worker.plugin = MagicMock()
    backend = MagicMock()
    backend.ipython_sys_exec.return_value = {
        "request": {"cmd": "ipython_sys_exec"},
        "result": "OK",
        "context": "SYS OUTPUT:\nOK",
    }
    worker.backend = backend
    item = {"cmd": "ipython_sys_exec", "params": {"command": "whoami"}}

    response = worker.cmd_ipython_sys_exec(item)

    backend.ipython_sys_exec.assert_called_once()
    call = backend.ipython_sys_exec.call_args.kwargs
    assert call["ctx"] is worker.ctx
    assert call["item"] is item
    assert call["request"]["cmd"] == "ipython_sys_exec"
    assert response["result"]["result"] == "OK"


def test_worker_ipython_sys_exec_extra_uses_bash():
    worker = Worker()
    item = {"cmd": "ipython_sys_exec", "params": {"command": "ls -la"}}
    result = {"result": "out", "context": "SYS OUTPUT:\nout"}

    extra = worker.prepare_extra(item, result)

    assert extra["code"]["input"] == {"lang": "bash", "content": "ls -la"}
    assert extra["code"]["output"] == {"lang": "bash", "content": "out"}


def test_docker_kernel_execute_system_execs_in_existing_ipython_container():
    plugin = MagicMock()
    kernel = DockerKernel(plugin)
    kernel.prepare_local_data_dir = MagicMock()
    kernel.is_image = MagicMock(return_value=True)
    kernel.start_container = MagicMock()
    kernel.get_container_name = MagicMock(return_value="ipy-container")

    container = MagicMock()
    container.status = "running"
    container.exec_run.return_value = SimpleNamespace(output=b"ok\n")
    client = MagicMock()
    client.containers.get.return_value = container
    kernel.get_docker_client = MagicMock(return_value=client)

    result = kernel.execute_system("printf ok")

    kernel.start_container.assert_called_once_with("ipy-container", ctx=None)
    client.containers.get.assert_called_once_with("ipy-container")
    container.exec_run.assert_called_once_with(
        ["/bin/sh", "-c", "printf ok"],
        stdin=False,
        stdout=True,
        stderr=True,
        workdir="/mnt/data",
    )
    assert result == b"ok\n"
