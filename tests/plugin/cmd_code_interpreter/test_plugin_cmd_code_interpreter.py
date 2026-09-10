#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 13:15:00                  #
# ================================================== #

import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_code_interpreter import Plugin
from pygpt_net.plugin.cmd_code_interpreter.worker import Worker
from pygpt_net.plugin.cmd_code_interpreter.runner import Runner
from pygpt_net.plugin.cmd_code_interpreter.ipython.docker_kernel import DockerKernel


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "python_cmd_tpl" in options
    assert "cmd.code_execute" in options
    assert "cmd.code_execute_file" in options
    assert "cmd.ipython_sys_exec" in options
    assert "sandbox_docker" in options
    assert "sandbox_ipython" in options


def test_handle_cmd_syntax(mock_window):
    """Test handle event: cmd.syntax"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.syntax"
    event.data = {
        "cmd": []
    }
    event.ctx = ctx
    plugin.handle(event)
    assert len(event.data["cmd"]) == 8
    assert "ipython_sys_exec" in [item["cmd"] for item in event.data["cmd"]]


def test_ipython_sys_exec_syntax_describes_same_sandbox_container(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.set_option_value("sandbox_ipython", True)
    plugin.set_option_value("ipython_run_as_root", False)

    data = {"cmd": []}
    plugin.cmd_syntax(data)

    cmd = next(item for item in data["cmd"] if item["cmd"] == "ipython_sys_exec")
    assert "same Docker container as the current IPython kernel" in cmd["instruction"]
    assert "Directory /data" in cmd["instruction"]
    assert "passwordless sudo" in cmd["instruction"]


def test_ipython_sys_exec_host_uses_host_security_and_shell(mock_window):
    plugin = MagicMock()
    plugin.window = mock_window
    runner = Runner(plugin)
    item = {"cmd": "ipython_sys_exec", "params": {"command": "echo hello"}}
    request = {"cmd": "ipython_sys_exec", "command": "echo hello"}

    process = MagicMock()
    process.communicate.return_value = (b"hello\n", b"")
    with patch("pygpt_net.plugin.cmd_code_interpreter.runner.subprocess.Popen", return_value=process) as popen:
        result = runner.ipython_sys_exec_host(CtxItem(), item, request)

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
    plugin = MagicMock()
    plugin.window = mock_window
    plugin.ipython_docker.execute_system.return_value = b"sandbox\n"
    runner = Runner(plugin)
    item = {"cmd": "ipython_sys_exec", "params": {"command": "pwd"}}
    request = {"cmd": "ipython_sys_exec", "command": "pwd"}

    result = runner.ipython_sys_exec_sandbox(CtxItem(), item, request)

    plugin.ipython_docker.execute_system.assert_called_once_with("pwd")
    assert result["request"] == request
    assert result["result"] == "sandbox\n"
    assert "SYS OUTPUT" in result["context"]


def test_worker_routes_ipython_sys_exec_to_matching_environment():
    worker = Worker()
    worker.ctx = CtxItem()
    worker.plugin = MagicMock()
    worker.plugin.runner.is_sandbox_ipython.return_value = True
    worker.plugin.runner.ipython_sys_exec_sandbox.return_value = {
        "request": {"cmd": "ipython_sys_exec"},
        "result": "OK",
        "context": "SYS OUTPUT:\nOK",
    }
    item = {"cmd": "ipython_sys_exec", "params": {"command": "whoami"}}

    response = worker.cmd_ipython_sys_exec(item)

    worker.plugin.runner.ipython_sys_exec_sandbox.assert_called_once()
    worker.plugin.runner.ipython_sys_exec_host.assert_not_called()
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

    kernel.start_container.assert_called_once_with("ipy-container")
    client.containers.get.assert_called_once_with("ipy-container")
    container.exec_run.assert_called_once_with(
        ["/bin/sh", "-c", "printf ok"],
        stdin=False,
        stdout=True,
        stderr=True,
        workdir="/data",
    )
    assert result == b"ok\n"
