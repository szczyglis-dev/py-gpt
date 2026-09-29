#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime
from pygpt_net.core.agents_v2.mode import AgentMode
from pygpt_net.core.agents_v2.state import WorkerState, WorkerStatus
from pygpt_net.core.agents_v2.status import RuntimeStatus
from pygpt_net.core.agents_v2.strategy import get_agent_strategy
from pygpt_net.core.agents_v2.workers import WorkerRuntime


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
    runtime.agent_mode = AgentMode.ORCHESTRATOR
    runtime.strategy = get_agent_strategy(runtime.agent_mode)
    runtime.workers = {}
    runtime.status_events = []
    runtime._status_seq = 0
    runtime.sequence = 0
    runtime.run_id = "run"
    runtime.finished = False
    runtime.final_answer = ""
    runtime.workflow_final_requested = False
    runtime.workflow_final_stream_started = False
    runtime.workflow_final_hint = ""
    runtime.shared_context_text = ""
    runtime.runtime_system_context = ""
    runtime.emitter = MagicMock()
    runtime.emitter.text = ""
    runtime.emitter.stream_final = AsyncMock()
    runtime.verbose = MagicMock()
    runtime.verbose_text = MagicMock()
    runtime.window = MagicMock()
    runtime.window.controller.kernel.stopped.return_value = False
    runtime.window.core.config.get.side_effect = lambda key, default=None: default
    runtime._worker_parent_parts = {}
    runtime._stored_worker_context_runs = set()
    runtime._swarm_worker_numbers = {}
    runtime._swarm_reporter_task = None
    runtime.swarm_created_workers = 0
    runtime.SHOW_AGENT_NAME_IN_STATUS = False
    runtime.status_api = RuntimeStatus(runtime)
    runtime.worker_api = WorkerRuntime(runtime)
    return runtime


def test_agents_v2_runtime_create_worker_requires_language_before_building_agent():
    runtime = make_runtime()

    payload = json.loads(asyncio.run(runtime.create_worker("Researcher", "Research", "")))

    assert payload["error"] == "Worker language is required."
    assert runtime.workers == {}


def test_agents_v2_runtime_create_worker_enforces_max_worker_limit():
    runtime = make_runtime()
    limit = runtime.MAX_WORKERS_DEFAULT
    runtime.window.core.config.get.side_effect = lambda key, default=None: (
        limit if key == "agent.v2.max_workers" else default
    )
    runtime.workers = {f"w{i}": make_worker(f"w{i}") for i in range(limit)}

    payload = json.loads(asyncio.run(runtime.create_worker("Extra", "Work", "English")))

    assert payload == {"error": f"Maximum workers reached ({limit})."}


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
    runtime.emitter.status.assert_called_once_with("[Worker w01] processing", source=worker.id)


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


def test_agents_v2_runtime_request_workflow_finish_accepts_empty_payload_and_arms_final_response():
    runtime = make_runtime()

    result = asyncio.run(runtime.request_workflow_finish())

    assert result.startswith("Finalization accepted.")
    assert runtime.workflow_final_requested is True
    assert runtime.workflow_final_stream_started is False
    assert runtime.workflow_final_hint == ""
    assert runtime.finished is False
    assert runtime.final_answer == ""
    runtime.emitter.clear_status.assert_called_once_with()
    runtime.emitter.stream_final.assert_not_awaited()


def test_agents_v2_runtime_finish_workflow_keeps_legacy_hint_without_materializing_final_output():
    runtime = make_runtime()

    result = asyncio.run(runtime.finish_workflow(" final answer "))

    assert result.startswith("Finalization accepted.")
    assert runtime.workflow_final_requested is True
    assert runtime.workflow_final_stream_started is False
    assert runtime.workflow_final_hint == "final answer"
    assert runtime.finished is False
    assert runtime.final_answer == ""
    runtime.emitter.clear_status.assert_called_once_with()
    runtime.emitter.stream_final.assert_not_awaited()


def test_agents_v2_runtime_finish_workflow_rejects_second_finalization_request():
    runtime = make_runtime()
    runtime.workflow_final_requested = True

    payload = json.loads(asyncio.run(runtime.finish_workflow("ignored")))

    assert payload["error"] == "Workflow finalization is already accepted."
    assert runtime.workflow_final_hint == ""
    runtime.emitter.clear_status.assert_not_called()


def test_agents_v2_runtime_begin_workflow_final_stream_prepares_final_part_once():
    runtime = make_runtime()
    runtime.workflow_final_requested = True
    runtime.emitter.begin_final_stream = MagicMock()
    final_part = SimpleNamespace(uuid="final-part")
    runtime._prepare_final_part = MagicMock(return_value=final_part)
    runtime._actor_part = MagicMock(return_value=final_part)

    first = runtime.begin_workflow_final_stream()
    second = runtime.begin_workflow_final_stream()

    assert first is final_part
    assert second is final_part
    assert runtime.workflow_final_stream_started is True
    runtime._prepare_final_part.assert_called_once_with()
    runtime.emitter.begin_final_stream.assert_called_once_with()


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


def test_blocked_swarm_can_finish_without_launching_missing_workers():
    runtime = make_runtime()
    runtime.agent_mode = AgentMode.SWARM
    runtime.strategy = get_agent_strategy(runtime.agent_mode)
    result = asyncio.run(runtime.request_workflow_finish(outcome="needs_input", evidence="Missing task attachment"))
    assert "accepted" in result.lower()
    assert runtime.workflow_final_requested
    assert runtime.workflow_outcome == "needs_input"


def test_blocked_workflow_requires_evidence_and_stops_active_workers():
    async def scenario():
        runtime = make_runtime()
        worker = make_worker(status=WorkerStatus.RUNNING)
        worker.task = asyncio.create_task(asyncio.sleep(60))
        runtime.workers[worker.id] = worker
        result = await runtime.request_workflow_finish(outcome="blocked")
        assert "error" in json.loads(result)
        assert not runtime.workflow_final_requested
        await runtime.request_workflow_finish(outcome="blocked", evidence="Required tool unavailable")
        assert worker.task.done()
        assert worker.status == WorkerStatus.STOPPED
        assert runtime.workflow_final_requested
    asyncio.run(scenario())


def test_stop_rejects_new_work():
    runtime = make_runtime()
    runtime.window.controller.kernel.stopped.return_value = True
    result = asyncio.run(runtime.create_worker("Worker", "Inspect", "English"))
    assert "error" in json.loads(result)
    assert not runtime.workers
