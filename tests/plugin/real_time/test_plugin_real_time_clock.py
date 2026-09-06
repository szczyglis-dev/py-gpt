from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.real_time import Plugin
from tests.mocks import mock_window


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2031, 4, 5, 6, 7, 8)
        return value if tz is None else value.replace(tzinfo=tz)


def _plugin(mock_window, *, hour=True, date=True):
    plugin = Plugin(window=mock_window)
    plugin.setup()
    plugin.options["hour"]["value"] = hour
    plugin.options["date"]["value"] = date
    plugin.options["tpl"]["value"] = "Current time: {time}"
    return plugin


@pytest.mark.parametrize(
    ("hour", "date", "expected"),
    [
        (True, True, "Current time: Saturday, 2031-04-05 06:07:08"),
        (True, False, "Current time: 06:07:08"),
        (False, True, "Current time: Saturday, 2031-04-05"),
    ],
)
def test_system_prompt_uses_fixed_clock(mock_window, hour, date, expected):
    plugin = _plugin(mock_window, hour=hour, date=date)
    with patch("pygpt_net.plugin.real_time.plugin.datetime", FixedDateTime):
        assert plugin.on_system_prompt("base") == f"base\n\n{expected}"


def test_system_prompt_disabled_leaves_prompt_unchanged(mock_window):
    plugin = _plugin(mock_window, hour=False, date=False)
    assert plugin.on_system_prompt("base") == "base"


def test_agent_prompt_prepends_fixed_time(mock_window):
    plugin = _plugin(mock_window)
    with patch("pygpt_net.plugin.real_time.plugin.datetime", FixedDateTime):
        assert plugin.on_agent_prompt("agent") == (
            "Current time: Saturday, 2031-04-05 06:07:08\n\nagent"
        )


def test_get_time_command_replies_once_with_fixed_clock(mock_window):
    plugin = _plugin(mock_window)
    plugin.options["cmd.get_time"]["value"]["enabled"] = True
    plugin.reply = MagicMock()
    ctx = CtxItem()
    commands = [
        {"cmd": "get_time", "params": {}},
        {"cmd": "ignored", "params": {}},
    ]
    with patch("pygpt_net.plugin.real_time.plugin.datetime", FixedDateTime):
        plugin.cmd(ctx, commands)

    response, response_ctx = plugin.reply.call_args.args
    assert response_ctx is ctx
    assert response == {
        "request": {"cmd": "get_time"},
        "result": "Saturday, 2031-04-05 06:07:08",
    }


def test_handle_routes_agent_prompt_and_silent_flag(mock_window):
    plugin = _plugin(mock_window)
    plugin.on_agent_prompt = MagicMock(return_value="updated")
    event = Event(Event.AGENT_PROMPT, {"value": "old", "silent": True}, CtxItem())

    plugin.handle(event)

    plugin.on_agent_prompt.assert_called_once_with("old", True)
    assert event.data["value"] == "updated"
