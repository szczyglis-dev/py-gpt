from datetime import datetime
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.plugin.cmd_history import Plugin
from pygpt_net.plugin.cmd_history.worker import Worker
from tests.mocks import mock_window


def test_history_options_and_command_syntax(mock_window):
    plugin = Plugin(window=mock_window)
    data = {"cmd": []}
    plugin.cmd_syntax(data)
    assert [x["cmd"] for x in data["cmd"]] == [
        cmd for cmd in plugin.allowed_cmds if plugin.has_cmd(cmd)
    ]


def test_system_prompt_uses_fixed_clock_without_local_timezone_dependency(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.controller.plugins.is_type_enabled.return_value = False
    fixed = datetime(2030, 1, 2, 3, 4, 5)
    with patch("pygpt_net.plugin.cmd_history.plugin.datetime") as dt_mock:
        dt_mock.now.return_value = fixed
        result = plugin.on_system_prompt("base")
    assert result == "base\nCurrent time is: Wednesday, 2030-01-02 03:04:05"


def test_system_prompt_does_not_duplicate_time_when_time_plugin_enabled(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.controller.plugins.is_type_enabled.return_value = True
    assert plugin.on_system_prompt("base") == "base"


def test_extract_tags_and_user_send(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.extract_tags("see @12 and @003, ignore @abc") == ["12", "003"]
    plugin.on_user_send("hello @12")
    assert plugin.input_text == "hello @12"


def test_handle_tags_uses_numeric_ids_and_serializes_contexts(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.input_text = "compare @12 @34"
    plugin.set_option_value("prompt_tag_summary", "ID={id}; Q={query}")
    plugin.get_summary = MagicMock(side_effect=["one", "two"])
    plugin.log = MagicMock()
    result = plugin.handle_tags(plugin.input_text)
    assert result == '[{"12": "one"}, {"34": "two"}]'
    assert plugin.get_summary.call_args_list[0].args == (12, "ID=12; Q=compare @12 @34")
    assert plugin.get_summary.call_args_list[1].args == (34, "ID=34; Q=compare @12 @34")


def test_handle_tags_invalid_prompt_template_returns_empty(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.input_text = "@12"
    plugin.set_option_value("prompt_tag_summary", "{missing}")
    plugin.log = MagicMock()
    assert plugin.handle_tags(plugin.input_text) == ""
    plugin.log.assert_called_once()


def test_post_prompt_skips_internal_context_and_resets_input(mock_window):
    plugin = Plugin(window=mock_window)
    ctx = CtxItem()
    ctx.internal = True
    plugin.input_text = "@1"
    assert plugin.on_post_prompt("base", ctx) == "base"
    assert plugin.input_text == "@1"

    ctx.internal = False
    plugin.set_option_value("use_tags", True)
    plugin.set_option_value("prompt_tag_system", "Use: {context}")
    plugin.handle_tags = MagicMock(return_value="summary")
    assert plugin.on_post_prompt("base", ctx) == "base\nUse: summary"
    assert plugin.input_text is None


def test_handle_routes_user_send_model_refresh_and_command_events(mock_window):
    plugin = Plugin(window=mock_window)
    ctx = CtxItem()

    event = Event()
    event.ctx = ctx
    event.name = Event.USER_SEND
    event.data = {"value": "hello"}
    plugin.handle(event)
    assert plugin.input_text == "hello"

    plugin.refresh_option = MagicMock()
    event.name = Event.MODELS_CHANGED
    event.data = {}
    plugin.handle(event)
    plugin.refresh_option.assert_called_once_with("model_summarize")

    plugin.cmd = MagicMock()
    event.name = Event.CMD_INLINE
    event.data = {"commands": [{"cmd": "get_day_note", "params": {}}]}
    plugin.handle(event)
    plugin.cmd.assert_called_once_with(ctx, event.data["commands"])


def test_cmd_filters_disabled_commands_and_routes_worker(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.cmd_prepare = MagicMock()
    plugin.is_async = MagicMock(return_value=False)
    cmd = next(x for x in plugin.allowed_cmds if plugin.has_cmd(x))
    ctx = CtxItem()

    worker = MagicMock()
    fake_mod = ModuleType("pygpt_net.plugin.cmd_history.worker")
    fake_mod.Worker = MagicMock(return_value=worker)
    with patch.dict("sys.modules", {"pygpt_net.plugin.cmd_history.worker": fake_mod}):
        plugin.cmd(ctx, [{"cmd": "not_history", "params": {}}])
        fake_mod.Worker.assert_not_called()
        request = {"cmd": cmd, "params": {}}
        plugin.cmd(ctx, [request])

    worker.from_defaults.assert_called_once_with(plugin)
    worker.signals.updated.connect.assert_called_once_with(plugin.handle_updated)
    worker.run.assert_called_once_with()


def test_calendar_note_and_context_helpers_delegate(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.calendar.load_note.return_value = "note"
    mock_window.core.calendar.append_to_note.return_value = True
    mock_window.core.calendar.update_note.return_value = True
    mock_window.core.calendar.remove_note.return_value = True
    assert plugin.get_day_note(2026, 9, 6) == "note"
    assert plugin.add_day_note(2026, 9, 6, "x") is True
    assert plugin.update_day_note(2026, 9, 6, "x") is True
    assert plugin.remove_day_note(2026, 9, 6) is True

    plugin.set_option_value("ctx_items_limit", 17)
    mock_window.core.ctx.get_list_in_date_range.return_value = [1, 2]
    assert plugin.get_list("2026-09") == [1, 2]
    mock_window.core.ctx.get_list_in_date_range.assert_called_once_with("2026-09", limit=17)

    mock_window.core.ctx.provider.get_ctx_count_by_day.return_value = {"count": 2}
    assert plugin.count_ctx_in_date(2026, 9, 6) == {"count": 2}


def test_chunking_and_summary_lookup(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin.to_chunks("", 2) == []
    assert plugin.to_chunks(None, 2) == []
    assert plugin.to_chunks("abcde", 2) == ["ab", "cd", "e"]

    mock_window.core.ctx.get_items_by_id.return_value = []
    assert plugin.get_summary(1, "p") == ""

    mock_window.core.ctx.get_items_by_id.return_value = ["abc", "def"]
    plugin.set_option_value("chunk_size", 3)
    plugin.get_summarized_text = MagicMock(return_value="SUM")
    assert plugin.get_summary(1, "prompt") == "SUM"
    plugin.get_summarized_text.assert_called_once_with(["abc", "\nde", "f"], "prompt")


def test_get_summarized_text_dispatches_each_chunk_and_joins_responses(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("summary_max_tokens", 55)
    plugin.set_option_value("summary_model", "chosen")
    default_model = ModelItem()
    chosen_model = ModelItem()
    mock_window.core.models.from_defaults.return_value = default_model
    mock_window.core.models.has.return_value = True
    mock_window.core.models.get.return_value = chosen_model

    responses = iter(["A", "B"])
    def dispatch(event):
        event.data["response"] = next(responses)
    mock_window.dispatch.side_effect = dispatch

    assert plugin.get_summarized_text(["one", "two"], "system") == "AB"
    assert mock_window.dispatch.call_count == 2
    first_event = mock_window.dispatch.call_args_list[0].args[0]
    assert first_event.data["context"].prompt == "one"
    assert first_event.data["context"].system_prompt == "system"
    assert first_event.data["context"].max_tokens == 55
    assert first_event.data["context"].model is chosen_model


def test_handle_updated_refreshes_calendar(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.handle_updated()
    mock_window.controller.calendar.setup.assert_called_once_with()


@pytest.mark.parametrize(
    "method_name,item,plugin_method,expected_args,emits_update",
    [
        ("cmd_get_ctx_list_in_date_range", {"cmd": "x", "params": {"range_query": "2026-09"}}, "get_list", ("2026-09",), False),
        ("cmd_get_ctx_content_by_id", {"cmd": "x", "params": {"id": "7", "summary_query": "sum"}}, "get_summary", (7, "sum"), False),
        ("cmd_get_day_note", {"cmd": "x", "params": {"year": "2026", "month": "9", "day": "6"}}, "get_day_note", (2026, 9, 6), False),
        ("cmd_add_day_note", {"cmd": "x", "params": {"year": "2026", "month": "9", "day": "6", "note": "n"}}, "add_day_note", (2026, 9, 6, "n"), True),
        ("cmd_update_day_note", {"cmd": "x", "params": {"year": "2026", "month": "9", "day": "6", "content": "n"}}, "update_day_note", (2026, 9, 6, "n"), True),
        ("cmd_remove_day_note", {"cmd": "x", "params": {"year": "2026", "month": "9", "day": "6"}}, "remove_day_note", (2026, 9, 6), True),
        ("cmd_count_ctx_in_date", {"cmd": "x", "params": {"year": "2026", "month": "9", "day": "6"}}, "count_ctx_in_date", (2026, 9, 6), False),
    ],
)
def test_worker_command_helpers(method_name, item, plugin_method, expected_args, emits_update):
    plugin = MagicMock()
    getattr(plugin, plugin_method).return_value = "RESULT"
    worker = Worker()
    worker.plugin = plugin

    # PySide6 SignalInstance.emit is read-only, so replace the signals
    # container instead of trying to monkeypatch the bound emit method.
    worker.signals = MagicMock()

    response = getattr(worker, method_name)(item)

    getattr(plugin, plugin_method).assert_called_once_with(*expected_args)
    assert response["result"] == "RESULT"
    if emits_update:
        worker.signals.updated.emit.assert_called_once_with()
    else:
        worker.signals.updated.emit.assert_not_called()


def test_worker_run_dispatches_known_commands_and_cleans_up():
    worker = Worker()
    worker.cmds = [{"cmd": "get_ctx_list_in_date_range", "params": {}}]
    worker.is_stopped = MagicMock(return_value=False)
    worker.cmd_get_ctx_list_in_date_range = MagicMock(return_value={"result": "ok"})
    worker.reply_more = MagicMock()
    worker.cleanup = MagicMock()
    worker.run()
    worker.reply_more.assert_called_once_with([{"result": "ok"}])
    worker.cleanup.assert_called_once_with()
