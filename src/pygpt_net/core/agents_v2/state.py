#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkerStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"
    REMOVED = "removed"


@dataclass
class WorkerState:
    id: str
    name: str
    instruction: str
    language: str
    system_prompt: str
    agent: Any
    memory: Any
    tool_ctx: Any
    status: WorkerStatus = WorkerStatus.CREATED
    progress: str = ""
    current_task: str = ""
    last_result: str = ""
    error: str = ""
    task: Optional[asyncio.Task] = None
    stop_requested: bool = False
    generation: int = 0
    artifacts: Dict[str, List[Any]] = field(default_factory=lambda: {
        "files": [], "images": [], "urls": [], "attachments": []
    })

    @property
    def terminal(self) -> bool:
        return self.status in {
            WorkerStatus.COMPLETED,
            WorkerStatus.FAILED,
            WorkerStatus.STOPPED,
            WorkerStatus.REMOVED,
        }

    @property
    def busy(self) -> bool:
        return self.status in {WorkerStatus.RUNNING, WorkerStatus.STOPPING}

    @staticmethod
    def _json_safe(value: Any) -> Any:
        try:
            return json.loads(json.dumps(value, ensure_ascii=False, default=str))
        except Exception:
            return str(value)

    def public_dict(self, include_result: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "status": self.status.value,
            "progress": self.progress,
            "current_task": self.current_task,
            "error": self.error,
            "generation": self.generation,
            "artifacts": {
                key: [self._json_safe(value) for value in values]
                for key, values in self.artifacts.items()
                if values
            },
        }
        if include_result:
            data["result"] = self.last_result
        return data
