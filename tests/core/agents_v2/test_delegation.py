#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pygpt_net.core.agents_v2.delegation import AgentDelegateBridge


def make_runtime():
    runtime = SimpleNamespace(
        is_stopped=MagicMock(return_value=False),
        window=SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock()))),
        workers=SimpleNamespace(states={}, create=AsyncMock(), start=AsyncMock(), remove=AsyncMock()),
        verbose=SimpleNamespace(log=MagicMock()),
    )
    return runtime


def test_delegate_task_rejects_empty_task_and_cancelled_runtime():
    runtime = make_runtime()
    bridge = AgentDelegateBridge(runtime)

    assert json.loads(asyncio.run(bridge.delegate("   "))) == {
        "error": "Delegated task is empty."
    }
    runtime.is_stopped.return_value = True
    assert json.loads(asyncio.run(bridge.delegate("work"))) == {
        "error": "Execution cancelled."
    }
    runtime.workers.create.assert_not_awaited()


def test_delegate_task_runs_ephemeral_worker_returns_compact_result_and_cleans_up():
    runtime = make_runtime()
    runtime.workers.create.return_value = json.dumps({"id": "w01"})
    runtime.workers.start.return_value = json.dumps({"id": "w01", "status": "running"})
    state = SimpleNamespace(
        name="Reviewer",
        status=SimpleNamespace(value="completed"),
        last_result="verified answer",
        error="",
        task=None,
        public_dict=lambda: {"artifacts": {"files": ["report.txt"]}},
    )
    runtime.workers.states["w01"] = state
    bridge = AgentDelegateBridge(runtime)

    payload = json.loads(asyncio.run(bridge.delegate(
        " verify ", name=" Reviewer ", instruction="", language=""
    )))

    assert payload == {
        "name": "Reviewer",
        "status": "completed",
        "result": "verified answer",
        "error": "",
        "artifacts": {"files": ["report.txt"]},
    }
    runtime.workers.create.assert_awaited_once_with(
        name="Reviewer",
        instruction="Complete the delegated task as a focused specialist and return a verified work product.",
        language="Use the same language as the current end-user request.",
        system_prompt="",
        task="",
    )
    runtime.workers.start.assert_awaited_once_with("w01", "verify")
    runtime.workers.remove.assert_awaited_once_with("w01")


def test_delegate_task_propagates_worker_start_error_and_still_cleans_up():
    runtime = make_runtime()
    runtime.workers.create.return_value = {"id": "w01"}
    runtime.workers.start.return_value = {"error": "start failed"}
    runtime.workers.states["w01"] = SimpleNamespace(task=None)
    bridge = AgentDelegateBridge(runtime)

    payload = json.loads(asyncio.run(bridge.delegate("work")))

    assert payload == {"error": "start failed"}
    runtime.workers.remove.assert_awaited_once_with("w01")
