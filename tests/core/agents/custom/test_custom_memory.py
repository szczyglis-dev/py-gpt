#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pygpt_net.core.agents.custom.memory import MemoryManager, MemoryState


def test_memory_state_set_update_and_empty_contract_copy_items():
    state = MemoryState("mem")
    source = [{"role": "user", "content": "a"}]

    assert state.is_empty() is True
    state.set_from(source, "resp-1")
    assert state.is_empty() is False
    assert state.items == source
    assert state.items is not source
    assert state.last_response_id == "resp-1"

    state.update_from_result([], None)
    assert state.items == []
    assert state.last_response_id is None


def test_memory_manager_lazily_creates_reuses_sets_and_snapshots_states():
    manager = MemoryManager()

    first = manager.get("a")
    assert first is manager.get("a")
    assert first.mem_id == "a"

    manager.set("a", [{"x": 1}], "resp")
    assert first.items == [{"x": 1}]
    assert first.last_response_id == "resp"

    snapshot = manager.snapshot()
    assert snapshot == {"a": first}
    assert snapshot is not manager._mem
