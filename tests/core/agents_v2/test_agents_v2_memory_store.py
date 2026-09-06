#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from llama_index.core.base.llms.types import MessageRole

import pygpt_net.core.agents_v2.memory as memory_module
from pygpt_net.core.agents_v2.memory import OrchestratorMemoryStore
from pygpt_net.core.types import MODE_AGENT_V2


def make_window(items=None):
    items = list(items or [])
    window = MagicMock()
    window.core.ctx.get_or_create_slave_meta.return_value = SimpleNamespace(id=77)
    window.core.ctx.provider.load.return_value = items
    window.core.config.get.side_effect = lambda key, default=None: {
        "max_total_tokens": 1000,
    }.get(key, default)
    window.core.tokens.from_user.return_value = 25
    return window


def test_agents_v2_memory_preset_key_prefers_uuid_then_filename():
    store = OrchestratorMemoryStore(make_window())

    assert store._preset_key(None) == "agents_v2.memory:default"
    assert store._preset_key(SimpleNamespace(uuid="u1", filename="f.json")) == "agents_v2.memory:u1"
    assert store._preset_key(SimpleNamespace(uuid=None, filename="f.json")) == "agents_v2.memory:f.json"


def test_agents_v2_memory_load_history_converts_hidden_turns_to_chat_messages():
    items = [
        SimpleNamespace(input="user 1", output="assistant 1"),
        SimpleNamespace(input="", output="assistant 2"),
        SimpleNamespace(input="user 3", output=""),
    ]
    window = make_window(items)
    store = OrchestratorMemoryStore(window)

    history = store.load_history(SimpleNamespace(), SimpleNamespace(uuid="p1"))

    assert [(message.role, message.content) for message in history] == [
        (MessageRole.USER, "user 1"),
        (MessageRole.ASSISTANT, "assistant 1"),
        (MessageRole.ASSISTANT, "assistant 2"),
        (MessageRole.USER, "user 3"),
    ]
    window.core.ctx.provider.load.assert_called_once_with(77)


def test_agents_v2_memory_load_history_applies_model_context_window():
    original = [SimpleNamespace(input="old", output="answer")]
    clipped = [SimpleNamespace(input="kept", output="kept answer")]
    window = make_window(original)
    window.core.ctx.get_history.return_value = clipped
    store = OrchestratorMemoryStore(window)
    model = SimpleNamespace(id="model-x", ctx=300)

    history = store.load_history(
        master_ctx=SimpleNamespace(),
        preset=None,
        model=model,
        current_input="current prompt",
    )

    window.core.ctx.get_history.assert_called_once_with(
        original,
        "model-x",
        MODE_AGENT_V2,
        25,
        300,
        ignore_first=False,
    )
    assert [message.content for message in history] == ["kept", "kept answer"]


def test_agents_v2_memory_load_history_logs_token_window_errors_and_keeps_history():
    items = [SimpleNamespace(input="user", output="assistant")]
    window = make_window(items)
    window.core.tokens.from_user.side_effect = RuntimeError("token failure")
    store = OrchestratorMemoryStore(window)

    history = store.load_history(SimpleNamespace(), None, model=SimpleNamespace(id="m", ctx=100))

    assert [message.content for message in history] == ["user", "assistant"]
    window.core.debug.log.assert_called_once()


def test_agents_v2_memory_append_turn_creates_hidden_internal_agent_item(monkeypatch):
    created = []

    class FakeCtxItem:
        def __init__(self, mode):
            self.mode = mode
            created.append(self)

    monkeypatch.setattr(memory_module, "CtxItem", FakeCtxItem)
    window = make_window()
    store = OrchestratorMemoryStore(window)
    meta = SimpleNamespace(id=91)
    store.get_meta = MagicMock(return_value=meta)
    master = SimpleNamespace(meta=SimpleNamespace(id=1), model="model-y")

    store.append_turn(master, SimpleNamespace(uuid="preset"), "question", "answer")

    item = created[0]
    assert item.mode == MODE_AGENT_V2
    assert item.hidden is True
    assert item.internal is True
    assert item.agent_call is True
    assert item.meta is meta
    assert item.meta_id == 91
    assert item.model == "model-y"
    assert item.input == "question"
    assert item.output == "answer"
    assert item.extra == {"agents_v2_memory": True}
    window.core.ctx.add_to_meta.assert_called_once_with(item, 91)


def test_agents_v2_memory_append_turn_ignores_missing_master_meta():
    window = make_window()
    store = OrchestratorMemoryStore(window)

    store.append_turn(SimpleNamespace(meta=None), None, "q", "a")

    window.core.ctx.add_to_meta.assert_not_called()
