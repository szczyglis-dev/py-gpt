from datetime import datetime
from email.message import EmailMessage
from types import ModuleType
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.mailer import Plugin
from pygpt_net.plugin.mailer.runner import Runner
from pygpt_net.plugin.mailer.worker import Worker
from tests.mocks import mock_window


def test_mailer_options_and_syntax(mock_window):
    plugin = Plugin(window=mock_window)
    assert {"smtp_host", "smtp_port_outbox", "smtp_port_inbox", "smtp_user", "smtp_password", "from_email"}.issubset(plugin.setup())
    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert [x["cmd"] for x in data["cmd"]] == [c for c in plugin.allowed_cmds if plugin.has_cmd(c)]


def test_mailer_handle_execute_passes_silent_flag(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd = MagicMock()
    event = Event()
    event.name = Event.CMD_EXECUTE
    event.data = {"commands": [{"cmd": "send_mail", "params": {}}], "silent": True}
    event.ctx = CtxItem()
    plugin.handle(event)
    plugin.cmd.assert_called_once_with(event.ctx, event.data["commands"], True)


def test_mailer_cmd_filters_and_routes_worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_prepare = MagicMock()
    plugin.runner.attach_signals = MagicMock()
    plugin.is_async = MagicMock(return_value=False)
    ctx = CtxItem()
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.mailer.worker")
    fake_mod.Worker = MagicMock(return_value=worker)

    with patch.dict("sys.modules", {"pygpt_net.plugin.mailer.worker": fake_mod}):
        plugin.cmd(ctx, [{"cmd": "foreign", "params": {}}])
        fake_mod.Worker.assert_not_called()
        request = {"cmd": "send_mail", "params": {}}
        plugin.cmd(ctx, [request])

    worker.from_defaults.assert_called_once_with(plugin)
    plugin.runner.attach_signals.assert_called_once_with(worker.signals)
    worker.run.assert_called_once_with()
    plugin.cmd_prepare.assert_called_once_with(ctx, [request])


def test_mailer_force_uses_async_and_silent_skips_busy(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_prepare = MagicMock()
    plugin.is_async = MagicMock(return_value=False)
    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.mailer.worker")
    fake_mod.Worker = MagicMock(return_value=worker)
    with patch.dict("sys.modules", {"pygpt_net.plugin.mailer.worker": fake_mod}):
        plugin.cmd(CtxItem(), [{"cmd": "send_mail", "params": {}, "force": True}], silent=True)
    worker.run_async.assert_called_once_with()
    worker.run.assert_not_called()
    plugin.cmd_prepare.assert_not_called()


def test_runner_parse_plain_and_html_email(mock_window):
    plugin = Plugin(window=mock_window)
    runner = Runner(plugin)

    plain = EmailMessage()
    plain.set_content("hello")
    assert runner.parse_email(plain).strip() == "hello"

    html = EmailMessage()
    html.set_content("fallback")
    html.add_alternative("<p>Hello <b>world</b></p>", subtype="html")
    text = runner.parse_email(html, as_text=True)
    assert "Hello world" in text
    raw_html = runner.parse_email(html, as_text=False)
    assert "<p>Hello <b>world</b></p>" in raw_html


def test_runner_smtp_send_email_uses_fixed_datetime_and_mocked_smtp(mock_window):
    plugin = Plugin(window=mock_window)
    values = {
        "from_email": "from@example.test",
        "smtp_host": "smtp.example.test",
        "smtp_port_outbox": 587,
        "smtp_user": "user",
        "smtp_password": "secret",
    }
    plugin.get_option_value = MagicMock(side_effect=values.get)
    runner = Runner(plugin)
    runner.log = MagicMock()
    smtp = MagicMock()
    fixed = datetime(2030, 1, 2, 3, 4)
    with patch("pygpt_net.plugin.mailer.runner.datetime.datetime") as dt_cls, \
            patch("pygpt_net.plugin.mailer.runner.smtplib.SMTP", return_value=smtp) as smtp_cls:
        dt_cls.now.return_value = fixed
        result = runner.smtp_send_email(
            CtxItem(),
            {"params": {"recipient": "to@example.test", "subject": "S", "message": "Body"}},
            {"cmd": "send_mail"},
        )
    smtp_cls.assert_called_once_with("smtp.example.test", 587)
    smtp.starttls.assert_called_once_with()
    smtp.login.assert_called_once_with("user", "secret")
    body = smtp.sendmail.call_args.args[2]
    assert "Date: 02/01/2030 03:04" in body
    assert result["result"] == "OK"


def test_runner_smtp_send_email_uses_ssl_for_465(mock_window):
    plugin = Plugin(window=mock_window)
    values = {
        "from_email": "from@example.test",
        "smtp_host": "smtp.example.test",
        "smtp_port_outbox": 465,
        "smtp_user": "user",
        "smtp_password": "secret",
    }
    plugin.get_option_value = MagicMock(side_effect=values.get)
    runner = Runner(plugin)
    runner.log = MagicMock()
    smtp = MagicMock()
    with patch("pygpt_net.plugin.mailer.runner.smtplib.SMTP_SSL", return_value=smtp) as smtp_ssl:
        result = runner.smtp_send_email(
            CtxItem(),
            {"params": {"recipient": "to@example.test", "subject": "S", "message": "Body"}},
            {"cmd": "send_mail"},
        )
    smtp_ssl.assert_called_once_with("smtp.example.test", 465)
    smtp.starttls.assert_not_called()
    assert result["result"] == "OK"


def test_runner_receive_emails_uses_mocked_pop3(mock_window):
    plugin = Plugin(window=mock_window)
    values = {
        "smtp_host": "pop.example.test",
        "smtp_port_inbox": 995,
        "smtp_user": "user",
        "smtp_password": "secret",
    }
    plugin.get_option_value = MagicMock(side_effect=values.get)
    runner = Runner(plugin)
    runner.log = MagicMock()
    pop = MagicMock()
    pop.getwelcome.return_value = b"hello"
    pop.stat.return_value = (2, 100)
    pop.top.side_effect = [
        (b"+OK", [b"From: a@example.test", b"Subject: A", b"Date: D", b""], 1),
        (b"+OK", [b"From: b@example.test", b"Subject: B", b"Date: D", b""], 1),
    ]
    with patch("pygpt_net.plugin.mailer.runner.poplib.POP3_SSL", return_value=pop):
        result = runner.smtp_receive_emails(
            CtxItem(), {"params": {"limit": 2, "order": "desc"}}, {"cmd": "get_emails"}
        )
    assert "'total': 2" in result["result"]
    assert "'Subject': 'B'" in result["result"]
    pop.quit.assert_called_once_with()


def test_runner_get_email_body_uses_mocked_pop3(mock_window):
    plugin = Plugin(window=mock_window)
    values = {
        "smtp_host": "pop.example.test",
        "smtp_port_inbox": 110,
        "smtp_user": "user",
        "smtp_password": "secret",
    }
    plugin.get_option_value = MagicMock(side_effect=values.get)
    runner = Runner(plugin)
    runner.log = MagicMock()
    pop = MagicMock()
    pop.getwelcome.return_value = b"hello"
    pop.retr.return_value = (
        b"+OK",
        [b"From: a@example.test", b"Subject: A", b"Date: D", b"", b"Body"],
        1,
    )
    with patch("pygpt_net.plugin.mailer.runner.poplib.POP3", return_value=pop):
        result = runner.smtp_get_email_body(
            CtxItem(), {"params": {"id": 1, "format": "text"}}, {"cmd": "get_email_body"}
        )
    assert "Body" in result["result"]
    pop.quit.assert_called_once_with()


def test_runner_signal_helpers(mock_window):
    runner = Runner(Plugin(window=mock_window))
    runner.signals = MagicMock()
    runner.error("e")
    runner.status("s")
    runner.debug("d")
    runner.log("l")
    runner.signals.error.emit.assert_called_once_with("e")
    runner.signals.status.emit.assert_called_once_with("s")
    runner.signals.debug.emit.assert_called_once_with("d")
    runner.signals.log.emit.assert_called_once_with("[SMTP] l")


def test_worker_command_wrappers_call_runner(mock_window):
    plugin = Plugin(window=mock_window)
    worker = Worker()
    worker.plugin = plugin
    worker.ctx = CtxItem()
    item = {"cmd": "x", "params": {}}

    plugin.runner.smtp_send_email = MagicMock(return_value={"result": "sent"})
    response = worker.cmd_send_mail(item)
    assert response["result"] == {"result": "sent"}

    plugin.runner.smtp_receive_emails = MagicMock(return_value={"result": "list"})
    response = worker.cmd_receive_emails(item)
    assert response["result"] == {"result": "list"}

    plugin.runner.smtp_get_email_body = MagicMock(return_value={"result": "body"})
    response = worker.cmd_get_email_body(item)
    assert response["result"] == {"result": "body"}
