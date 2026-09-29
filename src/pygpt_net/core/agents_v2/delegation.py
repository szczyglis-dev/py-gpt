#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 09:30:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional


class AgentDelegateBridge:
    """Reusable agent-as-tool bridge.

    The bridge deliberately exposes a *single* high-level operation to callers:
    ``delegate_task``.  Worker lifecycle stays behind this boundary.  A host
    runtime only needs to provide the small worker-runtime contract used below
    (``create_worker``, ``start_worker``, ``remove_worker``, ``workers`` and
    ``is_stopped``), which makes the same bridge reusable later from e.g. an
    "agents as tool" plugin without exposing worker-management tools to an LLM.

    One call creates an ephemeral specialist, runs exactly one delegated task,
    waits for completion and always cleans the worker up before returning.
    Progress/status events remain the responsibility of the host runtime and are
    therefore delivered through the same UI path as today.
    """

    def __init__(self, runtime):
        self.runtime = runtime

    @staticmethod
    def _json(payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def delegate_task(
            self,
            task: str,
            name: str = "Specialist",
            instruction: str = "",
            system_prompt: str = "",
            language: str = "",
    ) -> str:
        """Run one ephemeral specialist and return its compact work product."""
        task = str(task or "").strip()
        if not task:
            return self._json({"error": "Delegated task is empty."})
        if self.runtime.is_stopped():
            return self._json({"error": "Execution cancelled."})

        name = str(name or "Specialist").strip()[:80] or "Specialist"
        instruction = str(instruction or "").strip()
        if not instruction:
            instruction = "Complete the delegated task as a focused specialist and return a verified work product."
        language = str(language or "").strip()
        if not language:
            # Avoid forcing the Primary Agent to manage a language parameter on
            # every delegation.  The concrete task is also supplied verbatim to
            # the specialist, so this contract remains robust for multilingual
            # prompts while keeping the tool surface compact.
            language = "Use the same language as the current end-user request."

        worker_id: Optional[str] = None
        state = None
        self.runtime.verbose_log("DELEGATE TASK REQUEST", {
            "name": name,
            "instruction": instruction,
            "language": language,
            "system_prompt": system_prompt,
            "task": task,
        })
        try:
            created_raw = await self.runtime.create_worker(
                name=name,
                instruction=instruction,
                language=language,
                system_prompt=str(system_prompt or ""),
                task="",
            )
            try:
                created = json.loads(created_raw) if isinstance(created_raw, str) else created_raw
            except Exception:
                created = {"error": str(created_raw)}
            if not isinstance(created, dict) or created.get("error"):
                return self._json(created if isinstance(created, dict) else {"error": str(created)})

            worker_id = str(created.get("id") or "").strip()
            if not worker_id:
                return self._json({"error": "Worker runtime did not return an agent id."})

            started_raw = await self.runtime.start_worker(worker_id, task)
            try:
                started = json.loads(started_raw) if isinstance(started_raw, str) else started_raw
            except Exception:
                started = {"error": str(started_raw)}
            if isinstance(started, dict) and started.get("error"):
                return self._json(started)

            state = self.runtime.workers.get(worker_id)
            if state is None:
                return self._json({"error": "Worker disappeared before execution started."})

            if state.task is not None:
                # The worker coroutine converts normal cancellation/failure into
                # WorkerState.  gather(return_exceptions=True) additionally keeps
                # parent cancellation/error handling from leaking worker internals
                # into the Primary Agent's tool protocol.
                await asyncio.gather(state.task, return_exceptions=True)

            payload = {
                "name": state.name,
                "status": getattr(state.status, "value", str(state.status)),
                "result": str(state.last_result or ""),
                "error": str(state.error or ""),
                "artifacts": state.public_dict().get("artifacts", {}),
            }
            self.runtime.verbose_log("DELEGATE TASK RESULT", payload, actor=worker_id)
            return self._json(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.runtime.verbose_log("DELEGATE TASK ERROR", {"error": str(exc)}, actor=worker_id or "orchestrator")
            try:
                self.runtime.window.core.debug.log(exc)
            except Exception:
                pass
            return self._json({"error": str(exc)})
        finally:
            if worker_id and worker_id in self.runtime.workers:
                try:
                    await self.runtime.remove_worker(worker_id)
                except asyncio.CancelledError:
                    # Cancellation should still make a best-effort cleanup.  The
                    # outer runtime cleanup is the final safety net.
                    try:
                        state = self.runtime.workers.get(worker_id)
                        if state is not None and state.task is not None and not state.task.done():
                            state.stop_requested = True
                            state.task.cancel()
                    except Exception:
                        pass
                    raise
                except Exception as exc:
                    try:
                        self.runtime.window.core.debug.log(exc)
                    except Exception:
                        pass
