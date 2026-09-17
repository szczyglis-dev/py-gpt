#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 13:20:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
from typing import Optional

from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult

from .autonomy import AgentCheckpoint
from .emitter import RuntimeEmitter
from .runtime import AgentsV2Runtime
from .utils import result_text


class Runner:
    """Execute one Agents v2 user turn inside the existing BridgeWorker thread."""

    def __init__(self, window=None):
        self.window = window
        self.last_error: Optional[Exception] = None
        # Debug inspector hooks. current_runtime is live only for an active turn;
        # last_runtime remains available after completion for post-run inspection.
        self.current_runtime = None
        self.last_runtime = None

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
        finally:
            self.current_runtime = None

    async def _run(self, context, extra, signals, emitter: RuntimeEmitter):
        runtime = AgentsV2Runtime(self.window, context, extra, signals, emitter)
        self.current_runtime = runtime
        self.last_runtime = runtime
        runtime.debug_event_count = 0
        runtime.debug_event_types = {}
        emitter.begin()
        current_input = str(getattr(context.ctx, "final_input", None) or context.prompt or "")
        runtime.verbose_text("USER INPUT", current_input)
        history = runtime.memory_store.load_history(
            context.ctx,
            model=context.model,
            current_input=current_input,
        )
        runtime.verbose_log(runtime.main_event("HISTORY"), history)


        # Match Agents/Chat with Files RAG behavior: retrieve relevant context
        # before the first main-agent call and inject it into both the main agent
        # and subsequently created workers/specialists.
        rag_query = str(context.prompt or current_input)
        runtime.prefetch_rag_context(rag_query)
        llm = runtime.get_llm(stream=True, actor_id="orchestrator")
        main_system_prompt = runtime.main_agent_prompt()
        main_tools = runtime.main_agent_tools()
        main_agent = runtime.build_agent(
            name=runtime.main_agent_name,
            description=runtime.main_agent_description,
            llm=llm,
            system_prompt=main_system_prompt,
            tools=main_tools,
        )

        main_memory = None
        if runtime.window.core.context_manager.enabled():
            # Bounded LlamaIndex Memory is required inside a single long agent
            # run. Without it, top-level CTX_END checkpoints arrive too late: a
            # tool-heavy workflow can exceed the provider context window before
            # the user-visible turn has finished.
            main_memory = runtime.window.core.context_manager.build_agent_memory(
                runtime,
                actor_id="orchestrator",
                system_prompt=main_system_prompt,
                tools=main_tools,
                persistent=True,
            )
            await main_memory.aput_messages(history)

        handler = None
        stop_task = None
        event_count = 0
        event_types = {}
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
            main_max_iterations = runtime.main_max_iterations
            # Managed modes spend one extra internal LLM pass on the final
            # user-facing answer after workflow_finish validates the workflow.
            # Do not consume the user's configured work-iteration budget for that
            # transport/finalization pass (0/unlimited already maps to sys.maxsize).
            if runtime.uses_workflow_finish and runtime.main_max_iterations_configured > 0:
                main_max_iterations += 1
            run_kwargs = {
                "user_msg": main_input,
                "max_iterations": main_max_iterations,
                "early_stopping_method": "generate",
            }
            if main_memory is not None:
                # Passing ``memory`` lets LlamaIndex manage the FIFO after every
                # internal model/tool pass. The initial durable history was seeded
                # through SafeAgentMemory above.
                run_kwargs["memory"] = main_memory
            else:
                run_kwargs["chat_history"] = history
            runtime.window.core.api.logger.log_input(
                type="llama_index.agent.run",
                provider=str(getattr(runtime.model, "provider", "") or ""),
                kwargs=run_kwargs,
                input=main_input,
                history=history,
                model=getattr(runtime.model, "id", None),
                path="main_agent.run",
                extra={"actor": "orchestrator", "agent_mode": runtime.agent_mode.value},
            )
            handler = main_agent.run(**run_kwargs)

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
                event_count += 1
                event_name = type(event).__name__
                event_types[event_name] = event_types.get(event_name, 0) + 1
                runtime.debug_event_count = event_count
                runtime.debug_event_types = dict(event_types)
                # In managed modes workflow_finish only validates/arms the final
                # response. The first non-empty AgentStream after that tool result
                # is the real authoritative final answer, so prepare its durable
                # part/UI barrier *before* timeline processing sees the delta.
                if (isinstance(event, AgentStream)
                        and getattr(event, "delta", None)
                        and runtime.awaiting_workflow_final_response
                        and not runtime.workflow_final_stream_started):
                    runtime.begin_workflow_final_stream()

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

                if isinstance(event, AgentCheckpoint):
                    emitter.mark_block_boundary()
                    runtime._close_primary_stream_segment()
                    runtime._actor_needs_new_part["orchestrator"] = True
                    post_tool_stream = True
                    continue

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
                    fallback = result_text(result)
                    runtime.verbose_text(runtime.main_event("RESULT"), fallback)

                    exhausted = getattr(main_agent, "_iteration_limit_reached", False) is True
                    stalled = getattr(main_agent, "_stalled", False) is True
                    if exhausted or stalled:
                        reason = "Iteration limit reached" if exhausted else "Agent repeated an unchanged checkpoint"
                        runtime.final_answer = reason + "; task may be incomplete.\n\n" + fallback
                        runtime.finished = True
                        final_part = runtime._prepare_final_part()
                        await emitter.stream_final(
                            runtime.final_answer,
                            part_uuid=getattr(final_part, "uuid", None) if final_part is not None else None,
                        )
                    elif runtime.uses_workflow_finish:
                        if runtime.workflow_final_requested:
                            # workflow_finish has already validated the workflow.
                            # Resolve the just-completed ordinary assistant pass as
                            # the authoritative final answer. In the normal path its
                            # deltas were already forwarded to WebView live; only
                            # providers that fail to expose deltas use the fallback
                            # materialized replay below.
                            streamed = runtime.primary_stream_final_output()
                            runtime.final_answer = (
                                streamed
                                or runtime.resolve_primary_final_output(fallback)
                                or runtime.workflow_final_hint
                                or fallback
                                or "OK"
                            )
                            runtime.finished = True
                            if runtime.workflow_final_stream_started and streamed:
                                runtime.mark_current_part_final()
                                emitter.accept_streamed_final()
                            else:
                                final_part = runtime._prepare_final_part()
                                await emitter.stream_final(
                                    runtime.final_answer,
                                    part_uuid=getattr(final_part, "uuid", None) if final_part is not None else None,
                                )
                        else:
                            # Defensive compatibility path: a provider may end the
                            # managed workflow without calling workflow_finish.
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
        finally:
            runtime.window.core.api.logger.log_output(
                type="llama_index.agent.run",
                provider=str(getattr(runtime.model, "provider", "") or ""),
                output=runtime.final_answer or runtime.last_orchestrator_output(),
                chunks=event_count,
                chunk_types=event_types,
                model=getattr(runtime.model, "id", None),
                extra={
                    "actor": "orchestrator",
                    "finished": runtime.finished,
                    "stopped": runtime.is_stopped(),
                    "agent_mode": runtime.agent_mode.value,
                },
            )
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
            # cleanup() intentionally clears live worker/swarm maps. Preserve a
            # debug-only snapshot so the inspector still shows the completed flow.
            runtime.debug_cleanup_snapshot = {
                "finished": bool(runtime.finished),
                "stopped": bool(runtime.is_stopped()),
                "final_answer": str(runtime.final_answer or ""),
                "workers": {
                    wid: {
                        **state.public_dict(include_result=True),
                        "instruction": state.instruction,
                        "system_prompt": state.system_prompt,
                        "stop_requested": state.stop_requested,
                        "task_done": bool(state.task.done()) if state.task is not None else None,
                        "task_cancelled": bool(state.task.cancelled()) if state.task is not None else None,
                    }
                    for wid, state in list(runtime.workers.items())
                },
                "swarm_worker_numbers": dict(runtime._swarm_worker_numbers),
                "worker_parent_parts": {
                    str(k): getattr(v, "uuid", None)
                    for k, v in runtime._worker_parent_parts.items()
                },
                "stored_worker_context_runs": list(runtime._stored_worker_context_runs),
            }
            await runtime.cleanup()
            runtime.export_tool_calls_to_main_ctx()
            # The footer/status token summary represents one complete Agents v2
            # user turn: user input -> every orchestrator/worker LLM pass -> final
            # response. Commit it only now so no partial/intermediate usage leaks
            # into the UI while the workflow is still running.
            if runtime.finished and str(runtime.final_answer or runtime.last_orchestrator_output()).strip():
                turn_usage = runtime.apply_token_usage()
                runtime.verbose_log("TURN TOKEN USAGE", {
                    "input_tokens": turn_usage[0],
                    "output_tokens": turn_usage[1],
                    "total_tokens": turn_usage[2],
                })
            emitter.clear_status()
            final_part = runtime._actor_part("orchestrator", create=False)
            final_part_uuid = getattr(final_part, "uuid", None) if final_part is not None else None
            emitter.finish(
                runtime.final_answer,
                part_uuid=final_part_uuid,
                artifacts=runtime.pending_artifacts(),
            )
            runtime.verbose_log("RUNNER FINALIZE END", {
                "final_answer": runtime.final_answer,
                "agent_mode": runtime.agent_mode.value,
            })
