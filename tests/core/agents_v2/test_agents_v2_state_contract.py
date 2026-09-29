#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace

import pytest

from pygpt_net.core.agents_v2.state import WorkerState, WorkerStatus


def make_state(status=WorkerStatus.CREATED):
    return WorkerState(
        id="w01",
        name="Worker 1",
        instruction="Do work",
        language="en",
        system_prompt="system",
        agent=object(),
        memory=object(),
        tool_ctx=object(),
        status=status,
    )


@pytest.mark.parametrize(
    "status, terminal, busy",
    [
        (WorkerStatus.CREATED, False, False),
        (WorkerStatus.RUNNING, False, True),
        (WorkerStatus.STOPPING, False, True),
        (WorkerStatus.COMPLETED, True, False),
        (WorkerStatus.FAILED, True, False),
        (WorkerStatus.STOPPED, True, False),
        (WorkerStatus.REMOVED, True, False),
    ],
)
def test_agents_v2_worker_status_flags(status, terminal, busy):
    state = make_state(status)
    assert state.terminal is terminal
    assert state.busy is busy


def test_agents_v2_worker_public_dict_filters_empty_artifacts_and_result():
    state = make_state(WorkerStatus.COMPLETED)
    state.progress = "done"
    state.current_task = "task"
    state.last_result = "answer"
    state.generation = 3
    state.artifacts["files"].append({"path": "/tmp/a.txt"})

    data = state.public_dict(include_result=False)

    assert data == {
        "id": "w01",
        "name": "Worker 1",
        "language": "en",
        "status": "completed",
        "progress": "done",
        "current_task": "task",
        "error": "",
        "generation": 3,
        "artifacts": {"files": [{"path": "/tmp/a.txt"}]},
    }


def test_agents_v2_worker_public_dict_makes_artifacts_json_safe():
    state = make_state()
    marker = SimpleNamespace(value=7)
    state.artifacts["attachments"].append(marker)

    data = state.public_dict()

    assert data["result"] == ""
    assert data["artifacts"]["attachments"] == [str(marker)]
