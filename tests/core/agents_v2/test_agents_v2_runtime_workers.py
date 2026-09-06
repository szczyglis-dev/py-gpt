#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime
from pygpt_net.core.agents_v2.state import WorkerState, WorkerStatus


def make_worker(worker_id="w01", status=WorkerStatus.CREATED, generation=0):
    tool_ctx = MagicMock()
    return WorkerState(
        id=worker_id,
        name=f"Worker {worker_id}",
        instruction="instruction",
        language="English",
        system_prompt="",
        agent=SimpleNamespace(llm=None),
        memory=object(),
        tool_ctx=tool_ctx,
        status=status,
        generation=generation,
    )


def make_runtime():
    runtime = AgentsV2Runtime.__new__(AgentsV2Runtime)
    runtime.workers = {}
    runtime.status_events = []
    runtime._status_seq = 0
    runtime.sequence = 0
    runtime.run_id = "run"
    runtime.finished = False
    runtime.final_answer = ""
    runtime.shared_context_text = ""
    runtime.runtime_system_context = ""
    runtime.emitter = MagicMock()
    runtime.emitter.text = ""
    runtime.verbose = MagicMock()
    runtime.verbose_text = MagicMock()
    runtime.window = MagicMock()
    runtime.SHOW_AGENT_NAME_IN_STATUS = False
    return runtime


def test_agents_v2_runtime_create_worker_requires_language_before_building_agent():
    runtime = make_runtime()

    payload = json.loads(asyncio.run(runtime.create_worker("Researcher", "Research", "")))

    assert payload["error"] == "Worker language is required."
    assert runtime.workers == {}


def test_agents_v2_runtime_create_worker_enforces_max_worker_limit():
    runtime = make_runtime()
    runtime.workers = {f"w{i}": make_worker(f"w{i}") for i in range(runtime.MAX_WORKERS)}

    payload = json.loads(asyncio.run(runtime.create_worker("Extra", "Work", "English")))

    assert payload == {"error": f"Maximum workers reached ({runtime.MAX_WORKERS})."}


def test_agents_v2_runtime_update_worker_rejects_running_worker():
    runtime = make_runtime()
    runtime.workers["w01"] = make_worker(status=WorkerStatus.RUNNING)

    payload = json.loads(asyncio.run(runtime.update_worker("w01", name="New")))

    assert payload["error"] == "Worker is running; stop/wait before updating it."


def test_agents_v2_runtime_worker_status_and_list_hide_list_results():
    runtime = make_runtime()
    worker = make_worker(status=WorkerStatus.COMPLETED, generation=1)
    worker.last_result = "secret worker answer"
    runtime.workers[worker.id] = worker

    status = json.loads(asyncio.run(runtime.worker_status(worker.id)))
    listing = json.loads(asyncio.run(runtime.worker_list()))

    assert status["result"] == "secret worker answer"
    assert "result" not in listing[0]


def test_agents_v2_runtime_remove_worker_marks_removed_and_drops_registry_entry():
    runtime = make_runtime()
    worker = make_worker(status=WorkerStatus.COMPLETED, generation=1)
    runtime.workers[worker.id] = worker

    payload = json.loads(asyncio.run(runtime.remove_worker(worker.id)))

    assert payload == {"id": worker.id, "removed": True}
    assert worker.status == WorkerStatus.REMOVED
    assert worker.id not in runtime.workers


def test_agents_v2_runtime_wait_workers_reports_missing_and_recent_selected_statuses():
    runtime = make_runtime()
    worker = make_worker(status=WorkerStatus.COMPLETED, generation=1)
    runtime.workers[worker.id] = worker
    runtime.status_events = [
        {"seq": 1, "agent_id": worker.id, "status": "done"},
        {"seq": 2, "agent_id": "other", "status": "ignore"},
    ]

    payload = json.loads(asyncio.run(runtime.wait_workers("w01,missing", wait_for="all")))

    assert payload["missing"] == ["missing"]
    assert [event["agent_id"] for event in payload["recent_status_events"]] == ["w01"]


def test_agents_v2_runtime_emit_worker_status_bounds_event_history_and_updates_emitter():
    runtime = make_runtime()
    worker = make_worker(status=WorkerStatus.RUNNING)
    runtime.status_events = [
        {"seq": i, "agent_id": "old", "status": str(i)} for i in range(256)
    ]
    runtime._status_seq = 256

    runtime.emit_worker_status(worker, "  processing  ")

    assert worker.progress == "processing"
    assert len(runtime.status_events) == 256
    assert runtime.status_events[-1]["agent_id"] == worker.id
    runtime.emitter.status.assert_called_once_with("processing", source=worker.id)


def test_agents_v2_runtime_finish_workflow_rejects_running_or_unused_workers():
    runtime = make_runtime()
    runtime.workers = {
        "running": make_worker("running", WorkerStatus.RUNNING, generation=1),
        "unused": make_worker("unused", WorkerStatus.CREATED, generation=0),
    }

    payload = json.loads(asyncio.run(runtime.finish_workflow("answer")))

    assert "cannot finish" in payload["error"].lower()
    assert [item["id"] for item in payload["running"]] == ["running"]
    assert [item["id"] for item in payload["never_started"]] == ["unused"]
    assert runtime.finished is False


def test_agents_v2_runtime_finish_workflow_requires_non_empty_final_answer():
    runtime = make_runtime()

    payload = json.loads(asyncio.run(runtime.finish_workflow("   ")))

    assert payload["error"] == "final_answer is empty."
    assert runtime.finished is False


def test_agents_v2_runtime_finish_workflow_appends_final_answer_once_and_marks_finished():
    runtime = make_runtime()
    runtime.emitter.text = "intermediate text"

    result = asyncio.run(runtime.finish_workflow(" final answer "))

    assert result.startswith("Workflow marked as finished")
    assert runtime.finished is True
    assert runtime.final_answer == "final answer"
    runtime.emitter.clear_status.assert_called_once()
    runtime.emitter.mark_block_boundary.assert_called_once()
    runtime.emitter.append.assert_called_once_with("final answer")


def test_agents_v2_runtime_cleanup_cancels_pending_tasks_and_clears_workers():
    runtime = make_runtime()

    async def scenario():
        task = asyncio.create_task(asyncio.sleep(60))
        worker = make_worker(status=WorkerStatus.RUNNING, generation=1)
        worker.task = task
        runtime.workers[worker.id] = worker
        await runtime.cleanup()
        return task, worker

    task, worker = asyncio.run(scenario())

    assert task.cancelled() is True
    assert worker.stop_requested is True
    assert runtime.workers == {}
