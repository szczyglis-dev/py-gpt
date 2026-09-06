from datetime import datetime
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.plugin.crontab import Plugin
from tests.mocks import mock_window


def test_crontab_defaults_and_count_active(mock_window):
    plugin = Plugin(window=mock_window)
    assert {"crontab", "new_ctx", "show_notify"}.issubset(plugin.setup())
    assert plugin.count_active() == 0
    items = plugin.get_option_value("crontab")
    items[0]["enabled"] = True
    assert plugin.count_active() == 1


def test_crontab_handle_updates_tray_and_option_get(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.count_active = MagicMock(return_value=3)
    event = Event()
    event.name = Event.PLUGIN_SETTINGS_CHANGED
    event.data = {}
    event.ctx = None
    plugin.handle(event)
    mock_window.ui.tray.update_schedule_tasks.assert_called_once_with(3)

    event.name = Event.PLUGIN_OPTION_GET
    event.data = {"name": "scheduled_tasks_count"}
    plugin.handle(event)
    assert event.data["value"] == 3


def test_crontab_post_update_reschedules(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.schedule_tasks = MagicMock()
    plugin.on_post_update()
    plugin.schedule_tasks.assert_called_once_with()
    assert plugin.on_update() is None


def test_crontab_job_empty_prompt_is_ignored(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.log = MagicMock()
    plugin.job({"prompt": "", "preset": "_"})
    plugin.log.assert_called_once_with("Prompt is empty, skipping task")
    mock_window.dispatch.assert_not_called()


def test_crontab_job_uses_fixed_clock_and_dispatches_prompt(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.log = MagicMock()
    plugin.set_option_value("show_notify", True)
    plugin.set_option_value("new_ctx", True)
    mock_window.core.presets.exists.return_value = True
    mock_window.core.presets.get_first_mode.return_value = "chat"
    fixed = datetime(2030, 1, 2, 3, 4, 5)
    with patch("pygpt_net.plugin.crontab.plugin.datetime") as dt_mock, \
            patch("pygpt_net.plugin.crontab.plugin.trans", return_value="Cron title"):
        dt_mock.now.return_value = fixed
        plugin.job({"prompt": "Run this", "preset": "preset-a"})

    mock_window.ui.tray.show_msg.assert_called_once_with("Cron title", "Run this...")
    mock_window.controller.presets.set.assert_called_once_with("chat", "preset-a")
    mock_window.controller.ctx.new.assert_called_once_with(force=True)
    mock_window.dispatch.assert_called_once()
    event = mock_window.dispatch.call_args.args[0]
    assert event.data["context"].prompt == "Run this"
    assert event.data["extra"] == {"force": True}
    assert "2030-01-02 03:04:05" in plugin.log.call_args_list[0].args[0]


def test_schedule_tasks_adds_timer_without_real_clock_or_croniter(mock_window):
    plugin = Plugin(window=mock_window)
    item = {"enabled": True, "crontab": "* * * * *", "prompt": "x", "preset": "_"}
    plugin.set_option_value("crontab", [item])
    next_dt = datetime(2030, 1, 2, 3, 5, 0)
    cron = MagicMock()
    cron.get_next.return_value = next_dt
    with patch("pygpt_net.plugin.crontab.plugin.datetime") as dt_mock, \
            patch("pygpt_net.plugin.crontab.plugin.croniter", return_value=cron):
        dt_mock.now.return_value = datetime(2030, 1, 2, 3, 4, 0)
        plugin.schedule_tasks()
    assert plugin.timers == [{"item": item, "next_time": next_dt}]
    mock_window.ui.plugin_addon['schedule'].setVisible.assert_called_with(True)


def test_schedule_tasks_runs_due_timer_with_fixed_datetime(mock_window):
    plugin = Plugin(window=mock_window)
    item = {"enabled": True, "crontab": "* * * * *", "prompt": "x", "preset": "_"}
    due = datetime(2030, 1, 2, 3, 4, 0)
    plugin.timers = [{"item": item, "next_time": due}]
    plugin.set_option_value("crontab", [item])
    plugin.job = MagicMock()
    cron = MagicMock()
    cron.get_next.side_effect = [datetime(2030, 1, 2, 3, 5), datetime(2030, 1, 2, 3, 6)]
    with patch("pygpt_net.plugin.crontab.plugin.datetime") as dt_mock, \
            patch("pygpt_net.plugin.crontab.plugin.croniter", return_value=cron):
        dt_mock.now.return_value = due
        plugin.schedule_tasks()
    plugin.job.assert_called_once_with(item)
    assert plugin.timers[0]["next_time"] == datetime(2030, 1, 2, 3, 6)
