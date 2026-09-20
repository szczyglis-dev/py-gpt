#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from llama_index.core.base.llms.types import MessageRole

from pygpt_net.core.agents_v2.memory import OrchestratorMemoryStore
from pygpt_net.core.context_manager.constants import SOURCE_ITEM_KWARG
from pygpt_net.core.types import MODE_AGENT_V2


ROOT_META_ID = 11


def make_master(item_id=999, meta_id=ROOT_META_ID):
    return SimpleNamespace(
        id=item_id,
        meta=SimpleNamespace(id=meta_id),
        model="model-y",
    )


def make_window(root_items=None):
    root_items = list(root_items or [])
    window = MagicMock()

    def load(meta_id):
        if meta_id == ROOT_META_ID:
            return root_items
        return []

    window.core.ctx.provider.load.side_effect = load
    window.core.config.get.side_effect = lambda key, default=None: {
        "max_total_tokens": 1000,
    }.get(key, default)
    window.core.tokens.from_user.return_value = 25
    window.core.tokens.from_ctx.return_value = 10
    window.core.context_manager.enabled.return_value = False
    window.core.context_manager.filter_agents_v2_items.side_effect = lambda values, master: values
    return window


def source_item(
        input_text="",
        output_text="",
        *,
        item_id=1,
        mode="chat",
        extra=None,
        parts=None,
        hidden=False,
        internal=False,
):
    item = SimpleNamespace(
        id=item_id,
        input=input_text,
        final_input=input_text,
        output=output_text,
        final_output=output_text,
        parts=list(parts or []),
        active_part=None,
        extra=dict(extra or {}),
        hidden=hidden,
        internal=internal,
        mode=mode,
    )
    item.get_agents_v2_final_output = lambda: next(
        (
            part.output
            for part in reversed(item.parts)
            if isinstance(getattr(part, "extra", None), dict)
            and part.extra.get("agents_v2_final") is True
        ),
        None,
    )
    return item


def agent_part(output_text, *, part_id=1, created_at=1, extra=None):
    return SimpleNamespace(
        id=part_id,
        created_at=created_at,
        output=output_text,
        extra=dict(extra or {}),
    )


def test_agents_v2_history_is_conversation_scoped_and_does_not_lookup_preset_memory():
    root = source_item("question", "answer", item_id=10, mode="chat")
    window = make_window([root])
    store = OrchestratorMemoryStore(window)

    history_a = store.load_history(make_master(), SimpleNamespace(uuid="primary-a"))
    history_b = store.load_history(make_master(), SimpleNamespace(uuid="primary-b"))

    expected = [
        (MessageRole.USER, "question"),
        (MessageRole.ASSISTANT, "answer"),
    ]
    assert [(message.role, message.content) for message in history_a] == expected
    assert [(message.role, message.content) for message in history_b] == expected
    assert window.core.ctx.provider.load.call_count == 2
    window.core.ctx.get_or_create_slave_meta.assert_not_called()
    window.core.ctx.provider.get_meta_by_root_id_and_preset_id.assert_not_called()


def test_agents_v2_history_load_applies_model_context_window_to_root_projection():
    original = [source_item("old", "answer", item_id=10)]
    clipped = [source_item("kept", "kept answer", item_id=10)]
    window = make_window(original)
    window.core.ctx.get_history.return_value = clipped
    store = OrchestratorMemoryStore(window)
    model = SimpleNamespace(id="model-x", ctx=300)

    history = store.load_history(
        master_ctx=make_master(),
        model=model,
        current_input="current prompt",
    )

    window.core.ctx.get_history.assert_called_once()
    args, kwargs = window.core.ctx.get_history.call_args
    prepared = args[0]
    assert len(prepared) == 1
    assert prepared[0] is not original[0]
    assert prepared[0].input == "old"
    assert prepared[0].output == "answer"
    assert prepared[0].parts == []
    assert prepared[0].active_part is None
    assert args[1:] == ("model-x", MODE_AGENT_V2, 25, 300)
    assert kwargs == {"ignore_first": False}
    assert [message.content for message in history] == ["kept", "kept answer"]


def test_agents_v2_history_load_logs_token_window_errors_and_keeps_history():
    root = source_item("user", "assistant", item_id=10)
    window = make_window([root])
    window.core.tokens.from_user.side_effect = RuntimeError("token failure")
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master(), model=SimpleNamespace(id="m", ctx=100))

    assert [message.content for message in history] == ["user", "assistant"]
    window.core.debug.log.assert_called_once()


def test_agents_v2_history_includes_normal_mode_root_ctx_items():
    root = source_item("chat question", "chat answer", item_id=10, mode="chat")
    window = make_window([root])
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master())

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "chat question"),
        (MessageRole.ASSISTANT, "chat answer"),
    ]


def test_agents_v2_history_rebuilds_completed_agent_turn_from_root_partials():
    root = source_item(
        "agent question",
        "compact fallback",
        item_id=20,
        mode=MODE_AGENT_V2,
        extra={"response_final": True},
        parts=[agent_part("final from partial", extra={"agents_v2_final": True})],
    )
    window = make_window([root])
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master())

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "agent question"),
        (MessageRole.ASSISTANT, "final from partial"),
    ]


def test_agents_v2_history_accepts_durable_final_partial_without_parent_final_marker():
    root = source_item(
        "legacy agent question",
        "compact fallback",
        item_id=21,
        mode=MODE_AGENT_V2,
        extra={},
        parts=[agent_part("durable final", extra={"agents_v2_final": True})],
    )
    window = make_window([root])
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master())

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "legacy agent question"),
        (MessageRole.ASSISTANT, "durable final"),
    ]


def test_agents_v2_history_keeps_previous_interrupted_agent_turn_as_user_only():
    root = source_item(
        "unfinished question",
        "transient partial output",
        item_id=20,
        mode=MODE_AGENT_V2,
        extra={"response_interrupted": True},
        parts=[agent_part("transient partial output")],
    )
    window = make_window([root])
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master())

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "unfinished question"),
    ]


def test_agents_v2_history_excludes_current_root_item_from_replay():
    previous = source_item("previous", "answer", item_id=20, mode="chat")
    current = source_item(
        "current request",
        "",
        item_id=30,
        mode=MODE_AGENT_V2,
        extra={},
    )
    window = make_window([previous, current])
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master(item_id=30), current_input="current request")

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "previous"),
        (MessageRole.ASSISTANT, "answer"),
    ]


def test_agents_v2_history_replays_worker_context_as_separate_runtime_input():
    part = agent_part(
        "Primary progress",
        part_id=1,
        created_at=1,
        extra={
            "worker_context": [
                {
                    "id": "w1",
                    "name": "Researcher",
                    "output": "Worker final",
                    "created_at": 2,
                }
            ]
        },
    )
    final = agent_part(
        "Primary final",
        part_id=2,
        created_at=3,
        extra={"agents_v2_final": True},
    )
    root = source_item(
        "agent question",
        "Primary final",
        item_id=20,
        mode=MODE_AGENT_V2,
        extra={"response_final": True},
        parts=[part, final],
    )
    window = make_window([root])
    store = OrchestratorMemoryStore(window)

    history = store.load_history(make_master())

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "agent question"),
        (MessageRole.ASSISTANT, "Primary progress"),
        (
            MessageRole.USER,
            '<agents_runtime_context type="worker_result">\n'
            '<worker_context name="Researcher" source="delegated_agent">\n'
            'Worker final\n'
            '</worker_context>\n'
            '</agents_runtime_context>',
        ),
        (MessageRole.ASSISTANT, "Primary final"),
    ]
    assert SOURCE_ITEM_KWARG not in history[1].additional_kwargs
    assert SOURCE_ITEM_KWARG not in history[2].additional_kwargs
    assert history[3].additional_kwargs[SOURCE_ITEM_KWARG] == 20


def test_agents_v2_history_merges_adjacent_worker_results_into_one_runtime_input():
    part = agent_part(
        "Delegating",
        extra={
            "worker_context": [
                {"id": "w2", "name": "Second", "output": "B", "created_at": 3},
                {"id": "w1", "name": "First", "output": "A", "created_at": 2},
            ]
        },
    )
    final = agent_part("Done", part_id=2, created_at=4, extra={"agents_v2_final": True})
    root = source_item(
        "question",
        "Done",
        item_id=21,
        mode=MODE_AGENT_V2,
        extra={"response_final": True},
        parts=[part, final],
    )
    store = OrchestratorMemoryStore(make_window([root]))

    history = store.load_history(make_master())

    assert [message.role for message in history] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    runtime_context = history[2].content
    assert runtime_context.index('name="First"') < runtime_context.index('name="Second"')
    assert "A" in runtime_context
    assert "B" in runtime_context
    assert "worker_context" not in history[1].content
    assert "worker_context" not in history[3].content


def test_agents_v2_history_count_tokens_uses_same_root_projection_as_history():
    normal = source_item("chat question", "chat answer", item_id=10, mode="chat")
    agent = source_item(
        "agent question",
        "agent fallback",
        item_id=20,
        mode=MODE_AGENT_V2,
        extra={"response_final": True},
        parts=[agent_part("agent final", extra={"agents_v2_final": True})],
    )
    window = make_window([normal, agent])
    store = OrchestratorMemoryStore(window)
    model = SimpleNamespace(id="model-x", ctx=1000)

    count, tokens = store.count_history_tokens(make_master(), model=model)

    assert count == 2
    assert tokens == 20
    assert window.core.tokens.from_ctx.call_count == 2
    projected_items = [args[0] for args, _ in window.core.tokens.from_ctx.call_args_list]
    assert [item.output for item in projected_items] == ["chat answer", "agent final"]


def test_agents_v2_legacy_memory_write_helpers_do_not_create_duplicate_ctx_items():
    window = make_window()
    store = OrchestratorMemoryStore(window)
    master = make_master()

    turn = store.begin_turn(master, SimpleNamespace(uuid="old-preset"), "question")
    store.complete_turn(turn, "answer")
    appended = store.append_turn(master, SimpleNamespace(uuid="old-preset"), "question", "answer")

    assert turn is master
    assert appended is master
    window.core.ctx.add_to_meta.assert_not_called()
    window.core.ctx.update_item.assert_not_called()
