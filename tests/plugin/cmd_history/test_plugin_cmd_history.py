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


def test_summary_prompt_formatting_and_invalid_template(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.set_option_value("prompt_tag_summary", "ID={id}; Q={query}")
    assert plugin._format_prompt("prompt_tag_summary", id=12, query="current request") == (
        "ID=12; Q=current request"
    )

    plugin.set_option_value("prompt_tag_summary", "{missing}")
    plugin.log = MagicMock()
    assert plugin._format_prompt("prompt_tag_summary", id=12, query="q") == ""
    plugin.log.assert_called_once()


def test_handle_routes_model_refresh_and_command_events(mock_window):
    plugin = Plugin(window=mock_window)
    ctx = CtxItem()

    # Numeric conversation mentions are resolved by controller.chat.input now;
    # cmd_history remains callable even when the plugin itself is disabled.
    event = Event()
    event.ctx = ctx
    event.name = Event.USER_SEND
    event.data = {"value": "hello @12"}
    plugin.handle(event)
    assert not hasattr(plugin, "input_text")

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


def test_summary_lookup_uses_recent_first_chunks_and_reduces(mock_window):
    plugin = Plugin(window=mock_window)
    mock_window.core.ctx.get_items_by_id.return_value = []
    assert plugin.get_summary(1, "p") == ""

    model = ModelItem()
    mock_window.core.ctx.get_items_by_id.return_value = ["old", "new"]
    plugin._get_summary_model = MagicMock(return_value=model)
    plugin._clip_query = MagicMock(return_value="current question")
    plugin._format_prompt = MagicMock(side_effect=["extract prompt", "reduce prompt"])
    plugin._summary_max_tokens = MagicMock(return_value=55)
    plugin._input_budget = MagicMock(return_value=200)
    plugin._pack_recent_first = MagicMock(return_value=["new", "old"])
    plugin._call_model = MagicMock(side_effect=["NEW EXTRACT", "OLD EXTRACT"])
    plugin._reduce_extracts = MagicMock(return_value="FINAL")

    assert plugin.get_summary(7, "question") == "FINAL"
    plugin._pack_recent_first.assert_called_once_with(["old", "new"], model, 200)
    assert plugin._call_model.call_count == 2
    first_prompt = plugin._call_model.call_args_list[0].args[0]
    assert 'id="7"' in first_prompt
    assert 'recency_rank="1"' in first_prompt
    assert "new" in first_prompt
    plugin._reduce_extracts.assert_called_once_with(
        id=7,
        query="current question",
        extracts=["NEW EXTRACT", "OLD EXTRACT"],
        model=model,
        sys_prompt="reduce prompt",
        max_tokens=55,
    )


def test_call_model_dispatches_bridge_kernel_event(mock_window):
    plugin = Plugin(window=mock_window)
    model = ModelItem()

    def dispatch(event):
        event.data["response"] = "  ANSWER  "

    mock_window.dispatch.side_effect = dispatch
    assert plugin._call_model("chunk", "system", model, 55) == "ANSWER"

    event = mock_window.dispatch.call_args.args[0]
    assert event.name == "kernel.call"
    context = event.data["context"]
    assert context.prompt == "chunk"
    assert context.system_prompt == "system"
    assert context.max_tokens == 55
    assert context.model is model


def test_summary_model_selection_uses_configured_model(mock_window):
    plugin = Plugin(window=mock_window)
    default_model = ModelItem()
    chosen_model = ModelItem()
    mock_window.core.models.from_defaults.return_value = default_model
    mock_window.core.models.has.return_value = True
    mock_window.core.models.get.return_value = chosen_model
    plugin.set_option_value("model_summarize", "chosen")

    assert plugin._get_summary_model() is chosen_model
    mock_window.core.models.get.assert_called_once_with("chosen")


def test_split_text_to_budget_and_pack_recent_first(mock_window):
    plugin = Plugin(window=mock_window)
    model = ModelItem()
    plugin._count_tokens = MagicMock(side_effect=lambda text, _model: len(str(text or "")))
    plugin._char_chunk_limit = MagicMock(return_value=1000)

    assert plugin._split_text_to_budget("abcde", model, 2) == ["ab", "cd", "e"]
    assert plugin._pack_recent_first(["old", "new"], model, 4) == ["new", "old"]


def test_normalize_summary_filters_empty_and_legacy_sentinel(mock_window):
    plugin = Plugin(window=mock_window)
    assert plugin._normalize_summary("") == ""
    assert plugin._normalize_summary("  NO_RELEVANT_CONTEXT  ") == ""
    assert plugin._normalize_summary("  useful context  ") == "useful context"


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
