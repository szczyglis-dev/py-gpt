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
        create_worker=AsyncMock(),
        start_worker=AsyncMock(),
        remove_worker=AsyncMock(),
        workers={},
        verbose_log=MagicMock(),
        window=SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock()))),
    )
    return runtime


def test_delegate_task_rejects_empty_task_and_cancelled_runtime():
    runtime = make_runtime()
    bridge = AgentDelegateBridge(runtime)

    assert json.loads(asyncio.run(bridge.delegate_task("   "))) == {
        "error": "Delegated task is empty."
    }
    runtime.is_stopped.return_value = True
    assert json.loads(asyncio.run(bridge.delegate_task("work"))) == {
        "error": "Execution cancelled."
    }
    runtime.create_worker.assert_not_awaited()


def test_delegate_task_runs_ephemeral_worker_returns_compact_result_and_cleans_up():
    runtime = make_runtime()
    runtime.create_worker.return_value = json.dumps({"id": "w01"})
    runtime.start_worker.return_value = json.dumps({"id": "w01", "status": "running"})
    state = SimpleNamespace(
        name="Reviewer",
        status=SimpleNamespace(value="completed"),
        last_result="verified answer",
        error="",
        task=None,
        public_dict=lambda: {"artifacts": {"files": ["report.txt"]}},
    )
    runtime.workers["w01"] = state
    bridge = AgentDelegateBridge(runtime)

    payload = json.loads(asyncio.run(bridge.delegate_task(
        " verify ", name=" Reviewer ", instruction="", language=""
    )))

    assert payload == {
        "name": "Reviewer",
        "status": "completed",
        "result": "verified answer",
        "error": "",
        "artifacts": {"files": ["report.txt"]},
    }
    runtime.create_worker.assert_awaited_once_with(
        name="Reviewer",
        instruction="Complete the delegated task as a focused specialist and return a verified work product.",
        language="Use the same language as the current end-user request.",
        system_prompt="",
        task="",
    )
    runtime.start_worker.assert_awaited_once_with("w01", "verify")
    runtime.remove_worker.assert_awaited_once_with("w01")


def test_delegate_task_propagates_worker_start_error_and_still_cleans_up():
    runtime = make_runtime()
    runtime.create_worker.return_value = {"id": "w01"}
    runtime.start_worker.return_value = {"error": "start failed"}
    runtime.workers["w01"] = SimpleNamespace(task=None)
    bridge = AgentDelegateBridge(runtime)

    payload = json.loads(asyncio.run(bridge.delegate_task("work")))

    assert payload == {"error": "start failed"}
    runtime.remove_worker.assert_awaited_once_with("w01")
