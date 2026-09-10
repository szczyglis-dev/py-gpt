from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.cmd_custom import Plugin
from pygpt_net.plugin.cmd_custom.worker import Worker
from tests.mocks import mock_window


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2031, 4, 5, 6, 7, 8)
        return value if tz is None else value.replace(tzinfo=tz)


def _worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.setup()
    worker = Worker()
    worker.from_defaults(plugin)
    return plugin, worker


def test_extract_params_skips_empty_values(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.extract_params(None) == []
    assert plugin.extract_params("") == []
    assert plugin.extract_params(" first, ,second ") == [
        {"name": "first", "type": "str", "description": "first"},
        {"name": "second", "type": "str", "description": "second"},
    ]


def test_worker_handle_cmd_rejects_empty_command(mock_window):
    _, worker = _worker(mock_window)
    item = {"cmd": "empty", "params": {}}
    assert worker.handle_cmd({"cmd": "", "params": ""}, item) is False
    assert worker.handle_cmd({"cmd": None, "params": ""}, item) is False


def test_worker_handle_cmd_replaces_fixed_time_and_parameters(mock_window):
    plugin, worker = _worker(mock_window)
    mock_window.core.config.path = "/fixed/home"
    item = {"cmd": "demo", "params": {"name": "Ada"}}
    command = {
        "cmd": "echo {_date} {_time} {_datetime} {_home} {name}",
        "params": "name",
    }
    process = MagicMock()
    process.communicate.return_value = (b"done\n", b"")

    with patch("pygpt_net.plugin.cmd_custom.worker.datetime", FixedDateTime), \
            patch("pygpt_net.plugin.cmd_custom.worker.subprocess.Popen", return_value=process) as popen, \
            patch.object(worker, "security_command") as security, \
            patch.object(worker, "log"):
        response = worker.handle_cmd(command, item)

    rendered = popen.call_args.args[0]
    assert rendered == "echo 2031-04-05 06:07:08 2031-04-05 06:07:08 /fixed/home Ada"
    security.assert_called_once_with(rendered, sandbox=False)
    assert response["result"] == "done\n"


def test_worker_handle_cmd_combines_stdout_stderr_and_handles_empty(mock_window):
    _, worker = _worker(mock_window)
    item = {"cmd": "demo", "params": {}}
    command = {"cmd": "demo", "params": ""}

    process = MagicMock()
    process.communicate.return_value = (b"stdout", b"stderr")
    with patch("pygpt_net.plugin.cmd_custom.worker.subprocess.Popen", return_value=process), \
            patch.object(worker, "security_command"), patch.object(worker, "log"):
        assert worker.handle_cmd(command, item)["result"] == "stdout\nstderr"

    process.communicate.return_value = (b"", b"")
    with patch("pygpt_net.plugin.cmd_custom.worker.subprocess.Popen", return_value=process), \
            patch.object(worker, "security_command"), patch.object(worker, "log"):
        assert worker.handle_cmd(command, item)["result"] == "No result (STDOUT/STDERR empty)"


def test_worker_run_collects_responses_and_reports_empty_command(mock_window):
    plugin, worker = _worker(mock_window)
    plugin.options["cmds"]["value"] = [
        {"enabled": True, "name": "one", "instruction": "", "params": "", "cmd": "echo 1"},
        {"enabled": True, "name": "empty", "instruction": "", "params": "", "cmd": ""},
    ]
    worker.cmds = [
        {"cmd": "one", "params": {}},
        {"cmd": "empty", "params": {}},
    ]
    worker.ctx = CtxItem()
    worker.handle_cmd = MagicMock(side_effect=[{"request": {"cmd": "one"}, "result": "ok"}, False])
    worker.reply_more = MagicMock()
    worker.status = MagicMock()
    worker.cleanup = MagicMock()
    worker.is_stopped = MagicMock(return_value=False)

    worker.run()

    worker.reply_more.assert_called_once_with([{"request": {"cmd": "one"}, "result": "ok"}])
    worker.status.assert_called_once_with("Command is empty")
    worker.cleanup.assert_called_once()
