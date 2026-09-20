#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.context_manager.checkpoint as checkpoint_module
from pygpt_net.core.context_manager.checkpoint import ContextCheckpointWorker


def make_manager(plan=None):
    config = MagicMock()
    tokens = MagicMock()
    tokens.from_text.side_effect = lambda text, model_id=None: max(1, len(str(text or "")) // 4)
    models = MagicMock()
    models.has.return_value = False
    models.from_defaults.return_value = SimpleNamespace(id="default")
    window = SimpleNamespace(
        core=SimpleNamespace(
            config=config,
            tokens=tokens,
            models=models,
            debug=MagicMock(),
        ),
        dispatch=MagicMock(),
    )
    manager = MagicMock()
    manager.window = window
    manager.get_notes_max_chars.return_value = 12000
    manager.limit_notes.side_effect = lambda text, preserve_tail=False: str(text or "").strip()
    manager.clip_text_to_tokens.side_effect = lambda text, model_id, max_tokens, preserve_tail=True: str(text or "").strip()
    manager.build_checkpoint_input.side_effect = lambda state, chunk: f"STATE={state}\nCHUNK={chunk}"
    manager.clean_checkpoint_output.side_effect = lambda text: str(text or "").strip()
    manager.split_checkpoint_snapshot.side_effect = lambda snapshot, model_id, max_tokens: [str(snapshot)] if snapshot else []
    manager.store = MagicMock()
    manager.store.checkpoint.return_value = {
        "generation": 2,
        "last_item_id": 7,
    }
    manager.finish_checkpoint = MagicMock()
    return manager


def test_model_prefers_plan_model_when_available():
    manager = make_manager()
    manager.window.core.models.has.return_value = True
    selected = object()
    manager.window.core.models.get.return_value = selected
    worker = ContextCheckpointWorker(manager, {"model_id": "m"})

    assert worker._model() is selected
    manager.window.core.models.get.assert_called_once_with("m")


def test_model_falls_back_to_default_model():
    manager = make_manager()
    worker = ContextCheckpointWorker(manager, {"model_id": "missing"})

    assert worker._model() is manager.window.core.models.from_defaults.return_value


def test_call_builds_hidden_forced_tool_free_bridge_request(monkeypatch):
    manager = make_manager()
    captured = {}

    class FakeCtx:
        pass

    class FakeBridgeContext:
        def __init__(self, **kwargs):
            captured["bridge"] = kwargs

    class FakeKernelEvent:
        FORCE_CALL = "force-call"

        def __init__(self, event_type, data):
            captured["event_type"] = event_type
            self.data = data

    def dispatch(event):
        captured["event"] = event
        event.data["response"] = " compacted "

    monkeypatch.setattr(checkpoint_module, "CtxItem", FakeCtx)
    monkeypatch.setattr(checkpoint_module, "BridgeContext", FakeBridgeContext)
    monkeypatch.setattr(checkpoint_module, "KernelEvent", FakeKernelEvent)
    manager.window.dispatch = dispatch
    worker = ContextCheckpointWorker(manager, {"model_id": "m"})

    result = worker._call("prompt", 10)

    assert result == "compacted"
    assert captured["event_type"] == "force-call"
    bridge = captured["bridge"]
    assert bridge["prompt"] == "prompt"
    assert bridge["stream"] is False
    assert bridge["force"] is True
    assert bridge["max_tokens"] == 64
    assert bridge["ctx"].internal is True
    assert bridge["ctx"].hidden is True
    assert captured["event"].data["extra"] == {
        "disable_tools": True,
        "advanced_context_checkpoint": True,
        "disable_advanced_context": True,
    }


def test_run_compacts_snapshot_and_saves_checkpoint():
    manager = make_manager()
    plan = {
        "meta_id": 5,
        "existing_notes": "old notes",
        "snapshot": "new conversation",
        "model_id": "m",
        "last_item_id": 7,
        "revision": 3,
        "budget": SimpleNamespace(input_limit=10000, reserve_tokens=2000, effective_limit=12000),
    }
    worker = ContextCheckpointWorker(manager, plan)
    worker._call = MagicMock(return_value="updated notes")

    worker.run()

    manager.store.checkpoint.assert_called_once_with(5, "updated notes", 7, 3)
    manager.finish_checkpoint.assert_called_once_with(5)
    manager.window.core.debug.info.assert_called()


def test_run_uses_deterministic_fallback_when_maintenance_call_returns_empty():
    manager = make_manager()
    plan = {
        "meta_id": 5,
        "existing_notes": "old",
        "snapshot": "new",
        "model_id": "m",
        "last_item_id": 7,
        "revision": 3,
        "budget": SimpleNamespace(input_limit=10000, reserve_tokens=2000, effective_limit=12000),
    }
    worker = ContextCheckpointWorker(manager, plan)
    worker._call = MagicMock(return_value="")

    worker.run()

    saved = manager.store.checkpoint.call_args.args[1]
    assert "old" in saved
    assert "new" in saved
    assert "automatic fallback" in saved
    manager.finish_checkpoint.assert_called_once_with(5)


def test_run_always_releases_pending_marker_after_failure():
    manager = make_manager()
    manager.split_checkpoint_snapshot.side_effect = RuntimeError("boom")
    plan = {
        "meta_id": 9,
        "existing_notes": "",
        "snapshot": "new",
        "model_id": "m",
        "last_item_id": 1,
        "revision": 0,
        "budget": SimpleNamespace(input_limit=10000, reserve_tokens=1000, effective_limit=12000),
    }

    ContextCheckpointWorker(manager, plan).run()

    manager.window.core.debug.log.assert_called()
    manager.finish_checkpoint.assert_called_once_with(9)
