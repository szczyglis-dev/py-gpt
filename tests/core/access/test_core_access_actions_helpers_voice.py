import datetime as dt
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.access.actions as actions_mod
import pygpt_net.core.access.helpers as helpers_mod
from pygpt_net.core.access.actions import Actions
from pygpt_net.core.access.helpers import Helpers
from pygpt_net.core.access.voice import Voice
from pygpt_net.core.events import ControlEvent, KernelEvent
from pygpt_net.item.model import ModelItem


FIXED_NOW_TS = 1_737_028_800  # 2025-01-16 12:00:00 UTC
REAL_DATETIME = dt.datetime


class FixedDateTime(REAL_DATETIME):
    @classmethod
    def today(cls):
        return REAL_DATETIME.fromtimestamp(FIXED_NOW_TS, tz=dt.timezone.utc).replace(tzinfo=None)

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        value = REAL_DATETIME.fromtimestamp(timestamp, tz=dt.timezone.utc)
        if tz is None:
            return value.replace(tzinfo=None)
        return value.astimezone(tz)


def make_window(values=None):
    values = dict(values or {})
    config = SimpleNamespace(get=MagicMock(side_effect=lambda key, default=None: values.get(key, default)))
    ctx = SimpleNamespace(
        count_meta=MagicMock(return_value=2),
        get_current_meta=MagicMock(return_value=None),
        get_last=MagicMock(return_value=None),
        get_all_items=MagicMock(return_value=[]),
    )
    presets = SimpleNamespace(get_by_id=MagicMock(return_value=None))
    models = SimpleNamespace(
        from_defaults=MagicMock(return_value=ModelItem("default")),
        has=MagicMock(return_value=False),
        get=MagicMock(),
    )
    window = SimpleNamespace(
        core=SimpleNamespace(config=config, ctx=ctx, presets=presets, models=models, debug=SimpleNamespace(log=MagicMock())),
        controller=SimpleNamespace(ui=SimpleNamespace(tabs=SimpleNamespace(
            get_current_tab_name=MagicMock(return_value="Chat"),
            get_current_tab_name_for_audio=MagicMock(return_value="Chat"),
        ))),
        dispatch=MagicMock(),
    )
    return window


def test_actions_choices_contain_unique_control_events_and_voice_commands():
    window = make_window()
    window.core.access = SimpleNamespace(voice=SimpleNamespace(get_commands=MagicMock(return_value={"a": "A", "b": "B"})))
    actions = Actions(window)
    access_choices = actions.get_access_choices()
    keys = [next(iter(row)) for row in access_choices]
    assert ControlEvent.APP_STATUS in keys
    assert ControlEvent.CTX_INPUT_SEND in keys
    assert len(keys) == len(set(keys))
    assert actions.get_voice_control_choices() == [{"a": "A"}, {"b": "B"}]
    assert actions.get_speech_synthesis_choices()


def test_helpers_selected_values_and_context_messages(monkeypatch):
    window = make_window({"mode": "chat", "model": "gpt-x", "preset": "p1"})
    window.core.presets.get_by_id.return_value = SimpleNamespace(name="Preset One")
    window.core.ctx.get_current_meta.return_value = SimpleNamespace(name="Ctx", updated=FIXED_NOW_TS)
    mapping = {
        "mode.chat": "Chat",
        "event.audio.model.selected": "Model {model}",
        "event.audio.preset.selected": "Preset {preset}",
        "event.audio.mode.selected": "Mode {mode}",
        "event.audio.ctx.current": "Current {ctx} {last}",
        "event.audio.ctx.selected": "Selected {ctx} {last}",
        "event.audio.tab.switch": "Tab {tab}",
        "dt.today": "Today",
    }
    monkeypatch.setattr(helpers_mod, "trans", lambda key: mapping.get(key, key))
    monkeypatch.setattr(helpers_mod, "datetime", FixedDateTime)
    helper = Helpers(window)
    assert helper.get_selected_model() == "Model gpt-x"
    assert helper.get_selected_preset() == "Preset Preset One"
    assert helper.get_selected_mode() == "Mode Chat"
    assert helper.get_current_ctx() == "Current Ctx Today 12:00"
    assert helper.get_selected_ctx() == "Selected Ctx Today 12:00"
    assert helper.get_selected_tab() == "Tab Chat"


def test_helpers_convert_date_is_timezone_independent_via_epoch(monkeypatch):
    monkeypatch.setattr(helpers_mod, "datetime", FixedDateTime)
    labels = {
        "dt.today": "today",
        "dt.yesterday": "yesterday",
        "dt.week": "week",
        "dt.weeks": "weeks",
        "dt.days_ago": "days ago",
        "dt.month": "month",
    }
    monkeypatch.setattr(helpers_mod, "trans", lambda key: labels[key])
    helper = Helpers(make_window())
    day = 86400
    assert helper.convert_date(FIXED_NOW_TS) == "today 12:00"
    assert helper.convert_date(FIXED_NOW_TS - day) == "yesterday 12:00"
    assert helper.convert_date(FIXED_NOW_TS - 7 * day) == "week"
    assert helper.convert_date(FIXED_NOW_TS - 14 * day) == "2 weeks"
    assert helper.convert_date(FIXED_NOW_TS - 5 * day) == "5 days ago"
    assert helper.convert_date(FIXED_NOW_TS - 30 * day) == "month"
    assert helper.convert_date(FIXED_NOW_TS - 60 * day) == "2024-11-17"


def test_helpers_last_and_all_context_items(monkeypatch):
    window = make_window()
    items = [SimpleNamespace(input="i1", output="o1"), SimpleNamespace(input="i2", output="o2")]
    window.core.ctx.get_last.return_value = items[-1]
    window.core.ctx.get_all_items.return_value = items
    monkeypatch.setattr(helpers_mod, "trans", lambda key: "{input} -> {output}")
    helper = Helpers(window)
    assert helper.get_last_ctx_item() == "i2 -> o2"
    assert helper.get_all_ctx_items() == "i1 -> o1\ni2 -> o2"
    window.core.ctx.get_last.return_value = None
    assert helper.get_last_ctx_item() == ""


def test_voice_command_filtering_strings_and_json_extraction():
    window = make_window({
        "access.voice_control.blacklist": [{"disabled_action": ControlEvent.APP_EXIT}],
    })
    voice = Voice(window)
    commands = voice.get_commands()
    assert ControlEvent.APP_EXIT not in commands
    assert ControlEvent.APP_STATUS in commands
    text = voice.get_commands_string()
    assert f"{ControlEvent.APP_STATUS} =" in text
    numbered = voice.get_commands_string(values=True)
    assert numbered.startswith("1) ")

    payload = f'prefix {{"cmd":"{ControlEvent.APP_STATUS}","params":"x"}} suffix {{"cmd":"bad"}}'
    assert voice.extract_json(payload) == [
        {"cmd": ControlEvent.APP_STATUS, "params": "x"},
        {"cmd": "unrecognized", "params": ""},
    ]


def test_voice_invalid_json_is_logged_and_flags_use_config_lists():
    window = make_window({
        "access.audio.event.speech.disabled": [{"muted_action": "event-a"}],
        "access.voice_control.blacklist": [{"disabled_action": "event-b"}],
    })
    voice = Voice(window)
    assert voice.extract_json('{"cmd": broken}') == []
    # The regex may not produce valid JSON; malformed matches are logged when decoded.
    assert voice.is_muted("event-a") is True
    assert voice.is_muted("other") is False
    assert voice.is_blacklisted("event-b") is True
    assert voice.is_blacklisted("other") is False
    assert voice.cache_disabled(ControlEvent.APP_STATUS) is True
    assert voice.cache_disabled("custom") is False


def test_voice_recognize_commands_dispatches_kernel_call_and_parses_response():
    window = make_window({"access.voice_control.model": "custom-mini"})
    custom_model = ModelItem("custom")
    window.core.models.has.return_value = True
    window.core.models.get.return_value = custom_model

    def dispatch(event):
        assert isinstance(event, KernelEvent)
        assert event.name == KernelEvent.CALL
        assert event.data["context"].model is custom_model
        event.data["response"] = f'{{"cmd":"{ControlEvent.APP_STATUS}","params":""}}'

    window.dispatch.side_effect = dispatch
    voice = Voice(window)
    assert voice.recognize_commands("status") == [{"cmd": ControlEvent.APP_STATUS, "params": ""}]
    window.dispatch.assert_called_once()


def test_voice_prompts_include_schema_and_optional_inline_prefix():
    voice = Voice(make_window())
    assert '"cmd": "command_id"' in voice.get_prompt("open chat")
    assert "open chat" in voice.get_prompt("open chat")
    inline = voice.get_inline_prompt(prefix="computer")
    assert 'prefixed via "computer"' in inline
    assert '"cmd": "voice_cmd"' in inline
