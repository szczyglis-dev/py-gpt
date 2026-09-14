#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from llama_index.core.agent.workflow import AgentStream
from llama_index.core.memory import Memory

from .state import WorkerState, WorkerStatus
from .utils import legacy_worker_context_record, result_text


class WorkerRuntime:
    """Worker lifecycle and delegation runtime shared by all top-level modes."""

    def __init__(self, runtime):
        self.runtime = runtime

    def _worker_prompt(self, name: str, instruction: str, language: str, system_prompt: str) -> str:
        bridge_prompt = str(self.runtime.bridge_system_prompt or "").strip()
        runtime_context = str(self.runtime.runtime_system_context or "").strip()
        # Files I/O historically published a separate Agents-v2 runtime context.
        # Keep that fallback for compatibility, but do not duplicate it now that
        # the final Bridge system prompt is consumed directly.
        runtime_block = ""
        if runtime_context and runtime_context not in bridge_prompt:
            runtime_block = f"<runtime_environment>\n{runtime_context}\n</runtime_environment>"
        worker_base_prompt = self.runtime.strategy.worker_prompt
        controller_tag = self.runtime.strategy.worker_controller_tag
        return "\n\n".join(filter(None, [
            worker_base_prompt,
            f"<workflow_language>\n{language}\n</workflow_language>",
            f"<worker_identity>\nname={name}\nrole_instruction={instruction}\n</worker_identity>",
            (
                f"<additional_system_prompt>\n{bridge_prompt}\n</additional_system_prompt>"
                if bridge_prompt else ""
            ),
            runtime_block,
            self.runtime._rag_prompt_context(),
            (
                f"<{controller_tag}>\n{system_prompt}\n</{controller_tag}>"
                if system_prompt else ""
            ),
        ])).strip()

    async def create_worker(
            self,
            name: str,
            instruction: str,
            language: str,
            system_prompt: str = "",
            task: str = "",
    ) -> str:
        self.runtime.verbose.log("AGENT CREATE REQUEST", {
            "name": name,
            "instruction": instruction,
            "language": language,
            "system_prompt": system_prompt,
            "task": task,
        })
        if self.runtime.is_swarm_mode:
            if self.runtime.swarm_expected_workers is None:
                result = json.dumps({
                    "error": "Swarm size is not declared.",
                    "action": "Call swarm_start(agent_count=N) before creating workers.",
                }, ensure_ascii=False)
                self.runtime.verbose.log("AGENT CREATE REJECTED", result)
                return result
            if self.runtime.swarm_created_workers >= self.runtime.swarm_expected_workers:
                result = json.dumps({
                    "error": "Declared swarm size has already been reached.",
                    "declared": self.runtime.swarm_expected_workers,
                    "created": self.runtime.swarm_created_workers,
                }, ensure_ascii=False)
                self.runtime.verbose.log("AGENT CREATE REJECTED", result)
                return result
        else:
            max_workers = self.runtime.max_workers_configured
            if max_workers > 0 and len(self.runtime.workers) >= max_workers:
                result = json.dumps({"error": f"Maximum workers reached ({max_workers})."})
                self.runtime.verbose.log("AGENT CREATE REJECTED", result)
                return result
        raw_name = (name or "Worker").strip()[:80]
        instruction = (instruction or "General specialist").strip()
        language = str(language or "").strip()
        if not language:
            return json.dumps({
                "error": "Worker language is required.",
                "action": "Pass the language of the current end-user request (for example: Polish, English, German).",
            }, ensure_ascii=False)
        wid = self.runtime._worker_id()
        swarm_number = self.runtime.swarm_created_workers + 1 if self.runtime.is_swarm_mode else 0
        name = self.runtime._swarm_worker_name(raw_name, swarm_number) if self.runtime.is_swarm_mode else raw_name
        state = WorkerState(
            id=wid,
            name=name,
            instruction=instruction,
            language=language[:80],
            system_prompt=system_prompt or "",
            agent=None,
            memory=None,
            tool_ctx=self.runtime._make_worker_ctx(wid),
        )
        llm = self.runtime.get_llm(stream=False, actor_id=wid)
        worker_prompt = self.runtime._worker_prompt(
            name, instruction, state.language, system_prompt or ""
        )
        worker_tools = self.runtime.tool_factory.build(state)
        if self.runtime.window.core.context_manager.enabled():
            state.memory = self.runtime.window.core.context_manager.build_agent_memory(
                self.runtime,
                actor_id=wid,
                system_prompt=worker_prompt,
                tools=worker_tools,
                persistent=False,
            )
        else:
            state.memory = Memory.from_defaults(
                session_id=f"agents_v2_{self.runtime.run_id}_{wid}",
                token_limit=self.runtime._memory_token_limit(),
            )
        state.agent = self.runtime.build_agent(
            name=name,
            description=instruction[:512],
            llm=llm,
            system_prompt=worker_prompt,
            tools=worker_tools,
        )
        self.runtime.workers[wid] = state
        if self.runtime.is_swarm_mode:
            self.runtime._swarm_worker_numbers[wid] = swarm_number
            self.runtime.swarm_created_workers += 1
            self.runtime._emit_swarm_status(force=self.runtime.swarm_created_workers == self.runtime.swarm_expected_workers)
        self.runtime.verbose.log("AGENT CREATED", state.public_dict(), actor=wid)
        if task:
            await self.runtime.start_worker(wid, task)
        result = json.dumps(state.public_dict(), ensure_ascii=False, default=str)
        self.runtime.verbose.log("AGENT CREATE RESULT", state.public_dict(), actor=wid)
        return result

    async def update_worker(
            self,
            agent_id: str,
            name: Optional[str] = None,
            instruction: Optional[str] = None,
            language: Optional[str] = None,
            system_prompt: Optional[str] = None,
    ) -> str:
        self.runtime.verbose.log("AGENT UPDATE REQUEST", {
            "agent_id": agent_id,
            "name": name,
            "instruction": instruction,
            "language": language,
            "system_prompt": system_prompt,
        }, actor=agent_id)
        state = self.runtime.workers.get(agent_id)
        if state is None or state.status == WorkerStatus.REMOVED:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            return json.dumps({"error": "Worker is running; stop/wait before updating it.", "id": agent_id})
        if name is not None and name.strip():
            requested_name = name.strip()[:80]
            if self.runtime.is_swarm_mode:
                state.name = self.runtime._swarm_worker_name(
                    requested_name,
                    self.runtime._swarm_worker_number(state.id),
                )
            else:
                state.name = requested_name
        if instruction is not None and instruction.strip():
            state.instruction = instruction.strip()
        if language is not None and language.strip():
            state.language = language.strip()[:80]
        if system_prompt is not None:
            state.system_prompt = system_prompt.strip()

        # Rebuild the agent definition while deliberately preserving Memory.
        llm = self.runtime.get_llm(stream=False, actor_id=state.id)
        state.agent = self.runtime.build_agent(
            name=state.name,
            description=state.instruction[:512],
            llm=llm,
            system_prompt=self.runtime._worker_prompt(state.name, state.instruction, state.language, state.system_prompt),
            tools=self.runtime.tool_factory.build(state),
        )
        state.status = WorkerStatus.CREATED
        state.progress = ""
        state.error = ""
        result = state.public_dict()
        self.runtime.verbose.log("AGENT UPDATED", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def start_worker(self, agent_id: str, task: str) -> str:
        self.runtime.verbose.log("AGENT RUN REQUEST", {"agent_id": agent_id, "task": task}, actor=agent_id)
        state = self.runtime.workers.get(agent_id)
        if state is None or state.status == WorkerStatus.REMOVED:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            return json.dumps({"error": "Worker is already running", "id": agent_id})
        state.current_task = str(task or "").strip()
        if not state.current_task:
            return json.dumps({"error": "Task is empty", "id": agent_id})
        state.stop_requested = False
        state.status = WorkerStatus.RUNNING
        state.progress = ""
        # Keep the worker-local tool context aligned with the current assignment.
        # Some PyGPT plugins inspect ctx.input/output even when invoked as tools.
        state.tool_ctx.set_input(state.current_task, "orchestrator")
        state.tool_ctx.set_output("", state.name)
        state.error = ""
        state.last_result = ""
        if self.runtime.is_swarm_mode and state.generation == 0:
            self.runtime.swarm_launched_workers += 1
        state.generation += 1
        # Worker conversation state remains in-memory only. Remember the current
        # orchestrator partial as the durable origin for this run; worker tool
        # task rows and the final worker_context record are attached there.
        self.runtime._worker_parent_parts[state.id] = self.runtime._actor_part("orchestrator", create=True)
        self.runtime.emit_runtime_status("status.agent_v2.starting", worker=state)
        if self.runtime.is_swarm_mode:
            self.runtime._ensure_swarm_reporter()
            self.runtime._emit_swarm_status(force=False)
        self.runtime.verbose.log("AGENT RUNNING", state.public_dict(include_result=False), actor=agent_id)
        state.task = asyncio.create_task(
            self.runtime._worker_loop(state, state.current_task),
            name=f"agents-v2:{agent_id}",
        )
        result = state.public_dict(include_result=False)
        self.runtime.verbose.log("AGENT RUN RESULT", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def _worker_loop(self, state: WorkerState, task: str):
        handler = None
        event_count = 0
        event_types = {}
        try:
            shared_hint = ""
            if self.runtime.shared_context_text:
                shared_hint = (
                    "\n\nThis workflow has shared user attachments/context. Use shared_context for extracted text/manifest; "
                    "image inputs from the current turn are also attached to this task when the selected model supports them."
                )
            worker_input = self.runtime.build_user_message(f"Task from {self.runtime.main_agent_name}:\n{task}{shared_hint}")
            self.runtime.verbose.log("WORKER INPUT", worker_input, actor=state.id)
            run_kwargs = {
                "user_msg": worker_input,
                "memory": state.memory,
                "max_iterations": self.runtime.worker_max_iterations,
                "early_stopping_method": "generate",
            }
            self.runtime.window.core.api.logger.log_input(
                type="llama_index.agent.run",
                provider=str(getattr(self.runtime.model, "provider", "") or ""),
                kwargs=run_kwargs,
                input=worker_input,
                model=getattr(self.runtime.model, "id", None),
                path="worker_agent.run",
                extra={"actor": state.id, "worker_name": state.name},
            )
            handler = state.agent.run(**run_kwargs)
            async for event in handler.stream_events():
                event_count += 1
                event_name = type(event).__name__
                event_types[event_name] = event_types.get(event_name, 0) + 1
                self.runtime.verbose_event(event, actor=state.id)
                if self.runtime.is_stopped() or state.stop_requested:
                    state.status = WorkerStatus.STOPPING
                    try:
                        await handler.cancel_run()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                    raise asyncio.CancelledError()
                # Worker answer text is private. Progress reaches the UI through report_status.
                if isinstance(event, AgentStream):
                    continue
            result = await handler
            self.runtime.collect_llm_artifacts(
                getattr(state.agent, "llm", None),
                state,
                response=result,
                actor_id=state.id,
            )
            state.last_result = result_text(result)
            self.runtime.verbose_text("WORKER OUTPUT", state.last_result, actor=state.id)
            state.status = WorkerStatus.COMPLETED
            self.runtime.emit_runtime_status("status.agent_v2.completed", worker=state)
            self.runtime.collect_artifacts(state.tool_ctx, state)
            return state.last_result
        except asyncio.CancelledError:
            if handler is not None:
                try:
                    await handler.cancel_run()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            state.status = WorkerStatus.STOPPED
            self.runtime.verbose.log("WORKER CANCELLED", state.public_dict(), actor=state.id)
            self.runtime.emit_runtime_status("status.agent_v2.stopped", worker=state)
            return ""
        except Exception as exc:
            state.status = WorkerStatus.FAILED
            state.error = str(exc)
            self.runtime.verbose.log("WORKER ERROR", {"error": str(exc), "state": state.public_dict()}, actor=state.id)
            self.runtime.emit_runtime_status("status.agent_v2.failed", worker=state)
            self.runtime.window.core.debug.log(exc)
            return ""
        finally:
            self.runtime.window.core.api.logger.log_output(
                type="llama_index.agent.run",
                provider=str(getattr(self.runtime.model, "provider", "") or ""),
                output=state.last_result,
                chunks=event_count,
                chunk_types=event_types,
                error=state.error or None,
                model=getattr(self.runtime.model, "id", None),
                extra={"actor": state.id, "worker_name": state.name, "status": state.status.value},
            )
            self.runtime.collect_llm_artifacts(getattr(state.agent, "llm", None), state)
            self.runtime.collect_artifacts(state.tool_ctx, state)
            self.runtime._store_worker_output(state)

    def _store_worker_output(self, state: WorkerState):
        """Persist one worker final as orchestrator-only restore context.

        Workers keep their private LlamaIndex Memory in RAM.  What must survive a
        reload is only what the Primary Agent learned from a specialist during this
        turn.  Store that compact payload on the orchestrator partial which
        launched the run; when history is rebuilt it is inserted immediately
        after that partial's prose and before the following partial.
        """
        part = self.runtime._worker_parent_parts.get(state.id)
        main = getattr(self.runtime.context, "ctx", None)
        if part is None or main is None or part not in (main.parts or []):
            return
        run_key = (str(state.id or ""), int(state.generation or 0))
        if run_key in self.runtime._stored_worker_context_runs:
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
        self.runtime._stored_worker_context_runs.add(run_key)

    async def stop_worker(self, agent_id: str) -> str:
        self.runtime.verbose.log("AGENT STOP REQUEST", {"agent_id": agent_id}, actor=agent_id)
        state = self.runtime.workers.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        state.stop_requested = True
        if state.task and not state.task.done():
            state.status = WorkerStatus.STOPPING
            state.task.cancel()
            await asyncio.gather(state.task, return_exceptions=True)
        if state.status != WorkerStatus.REMOVED:
            state.status = WorkerStatus.STOPPED
        result = state.public_dict()
        self.runtime.verbose.log("AGENT STOPPED", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def remove_worker(self, agent_id: str) -> str:
        self.runtime.verbose.log("AGENT REMOVE REQUEST", {"agent_id": agent_id}, actor=agent_id)
        state = self.runtime.workers.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            await self.runtime.stop_worker(agent_id)
        if self.runtime.is_swarm_mode and state.generation == 0 and self.runtime.swarm_created_workers > 0:
            # An unlaunched slot can be replaced while still honoring the exact
            # user-requested swarm size. Launched agents always count permanently.
            self.runtime.swarm_created_workers -= 1
        state.status = WorkerStatus.REMOVED
        self.runtime.workers.pop(agent_id, None)
        self.runtime._swarm_worker_numbers.pop(agent_id, None)
        self.runtime._worker_parent_parts.pop(agent_id, None)
        result = {"id": agent_id, "removed": True}
        self.runtime.verbose.log("AGENT REMOVED", result, actor=agent_id)
        return json.dumps(result)

    async def worker_status(self, agent_id: str) -> str:
        state = self.runtime.workers.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        result = state.public_dict()
        self.runtime.verbose.log("AGENT STATUS", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def worker_list(self) -> str:
        result = [w.public_dict(include_result=False) for w in self.runtime.workers.values()]
        self.runtime.verbose.log("AGENT LIST", result)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def wait_workers(self, agent_ids: str = "", wait_for: str = "all", timeout_seconds: int = 60) -> str:
        self.runtime.verbose.log("AGENT WAIT REQUEST", {
            "agent_ids": agent_ids,
            "wait_for": wait_for,
            "timeout_seconds": timeout_seconds,
        })
        ids = [x.strip() for x in str(agent_ids or "").split(",") if x.strip()]
        if not ids:
            ids = list(self.runtime.workers.keys())
        states = [self.runtime.workers[i] for i in ids if i in self.runtime.workers]
        missing = [i for i in ids if i not in self.runtime.workers]
        if not states:
            return json.dumps({"error": "No matching workers", "missing": missing})

        tasks = [s.task for s in states if s.task is not None and not s.task.done()]
        mode = str(wait_for or "all").lower()
        if mode not in ("all", "any"):
            mode = "all"
        if tasks:
            waiting_names = ", ".join(s.name for s in states if s.task is not None and not s.task.done())
            self.runtime.emit_runtime_status("status.agent_v2.waiting", name=waiting_names)
            timeout = max(1, min(int(timeout_seconds or 60), 600))
            try:
                await asyncio.wait(
                    tasks,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED if mode == "any" else asyncio.ALL_COMPLETED,
                )
            except Exception as exc:
                self.runtime.window.core.debug.log(exc)
        selected_ids = {s.id for s in states}
        payload = {
            "workers": [s.public_dict() for s in states],
            "missing": missing,
            "recent_status_events": [
                event for event in self.runtime.status_events if event.get("agent_id") in selected_ids
            ][-64:],
        }
        self.runtime.verbose.log("AGENT WAIT RESULT", payload)
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def set_status(self, status: str) -> str:
        value = str(status or "").strip()
        self.runtime.verbose.log("WORKFLOW STATUS", {"status": value})
        self.runtime.emitter.status(value, source="orchestrator")
        return "Status updated."

    async def finish_workflow(self, final_answer: str = "") -> str:
        """Legacy compatibility finalizer; not exposed to the Primary Agent."""
        self.runtime.verbose_text("WORKFLOW FINISH REQUEST", final_answer)
        if self.runtime.finished:
            self.runtime.verbose.log("WORKFLOW FINISH REJECTED", "Workflow is already finished.")
            return "Workflow is already finished."
        if self.runtime.workflow_final_requested:
            payload = {
                "error": "Workflow finalization is already accepted.",
                "action": "Return the complete final answer now as normal assistant text without calling any more tools.",
            }
            self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
            return json.dumps(payload, ensure_ascii=False)

        if self.runtime.is_swarm_mode:
            if self.runtime.swarm_expected_workers is None:
                payload = {
                    "error": "Swarm workflow cannot finish before its size is declared.",
                    "action": "Call swarm_start(agent_count=N), launch exactly N workers, then finish the workflow.",
                }
                self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
                return json.dumps(payload, ensure_ascii=False)
            if self.runtime.swarm_created_workers != self.runtime.swarm_expected_workers:
                payload = {
                    "error": "Swarm workflow cannot finish before the declared number of workers has been launched.",
                    "declared": self.runtime.swarm_expected_workers,
                    "created": self.runtime.swarm_created_workers,
                    "remaining": max(0, self.runtime.swarm_expected_workers - self.runtime.swarm_created_workers),
                    "action": "Create/start the remaining workers before calling workflow_finish again.",
                }
                self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
                return json.dumps(payload, ensure_ascii=False)
            if self.runtime.swarm_launched_workers != self.runtime.swarm_expected_workers:
                payload = {
                    "error": "Swarm workflow cannot finish before every declared worker has actually been started.",
                    "declared": self.runtime.swarm_expected_workers,
                    "launched": self.runtime.swarm_launched_workers,
                    "remaining": max(0, self.runtime.swarm_expected_workers - self.runtime.swarm_launched_workers),
                    "action": "Start the remaining created workers before calling workflow_finish again.",
                }
                self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
                return json.dumps(payload, ensure_ascii=False)

        running = [w for w in self.runtime.workers.values() if w.busy]
        never_started = [
            w for w in self.runtime.workers.values()
            if w.status == WorkerStatus.CREATED and w.generation == 0
        ]
        if running or never_started:
            payload = {
                "error": "Workflow cannot finish while workers are still running or were created but never started.",
                "running": [w.public_dict(include_result=False) for w in running],
                "never_started": [w.public_dict(include_result=False) for w in never_started],
                "action": "Wait for/stop running workers and run or remove unused workers, then call workflow_finish again.",
            }
            self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
            return json.dumps(payload, ensure_ascii=False, default=str)

        # Do not finalize from a tool argument. A function/tool call is only
        # dispatched after its complete JSON payload has been generated, which
        # necessarily turns a long final_answer argument into a non-streamed wait.
        # Instead this tool only validates/arms finalization; the next ordinary
        # assistant pass is the authoritative answer and arrives as native
        # AgentStream deltas. Keep an optional legacy hint so older/custom prompts
        # that still pass final_answer can recover if the final pass is empty.
        self.runtime.workflow_final_requested = True
        self.runtime.workflow_final_stream_started = False
        self.runtime.workflow_final_hint = str(final_answer or "").strip()
        self.runtime.verbose.log("WORKFLOW FINAL RESPONSE ARMED", {
            "legacy_hint_chars": len(self.runtime.workflow_final_hint),
        })
        self.runtime.emitter.clear_status()
        return (
            "Finalization accepted. Return the complete user-facing final answer now as normal assistant text. "
            "Do not call workflow_finish again and do not call any other tool."
        )

    async def start_swarm(self, agent_count: int) -> str:
        """Declare the exact user-requested Swarm size before worker creation."""
        if not self.runtime.is_swarm_mode:
            return json.dumps({"error": "swarm_start is available only in Swarm mode."})
        try:
            count = int(agent_count)
        except (TypeError, ValueError):
            count = 0
        if count < 1:
            return json.dumps({
                "error": "agent_count must be a positive integer.",
                "action": "Ask the user for a concrete swarm size if it was not specified.",
            }, ensure_ascii=False)
        if self.runtime.swarm_created_workers:
            return json.dumps({
                "error": "Swarm size must be declared before creating workers.",
                "created": self.runtime.swarm_created_workers,
            }, ensure_ascii=False)
        if self.runtime.swarm_expected_workers is not None and self.runtime.swarm_expected_workers != count:
            return json.dumps({
                "error": "Swarm size is already declared for this run.",
                "declared": self.runtime.swarm_expected_workers,
                "requested": count,
            }, ensure_ascii=False)
        self.runtime.swarm_expected_workers = count
        self.runtime.verbose.log("SWARM START", {"agent_count": count})
        self.runtime._ensure_swarm_reporter()
        self.runtime._emit_swarm_status(force=True)
        return json.dumps({
            "mode": "swarm",
            "declared": count,
            "created": self.runtime.swarm_created_workers,
            "launched": self.runtime.swarm_launched_workers,
            "message": f"Swarm declared with {count} agents. Create and start exactly {count} numbered workers.",
        }, ensure_ascii=False)

    async def swarm_status(self) -> str:
        """Emit and return the current aggregate Swarm snapshot."""
        if not self.runtime.is_swarm_mode:
            return json.dumps({"error": "swarm_status is available only in Swarm mode."})
        payload = self.runtime._swarm_snapshot()
        self.runtime._emit_swarm_status(force=True)
        self.runtime.verbose.log("SWARM STATUS", payload)
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def delegate_task(
            self,
            task: str,
            name: str = "Specialist",
            instruction: str = "",
            system_prompt: str = "",
            language: str = "",
    ) -> str:
        """Delegate one self-contained task through the reusable agent-as-tool bridge."""
        return await self.runtime.delegate_bridge.delegate_task(
            task=task,
            name=name,
            instruction=instruction,
            system_prompt=system_prompt,
            language=language,
        )

    async def cleanup(self):
        self.runtime.verbose.log("CLEANUP BEGIN", [w.public_dict() for w in self.runtime.workers.values()])
        if self.runtime._swarm_reporter_task is not None:
            self.runtime._swarm_reporter_task.cancel()
            await asyncio.gather(self.runtime._swarm_reporter_task, return_exceptions=True)
            self.runtime._swarm_reporter_task = None
        for state in list(self.runtime.workers.values()):
            if state.task and not state.task.done():
                state.stop_requested = True
                state.task.cancel()
        pending = [s.task for s in self.runtime.workers.values() if s.task is not None and not s.task.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self.runtime.workers.clear()
        self.runtime._swarm_worker_numbers.clear()
        self.runtime._worker_parent_parts.clear()
        self.runtime._stored_worker_context_runs.clear()
        self.runtime.verbose.log("CLEANUP END", {"workers": 0, "finished": self.runtime.finished})
