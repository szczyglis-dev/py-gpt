#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.context_manager.budget import ContextBudget
from pygpt_net.core.context_manager.manager import ContextManager
from pygpt_net.core.types import MODE_AGENT_V2, MODE_CHAT


def make_window(config=None):
    values = {
        "context.advanced.enabled": True,
        "context.advanced.notes_max_chars": 24000,
        "context.advanced.threshold": 75,
        "context.advanced.target": 45,
        "max_total_tokens": 10000,
        "max_output_tokens": 1000,
        "context_threshold": 0,
        "mode": MODE_CHAT,
    }
    if config:
        values.update(config)
    config_obj = MagicMock()
    config_obj.get.side_effect = lambda key, default=None: values.get(key, default)
    tokens = MagicMock()
    tokens.from_text.side_effect = lambda text, model_id=None: len(str(text or ""))
    tokens.from_ctx.return_value = 17
    models = MagicMock()
    models.has.return_value = False
    models.from_defaults.return_value = SimpleNamespace(id="model-default", ctx=10000)
    window = SimpleNamespace(
        core=SimpleNamespace(
            config=config_obj,
            tokens=tokens,
            models=models,
            debug=MagicMock(),
            ctx=SimpleNamespace(provider=MagicMock()),
        ),
        threadpool=MagicMock(),
    )
    return window


def make_manager(config=None):
    manager = ContextManager(make_window(config))
    manager.store = MagicMock()
    return manager


def ctx(meta_id=7, **kwargs):
    data = {
        "meta": SimpleNamespace(id=meta_id),
        "meta_id": meta_id,
        "internal": False,
        "sub_call": False,
        "extra": {},
        "mode": MODE_CHAT,
        "model": "model-default",
    }
    data.update(kwargs)
    return SimpleNamespace(**data)


def test_enabled_and_notes_limit_config_are_defensive():
    manager = make_manager({
        "context.advanced.enabled": 1,
        "context.advanced.notes_max_chars": 500,
    })

    assert manager.enabled() is True
    assert manager.get_notes_max_chars() == 1000

    manager.window.core.config.get.side_effect = lambda key, default=None: "invalid" if key == "context.advanced.notes_max_chars" else True
    assert manager.get_notes_max_chars() == 24000


def test_limit_notes_can_preserve_stable_head_and_newest_tail():
    manager = make_manager({"context.advanced.notes_max_chars": 2000})
    value = "A" * 1600 + "B" * 1600

    prefix_only = manager.limit_notes(value)
    preserved = manager.limit_notes(value, preserve_tail=True)

    assert len(prefix_only) == 2000
    assert prefix_only.startswith("A" * 100)
    assert prefix_only.endswith("B" * 400)
    assert "\n…\n" in preserved
    assert preserved.startswith("A" * 1000)
    assert preserved.endswith("B" * 700)
    assert len(preserved) <= 2000


def test_clip_text_to_tokens_returns_empty_for_zero_budget_and_keeps_short_text():
    manager = make_manager()

    assert manager.clip_text_to_tokens("abc", "m", 0) == ""
    assert manager.clip_text_to_tokens("abc", "m", 10) == "abc"


def test_clip_text_to_tokens_bounds_dense_text_and_preserves_tail():
    manager = make_manager()
    manager.window.core.tokens.from_text.side_effect = lambda text, model_id=None: len(str(text))
    value = "HEAD-" + ("x" * 500) + "-TAIL"

    clipped = manager.clip_text_to_tokens(value, "m", 200, preserve_tail=True)

    assert len(clipped) <= 200
    assert clipped.startswith("HEAD-")
    assert clipped.endswith("-TAIL")


def test_clip_text_to_tokens_falls_back_when_tokenizer_raises():
    manager = make_manager()
    manager.window.core.tokens.from_text.side_effect = RuntimeError("tokenizer down")

    clipped = manager.clip_text_to_tokens("x" * 1000, "m", 100)

    assert clipped
    assert len(clipped) <= 500


def test_notes_for_model_uses_default_model_and_safe_share_of_input_budget():
    manager = make_manager()
    manager.get_notes = MagicMock(return_value="x" * 5000)
    manager.clip_text_to_tokens = MagicMock(return_value="clipped")
    model = SimpleNamespace(id="m", ctx=10000)
    manager.window.core.models.from_defaults.return_value = model

    result = manager.notes_for_model(ctx())

    assert result == "clipped"
    _, _, max_tokens = manager.clip_text_to_tokens.call_args.args[:3]
    assert 256 <= max_tokens <= 8192


def test_tokenizer_fn_returns_len_compatible_range_without_allocating_tokens():
    manager = make_manager()
    manager.window.core.tokens.from_text.side_effect = None
    manager.window.core.tokens.from_text.return_value = 123

    tokens = manager._tokenizer_fn("m")("payload")

    assert isinstance(tokens, range)
    assert len(tokens) == 123


def test_tool_tokens_serializes_metadata_and_adds_protocol_reserve():
    manager = make_manager()
    manager.window.core.tokens.from_text.side_effect = lambda text, model_id=None: 10
    metadata = SimpleNamespace(
        name="tool",
        description="desc",
        get_parameters_dict=lambda: {"type": "object"},
    )
    tool = SimpleNamespace(metadata=metadata)

    assert manager._tool_tokens([tool], "m") == 34


def test_tool_tokens_uses_conservative_fallback_on_serialization_failure():
    manager = make_manager()
    manager.window.core.tokens.from_text.side_effect = RuntimeError("no tokenizer")
    tool = SimpleNamespace(metadata=None)

    assert manager._tool_tokens([tool], "m") == 152


def test_configure_llm_for_rolling_context_disables_server_chain_tracking():
    manager = make_manager()
    llm = SimpleNamespace(
        track_previous_responses=True,
        _previous_response_id="resp-1",
        truncation="disabled",
    )

    assert manager.configure_llm_for_rolling_context(llm) is llm
    assert llm.track_previous_responses is False
    assert llm._previous_response_id is None
    assert llm.truncation == "auto"


def test_configure_llm_for_rolling_context_is_noop_when_disabled():
    manager = make_manager({"context.advanced.enabled": False})
    llm = SimpleNamespace(track_previous_responses=True, truncation="disabled")

    manager.configure_llm_for_rolling_context(llm)

    assert llm.track_previous_responses is True
    assert llm.truncation == "disabled"


def test_configure_maintenance_llm_caps_common_and_google_output_limits():
    manager = make_manager()
    llm = SimpleNamespace(
        max_tokens=9000,
        max_output_tokens=0,
        _generation_config={"temperature": 0.1, "max_output_tokens": 12000},
    )

    result = manager.configure_maintenance_llm(llm, 1024)

    assert result is llm
    assert llm.max_tokens == 1024
    assert llm.max_output_tokens == 1024
    assert llm._generation_config == {"temperature": 0.1, "max_output_tokens": 1024}


def test_configure_maintenance_llm_preserves_lower_existing_limits():
    manager = make_manager()
    llm = SimpleNamespace(max_tokens=200, max_output_tokens=300, _generation_config={"max_output_tokens": 400})

    manager.configure_maintenance_llm(llm, 1024)

    assert llm.max_tokens == 200
    assert llm.max_output_tokens == 300
    assert llm._generation_config["max_output_tokens"] == 400


def test_agent_memory_limit_reserves_system_tools_and_protocol_budget(monkeypatch):
    manager = make_manager()
    model = SimpleNamespace(id="m", ctx=10000)
    budget = ContextBudget(10000, 10000, 10000, 1000, 9000, 7000, 4000)
    monkeypatch.setattr("pygpt_net.core.context_manager.manager.ContextBudget.build", lambda window, value: budget)
    manager.window.core.tokens.from_text.side_effect = None
    manager.window.core.tokens.from_text.return_value = 500
    manager._tool_tokens = MagicMock(return_value=600)

    result = manager.agent_memory_limit(model, "system", [object()])

    # Protocol reserve has a hard minimum of 1024.
    assert result == 9000 - 500 - 600 - 1024
    assert manager.agent_memory_limit(None) == 40000


def test_build_agent_memory_configures_bounded_memory_and_persistent_summary(monkeypatch):
    manager = make_manager({
        "context.advanced.threshold": 75,
        "context.advanced.target": 45,
        "context.advanced.notes_max_chars": 24000,
    })
    manager.agent_memory_limit = MagicMock(return_value=10000)
    manager.notes_for_model = MagicMock(return_value="initial notes")
    manager.configure_maintenance_llm = MagicMock(side_effect=lambda llm, limit: llm)
    runtime = SimpleNamespace(
        model=SimpleNamespace(id="m", ctx=12000),
        context=SimpleNamespace(ctx=ctx(3)),
        run_id="run-1",
        get_llm=MagicMock(return_value=SimpleNamespace(name="summary-llm")),
        verbose_log=MagicMock(),
    )
    captured = {}

    class FakeBlock:
        def __init__(self, **kwargs):
            captured["block"] = kwargs

    class FakeSafeMemory:
        @classmethod
        def from_defaults(cls, **kwargs):
            captured["memory"] = kwargs
            return SimpleNamespace()

    import pygpt_net.core.context_manager.agent_memory as memory_module
    monkeypatch.setattr(memory_module, "ContinuationSummaryBlock", FakeBlock)
    monkeypatch.setattr(memory_module, "SafeAgentMemory", FakeSafeMemory)

    memory = manager.build_agent_memory(
        runtime,
        actor_id="orchestrator",
        system_prompt="system",
        tools=["tool"],
        persistent=True,
    )

    assert memory is not None
    manager.agent_memory_limit.assert_called_once_with(runtime.model, "system", ["tool"])
    runtime.get_llm.assert_called_once_with(
        stream=False, actor_id="orchestrator:context-memory", allow_remote_tools=False,
    )
    assert captured["block"]["persistent"] is True
    assert captured["block"]["summary"] == "initial notes"
    assert captured["block"]["ctx"] is runtime.context.ctx
    assert captured["memory"]["token_limit"] == 10000
    assert captured["memory"]["chat_history_token_ratio"] == 0.75
    assert captured["memory"]["token_flush_size"] == 3000
    assert captured["memory"]["memory_blocks"]
    runtime.verbose_log.assert_called_once()


def test_meta_id_prefers_meta_object_then_meta_id_fallback():
    assert ContextManager._meta_id(SimpleNamespace(meta=SimpleNamespace(id="9"), meta_id=3)) == 9
    assert ContextManager._meta_id(SimpleNamespace(meta=None, meta_id="4")) == 4
    assert ContextManager._meta_id(SimpleNamespace(meta=None, meta_id=0)) is None
    assert ContextManager._meta_id(None, SimpleNamespace(id=5)) == 5


def test_get_and_get_notes_return_safe_default_on_store_error():
    manager = make_manager()
    manager.store.get.side_effect = RuntimeError("db")
    item = ctx(4)

    state = manager.get(item)

    assert state["meta_id"] == 4
    assert state["content"] == ""
    assert manager.get_notes(item) == ""
    manager.window.core.debug.log.assert_called()


def test_add_replace_and_commit_notes_use_store_with_limits():
    manager = make_manager({"context.advanced.notes_max_chars": 1000})
    item = ctx(2)
    manager.store.content.return_value = "old"
    manager.store.replace.side_effect = lambda meta_id, text: text
    manager.store.runtime_summary.return_value = {"content": "runtime"}

    assert manager.add_notes(item, " new ") == "old\nnew"
    assert manager.replace_notes(item, "x" * 1200) == "x" * 1000
    saved = manager.commit_runtime_summary(item, "summary", expected_revision=3, last_item_id=8)

    assert saved == {"content": "runtime"}
    manager.store.runtime_summary.assert_called_once_with(
        2, "summary", expected_revision=3, last_item_id=8,
    )


def test_add_replace_notes_require_active_conversation():
    manager = make_manager()
    missing = SimpleNamespace(meta=None, meta_id=None)

    with pytest.raises(ValueError):
        manager.add_notes(missing, "x")
    with pytest.raises(ValueError):
        manager.replace_notes(missing, "x")


def test_prepare_system_prompt_adds_policy_and_chat_continuation_but_not_agent_v2_copy():
    manager = make_manager()
    item = ctx(7)
    manager.get = MagicMock(return_value={"generation": 3, "last_item_id": 42, "content": "notes"})
    manager.notes_for_model = MagicMock(return_value="canonical notes")

    chat_prompt = manager.prepare_system_prompt("base", item, MODE_CHAT, model=object())
    agent_prompt = manager.prepare_system_prompt("base", item, MODE_AGENT_V2, model=object())

    assert "<context_management>" in chat_prompt
    assert '<context_continuation generation="3" summarized_through_item_id="42">' in chat_prompt
    assert "canonical notes" in chat_prompt
    assert "<context_management>" in agent_prompt
    assert "<context_continuation " not in agent_prompt


def test_prepare_system_prompt_is_noop_for_disabled_or_internal_requests():
    manager = make_manager({"context.advanced.enabled": False})
    assert manager.prepare_system_prompt("base", ctx(), MODE_CHAT) == "base"

    manager = make_manager()
    assert manager.prepare_system_prompt("base", ctx(), MODE_CHAT, internal=True) == "base"
    assert manager.prepare_system_prompt("base", ctx(internal=True), MODE_CHAT) == "base"


def test_fit_history_limit_applies_model_safe_limit_only_when_enabled(monkeypatch):
    disabled = make_manager({"context.advanced.enabled": False})
    assert disabled.fit_history_limit("m", 5000) == 5000

    manager = make_manager()
    model = SimpleNamespace(id="m", ctx=10000)
    manager.window.core.models.has.return_value = True
    manager.window.core.models.get.return_value = model
    budget = ContextBudget(10000, 10000, 10000, 1000, 7000, 5000, 3000)
    monkeypatch.setattr("pygpt_net.core.context_manager.manager.ContextBudget.build", lambda window, value: budget)

    assert manager.fit_history_limit("m", 9000) == 7000
    assert manager.fit_history_limit("m", 0) == 7000


def test_filter_history_drops_items_at_or_below_checkpoint_floor():
    manager = make_manager()
    manager.store.get.return_value = {"last_item_id": 3}
    items = [ctx(1, id=1), ctx(1, id=2), ctx(1, id=4), ctx(1, id=0)]

    result = manager.filter_history(items)

    assert [item.id for item in result] == [4, 0]


def test_filter_agents_v2_items_uses_source_item_marker():
    manager = make_manager()
    manager.get = MagicMock(return_value={"last_item_id": 10})
    items = [
        SimpleNamespace(extra={"agents_v2_source_item_id": 4}),
        SimpleNamespace(extra={"agents_v2_source_item_id": 11}),
        SimpleNamespace(extra={}),
    ]

    result = manager.filter_agents_v2_items(items, ctx())

    assert result == items[1:]


def test_mark_request_generation_and_server_chain_break_detection():
    manager = make_manager()
    item = ctx(extra=None)
    manager.get = MagicMock(return_value={"generation": 2})

    manager.mark_request_generation(item)

    assert item.extra["context_generation"] == 2
    older = SimpleNamespace(msg_id="resp", extra={"context_generation": 1})
    current = SimpleNamespace(msg_id="resp2", extra={"context_generation": 2})
    assert manager.should_break_server_chain([older], item) is True
    assert manager.should_break_server_chain([current], item) is False


def test_item_tokens_uses_agents_v2_text_projection_and_normal_ctx_counter():
    manager = make_manager()
    manager.window.core.tokens.from_text.side_effect = lambda text, model_id=None: 33
    manager.window.core.tokens.from_ctx.return_value = 44
    agent_item = SimpleNamespace(mode=MODE_AGENT_V2, final_input="u", parts=[], output="a")
    normal_item = SimpleNamespace(mode=MODE_CHAT)

    assert manager._item_tokens(agent_item, "m", MODE_CHAT) == 33
    assert manager._item_tokens(normal_item, "m", MODE_CHAT) == 44


def test_assistant_snapshot_prefers_parts_and_worker_context_without_raw_tool_payloads():
    item = SimpleNamespace(
        parts=[
            SimpleNamespace(output="step", extra={"worker_context": [
                {"name": "Coder", "result": "patched"},
                {"worker": "Researcher", "output": "found"},
            ]}),
        ],
        output="fallback",
    )

    manager = make_manager()
    snapshot = manager._assistant_snapshot(item)

    assert snapshot == "step\n\n[Coder] patched\n\n[Researcher] found"


def test_assistant_snapshot_falls_back_to_agent_response_then_output():
    with_agent = SimpleNamespace(
        parts=[], output="raw", get_agents_v2_response_output=lambda: "agent final",
    )
    without_agent = SimpleNamespace(
        parts=[], output="raw", get_agents_v2_response_output=lambda: "",
    )

    manager = make_manager()
    assert manager._assistant_snapshot(with_agent) == "agent final"
    assert manager._assistant_snapshot(without_agent) == "raw"


def test_build_snapshot_uses_durable_input_and_assistant_state_only():
    manager = make_manager()
    item = SimpleNamespace(
        id=3,
        final_input="user durable",
        hidden_input="do not persist",
        parts=[],
        output="assistant durable",
        get_agents_v2_response_output=lambda: "",
    )

    snapshot = manager.build_snapshot([item])

    assert '<turn id="3">' in snapshot
    assert "user durable" in snapshot
    assert "assistant durable" in snapshot
    assert "do not persist" not in snapshot


def test_checkpoint_input_split_and_clean_helpers():
    manager = make_manager()
    prompt = manager.build_checkpoint_input("notes", "segment")

    assert "<existing_continuation_notes>\nnotes" in prompt
    assert "<conversation_segment_to_compact>\nsegment" in prompt
    assert manager.clean_checkpoint_output("```text\nhello\n```") == "hello"
    assert manager.clean_checkpoint_output(" plain ") == "plain"
    assert manager.split_checkpoint_snapshot("", "m", 100) == []

    manager.window.core.tokens.from_text.side_effect = lambda text, model_id=None: len(str(text))
    chunks = manager.split_checkpoint_snapshot("A" * 500, "m", 128)
    assert "".join(chunks) == "A" * 500
    assert all(len(chunk) <= 128 for chunk in chunks)


def test_checkpoint_plan_selects_old_turns_and_keeps_recent_tail(monkeypatch):
    manager = make_manager()
    item = ctx(1, model="m", id=99, mode=MODE_CHAT)
    manager.window.core.models.has.return_value = True
    manager.window.core.models.get.return_value = SimpleNamespace(id="m", ctx=1000)
    manager.store.get.return_value = {
        "last_item_id": 0,
        "revision": 4,
        "content": "notes",
    }
    turns = []
    for turn_id in (1, 2, 3, 4):
        turns.append(SimpleNamespace(
            id=turn_id,
            internal=False,
            hidden=False,
            mode=MODE_CHAT,
            final_input=f"u{turn_id}",
            parts=[],
            output=f"a{turn_id}",
            get_agents_v2_response_output=lambda: "",
        ))
    manager.window.core.ctx.provider.load.return_value = turns
    manager._item_tokens = MagicMock(return_value=100)
    manager.window.core.tokens.from_text.side_effect = lambda text, model_id=None: 10
    budget = ContextBudget(1000, 1000, 1000, 100, 900, 300, 150)
    monkeypatch.setattr("pygpt_net.core.context_manager.manager.ContextBudget.build", lambda window, model: budget)

    plan = manager._checkpoint_plan(item)

    assert plan["meta_id"] == 1
    assert plan["revision"] == 4
    assert plan["last_item_id"] == 3
    assert '<turn id="1">' in plan["snapshot"]
    assert '<turn id="2">' in plan["snapshot"]
    assert '<turn id="3">' in plan["snapshot"]
    assert '<turn id="4">' not in plan["snapshot"]


def test_on_ctx_end_avoids_duplicate_pending_checkpoint(monkeypatch):
    manager = make_manager()
    plan = {"meta_id": 7}
    manager._checkpoint_plan = MagicMock(return_value=plan)
    fake_worker = object()
    with patch("pygpt_net.core.context_manager.checkpoint.ContextCheckpointWorker", return_value=fake_worker) as worker_cls:
        manager.on_ctx_end(ctx(7))
        manager.on_ctx_end(ctx(7))

    worker_cls.assert_called_once_with(manager, plan)
    manager.window.threadpool.start.assert_called_once_with(fake_worker)
    assert 7 in manager._pending

    manager.finish_checkpoint("7")
    assert 7 not in manager._pending


def test_build_agent_tools_is_disabled_with_context_and_delegates_when_enabled(monkeypatch):
    disabled = make_manager({"context.advanced.enabled": False})
    assert disabled.build_agent_tools(ctx()) == []

    manager = make_manager()
    expected = [object()]
    monkeypatch.setattr("pygpt_net.core.context_manager.tools.build_context_tools", lambda mgr, item: expected)
    assert manager.build_agent_tools(ctx()) is expected
