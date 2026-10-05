import json
import subprocess
import sys

import pytest

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.plugin.base.execution import execution_response
from pygpt_net.plugin.cmd_code_interpreter.execution.host import HostBackend
from pygpt_net.plugin.cmd_code_interpreter.worker import Worker as PythonWorker
from pygpt_net.plugin.cmd_system.worker import Worker as SystemWorker
from tests.mocks import mock_window


@pytest.mark.parametrize('use_extra', [False, True])
@pytest.mark.parametrize('worker_type,cmd', [(PythonWorker, 'python_exec'), (SystemWorker, 'shell_exec')])
def test_streams_reach_model_once_and_context_stays_local(mock_window, use_extra, worker_type, cmd):
    backend = execution_response({'cmd': cmd}, 'unique stdout', 'unique stderr', 7,
                                 context='local context unique stdout unique stderr')
    worker = worker_type()
    item = {'cmd': cmd, 'params': {}}
    extra = worker.prepare_extra(item, backend)
    response = worker.make_response(item, backend, extra)
    assert response['result']['result'] is False
    assert extra['code']['output']['content'] == 'unique stdout\nunique stderr'
    assert response['context'] == backend['context']
    ctx = CtxItem()
    plugin = BasePlugin(window=mock_window)
    mock_window.core.config.set('ctx.use_extra', use_extra)
    mock_window.core.command.is_tool_hidden.return_value = False
    plugin.prepare_reply_ctx(response, ctx)
    assert ctx.results == [{'request': {'cmd': cmd}, 'result': {
        'request': {'cmd': cmd}, 'result': False,
        'stdout': 'unique stdout', 'stderr': 'unique stderr', 'return_code': 7}}]
    assert 'context' not in ctx.extra['tool_output'][0]['result']
    encoded = json.dumps(ctx.results)
    assert encoded.count('unique stdout') == encoded.count('unique stderr') == 1
    assert ctx.extra_ctx is None
    assert 'context' not in encoded


@pytest.mark.parametrize('stderr,code,success', [('', 0, True), ('warning', 0, False), ('', 3, False)])
def test_success_status_obeys_stderr_and_exit_status(stderr, code, success):
    assert execution_response({}, '', stderr, code)['result'] is success


def test_host_communicate_preserves_exit_code_and_both_streams():
    result = HostBackend._communicate_subprocess(
        [sys.executable, '-c', "import sys;print('out');print('err',file=sys.stderr);sys.exit(9)"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    stdout, stderr = result
    assert stdout == b'out\n'
    assert stderr == b'err\n'
    assert result.return_code == 9


def test_builtin_process_keeps_exit_status_without_shared_state(monkeypatch):
    from pygpt_net.core.sandbox.builtin import BuiltinSandboxRuntime
    from unittest.mock import MagicMock

    runtime = BuiltinSandboxRuntime(None, "python")
    runtime.prepare_process = MagicMock(return_value=(['python'], '/tmp', {}))
    runtime.attach_process_job = MagicMock(return_value=None)
    runtime.close_process_job = MagicMock()
    process = MagicMock()
    process.communicate.return_value = (b'out', b'err')
    process.returncode = 5
    monkeypatch.setattr('pygpt_net.core.sandbox.builtin.subprocess.Popen', lambda *a, **k: process)
    output = runtime._communicate(['python'])
    assert tuple(output) == (b'out', b'err')
    assert output.return_code == 5


@pytest.mark.parametrize('worker_type,cmd', [(PythonWorker, 'ipython_exec'), (SystemWorker, 'shell_exec')])
def test_execution_response_cleans_terminal_formatting_before_tool_reply(mock_window, worker_type, cmd):
    stdout = '\x1b[32mZażółć gęślą\x1b[0m\n'.encode('utf-8')
    stderr = 'Error executing code:\x1b[31mModuleNotFoundError\x1b[39m\nNo module named googletrans'
    backend = execution_response({'cmd': cmd}, stdout, stderr, 1)
    worker = worker_type()
    item = {'cmd': cmd, 'params': {}}
    response = worker.make_response(item, backend, worker.prepare_extra(item, backend))
    ctx = CtxItem()
    plugin = BasePlugin(window=mock_window)
    mock_window.core.command.is_tool_hidden.return_value = False
    plugin.prepare_reply_ctx(response, ctx)
    result = ctx.results[0]['result']
    assert result['stdout'] == 'Zażółć gęślą\n'
    assert result['stderr'] == 'Error executing code:ModuleNotFoundError\nNo module named googletrans'
    assert result['result'] is False
    assert result['return_code'] == 1
    assert '\x1b' not in json.dumps(ctx.results, ensure_ascii=False)
    assert '\\u001b' not in json.dumps(ctx.results)


def test_execution_response_removes_osc_without_altering_plain_output():
    output = '\x1b]0;title\x07line 1\n\x1b]8;;https://example.com\x1b\\link\x1b]8;;\x1b\\\nline 2\tend'
    assert execution_response({}, stdout=output)['stdout'] == 'line 1\nlink\nline 2\tend'
