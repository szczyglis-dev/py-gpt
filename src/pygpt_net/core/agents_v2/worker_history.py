"""Persist worker output onto the main agent part that launched the task."""

import time
from .state import WorkerState
from .utils import legacy_worker_context_record


class WorkerHistory:
    def __init__(self, runtime):
        self.runtime = runtime

    def save(self, state: WorkerState):
        """Persist one worker final as orchestrator-only restore context.

        Workers keep their private LlamaIndex Memory in RAM.  What must survive a
        reload is only what the Primary Agent learned from a specialist during this
        turn.  Store that compact payload on the orchestrator partial which
        launched the run; when history is rebuilt it is inserted immediately
        after that partial's prose and before the following partial.
        """
        part = self.runtime.workers.parent_parts.get(state.id)
        main = getattr(self.runtime.context, "ctx", None)
        if part is None or main is None or part not in (main.parts or []):
            return
        run_key = (str(state.id or ""), int(state.generation or 0))
        if run_key in self.runtime.workers.stored_context_runs:
            return
        if not isinstance(part.extra, dict):
            part.extra = {}

        values = part.extra.get("worker_context")
        if not isinstance(values, list):
            values = []
            # Best-effort in-place migration for runs saved by the immediately
            # preceding implementation.  New writes use only worker_context.
            legacy = part.extra.pop("worker_outputs", None)
            if isinstance(legacy, list):
                for item in legacy:
                    converted = legacy_worker_context_record(item)
                    if converted is not None:
                        values.append(converted)
            part.extra["worker_context"] = values

        record = {
            "id": str(state.id or ""),
            "name": str(state.name or ""),
            "input": str(state.current_task or ""),
            "output": str(state.last_result or ""),
            "created_at": int(time.time() * 1000),
        }
        values.append(record)
        values.sort(key=lambda item: int(item.get("created_at") or 0) if isinstance(item, dict) else 0)
        self.runtime.window.core.ctx.update_part(main, part, sync_item=False)
        self.runtime.workers.stored_context_runs.add(run_key)

