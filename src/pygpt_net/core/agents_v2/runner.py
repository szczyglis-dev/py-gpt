#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 11:00:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
from typing import Optional

from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult

from .emitter import RuntimeEmitter
from .runtime import AgentsV2Runtime


class Runner:
    """Execute one Agents v2 user turn inside the existing BridgeWorker thread."""

    def __init__(self, window=None):
        self.window = window
        self.last_error: Optional[Exception] = None

    def get_error(self):
        return self.last_error

    def call(self, context, extra, signals) -> bool:
        self.last_error = None
        emitter = RuntimeEmitter(context, extra, signals)
        try:
            asyncio.run(self._run(context, extra, signals, emitter))
            return True
        except asyncio.CancelledError:
            # Cancellation is a normal control path (Stop, or Orchestrator
            # workflow_finish), not an error.
            try:
                emitter.clear_status()
                emitter.finish()
            except Exception:
                pass
            return True
        except Exception as exc:
            self.last_error = exc
            self.window.core.debug.log(exc)
            try:
                emitter.clear_status()
                emitter.finish(f"Chat with Agents: {exc}")
            except Exception:
                pass
            return True

    async def _run(self, context, extra, signals, emitter: RuntimeEmitter):
        runtime = AgentsV2Runtime(self.window, context, extra, signals, emitter)
        emitter.begin()
        current_input = str(getattr(context.ctx, "input", "") or context.prompt or "")
        runtime.verbose_text("USER INPUT", current_input)
        history = runtime.memory_store.load_history(
            context.ctx,
            context.preset,
            model=context.model,
            current_input=current_input,
        )
        runtime.verbose_log(runtime.main_event("HISTORY"), history)

        # Persist the user side immediately after previous history is loaded. If
        # execution is interrupted while a tool is running, the input-only memory
        # row survives and is available on the next turn.
        memory_turn = runtime.memory_store.begin_turn(
            context.ctx,
            context.preset,
            current_input,
        )
        runtime.verbose_log("MEMORY BEGIN", {
            "input": current_input,
            "memory_item_id": getattr(memory_turn, "id", None),
            "agent_mode": runtime.agent_mode.value,
        })

        # Match Agents/Chat with Files RAG behavior: retrieve relevant context
        # before the first main-agent call and inject it into both the main agent
        # and subsequently created workers/specialists.
        rag_query = str(context.prompt or current_input)
        runtime.prefetch_rag_context(rag_query)
        llm = runtime.get_llm(stream=True, actor_id="orchestrator")
        main_agent = runtime.build_agent(
            name=runtime.main_agent_name,
            description=runtime.main_agent_description,
            llm=llm,
            system_prompt=runtime.main_agent_prompt(),
            tools=runtime.main_agent_tools(),
        )

        handler = None
        stop_task = None
        try:
            shared = ""
            if runtime.shared_context_text:
                shared = (
                    "\n\n<turn_context>\nThis turn contains shared user attachments/context. "
                    "Use shared_context for extracted text/manifest. Current image attachments are also supplied "
                    "as native image blocks when the selected model supports image input.\n</turn_context>"
                )
            main_input = runtime.build_user_message(str(context.prompt or "") + shared)
            runtime.verbose_log(runtime.main_event("INPUT"), main_input)
            handler = main_agent.run(
                user_msg=main_input,
                chat_history=history,
                max_iterations=runtime.main_max_iterations,
                early_stopping_method="generate",
            )

            async def watch_stop():
                while not runtime.finished:
                    if runtime.is_stopped():
                        runtime.verbose_log("STOP REQUESTED", {"source": "kernel"})
                        for state in list(runtime.workers.values()):
                            if state.task and not state.task.done():
                                state.stop_requested = True
                                state.task.cancel()
                        try:
                            await handler.cancel_run()
                        except asyncio.CancelledError:
                            pass
                        except Exception:
                            pass
                        return
                    await asyncio.sleep(0.2)

            stop_task = asyncio.create_task(watch_stop(), name="agents-v2:stop-watch")

            post_tool_stream = False
            async for event in handler.stream_events():
                runtime.verbose_event(event, actor="orchestrator")
                if runtime.is_stopped():
                    try:
                        await handler.cancel_run()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                    break

                # Orchestrator and Swarm modes use workflow_finish as the
                # authoritative finalizer. Primary Agent finalizes from its
                # terminal response instead.
                if runtime.uses_workflow_finish and runtime.finished:
                    try:
                        await handler.cancel_run()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                    break

                if isinstance(event, ToolCall):
                    # A tool call closes the current model pass. Keep normal
                    # provider-sized streaming for any prose before the call.
                    emitter.mark_block_boundary()
                    post_tool_stream = False
                    continue

                if isinstance(event, ToolCallResult):
                    # The response after a tool result starts a new model pass.
                    # Some LlamaIndex/provider combinations expose that pass as
                    # one large AgentStream.delta even when streaming is enabled.
                    # Arm the emitter's incremental fallback for this segment so
                    # it is painted progressively just like a materialized final.
                    emitter.mark_block_boundary()
                    post_tool_stream = True
                    continue

                if isinstance(event, AgentStream) and getattr(event, "delta", None):
                    await emitter.append_streamed(
                        event.delta,
                        part_uuid=runtime.actor_part_uuid("orchestrator"),
                        ensure_incremental=post_tool_stream,
                    )

            if not runtime.is_stopped():
                if not runtime.finished:
                    result = await handler
                    # The final AgentOutput contains the raw provider response even
                    # when a streamed workflow did not leave citation metadata in
                    # the original adapter buffer. Capture it before resolving the
                    # final prose.
                    runtime.collect_llm_artifacts(
                        getattr(main_agent, "llm", None) or llm,
                        response=result,
                        actor_id="orchestrator",
                    )
                    fallback = runtime._result_text(result)
                    runtime.verbose_text(runtime.main_event("RESULT"), fallback)

                    if runtime.uses_workflow_finish:
                        # Managed-worker modes normally finalize via
                        # workflow_finish. Keep the historical fallback when a
                        # provider ends normally without calling the tool.
                        last_output = runtime.last_orchestrator_output()
                        runtime.final_answer = fallback or last_output or "OK"
                        runtime.finished = True
                        if last_output and runtime.final_answer.strip() == last_output.strip():
                            runtime.mark_current_part_final()
                            emitter.accept_streamed_final()
                        else:
                            final_part = runtime._prepare_final_part()
                            await emitter.stream_final(
                                runtime.final_answer,
                                part_uuid=getattr(final_part, "uuid", None) if final_part is not None else None,
                            )
                    else:
                        # Primary Agent finalizes from the terminal response. The
                        # resolver removes already-streamed pre-tool prose and
                        # understands provider-native hosted-tool boundaries.
                        runtime.final_answer = runtime.resolve_primary_final_output(fallback) or "OK"
                        runtime.verbose_text("PRIMARY AGENT RESOLVED FINAL", runtime.final_answer)
                        runtime.detach_primary_final_suffix(runtime.final_answer)
                        last_output = runtime.last_orchestrator_output()
                        runtime.finished = True
                        if last_output and runtime.final_answer.strip() == last_output.strip():
                            runtime.mark_current_part_final()
                            emitter.accept_streamed_final()
                        else:
                            final_part = runtime._prepare_final_part()
                            await emitter.stream_final(
                                runtime.final_answer,
                                part_uuid=getattr(final_part, "uuid", None) if final_part is not None else None,
                            )

                final_text = runtime.final_answer or runtime.last_orchestrator_output()
                runtime.verbose_text(runtime.main_event("FINAL TEXT"), final_text)
                memory_output = runtime.orchestrator_memory_output(final_text)
                runtime.memory_store.complete_turn(memory_turn, memory_output)
                runtime.verbose_log("MEMORY COMPLETE", {
                    "input": current_input,
                    "final_output": final_text,
                    "assistant_output": memory_output,
                    "memory_item_id": getattr(memory_turn, "id", None),
                    "agent_mode": runtime.agent_mode.value,
                })
        finally:
            runtime.verbose_log("RUNNER FINALIZE BEGIN", {
                "finished": runtime.finished,
                "stopped": runtime.is_stopped(),
                "agent_mode": runtime.agent_mode.value,
            })
            if stop_task is not None:
                stop_task.cancel()
                await asyncio.gather(stop_task, return_exceptions=True)
            # Provider-native hosted tools bypass local plugin CtxItems. Drain
            # both the LLM owned by the workflow agent and the originally created
            # adapter before runtime cleanup. Usually they are the same object; the
            # second call is a no-op after the first drain.
            agent_llm = getattr(main_agent, "llm", None)
            runtime.collect_llm_artifacts(agent_llm or llm, actor_id="orchestrator")
            if agent_llm is not None and agent_llm is not llm:
                runtime.collect_llm_artifacts(llm, actor_id="orchestrator")
            await runtime.cleanup()
            runtime.export_tool_calls_to_main_ctx()
            emitter.clear_status()
            final_part = runtime._actor_part("orchestrator", create=False)
            final_part_uuid = getattr(final_part, "uuid", None) if final_part is not None else None
            emitter.finish(runtime.final_answer, part_uuid=final_part_uuid)
            runtime.verbose_log("RUNNER FINALIZE END", {
                "final_answer": runtime.final_answer,
                "agent_mode": runtime.agent_mode.value,
            })
