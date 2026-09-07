#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
            # Cancellation is a normal control path (Stop/workflow_finish), not an error.
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
                emitter.finish(f"Agents v2: {exc}")
            except Exception:
                pass
            return True

    async def _run(self, context, extra, signals, emitter: RuntimeEmitter):
        runtime = AgentsV2Runtime(self.window, context, extra, signals, emitter)
        emitter.begin()
        runtime.emit_runtime_status("status.agent_v2.planning")

        current_input = str(getattr(context.ctx, "input", "") or context.prompt or "")
        runtime.verbose_text("USER INPUT", current_input)
        history = runtime.memory_store.load_history(
            context.ctx,
            context.preset,
            model=context.model,
            current_input=current_input,
        )
        runtime.verbose_log("ORCHESTRATOR HISTORY", history)

        # Persist the user side of this orchestrator turn immediately after the
        # previous history has been loaded.  If the user stops Agents v2 while a
        # tool is running, this input-only memory row survives and is available in
        # chat_history on the next turn instead of losing the interrupted request.
        memory_turn = runtime.memory_store.begin_turn(
            context.ctx,
            context.preset,
            current_input,
        )
        runtime.verbose_log("MEMORY BEGIN", {
            "input": current_input,
            "memory_item_id": getattr(memory_turn, "id", None),
        })

        # Match the existing Agents/Chat with Files RAG behavior: when an index is
        # selected and agent.idx.auto_retrieve is enabled, retrieve a relevant chunk
        # before the first Orchestrator call. The runtime injects it into both the
        # Orchestrator and every subsequently created worker system prompt.
        rag_query = str(context.prompt or current_input)
        runtime.prefetch_rag_context(rag_query)
        llm = runtime.get_llm(stream=True)
        orchestrator = runtime.build_agent(
            name="Orchestrator",
            description="PyGPT Agents v2 main orchestrator",
            llm=llm,
            system_prompt=runtime.orchestrator_prompt(),
            tools=runtime.orchestrator_tools(),
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
            orchestrator_input = runtime.build_user_message(str(context.prompt or "") + shared)
            runtime.verbose_log("ORCHESTRATOR INPUT", orchestrator_input)
            handler = orchestrator.run(
                user_msg=orchestrator_input,
                chat_history=history,
                max_iterations=48,
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

                # workflow_finish is authoritative. Stop immediately instead of letting
                # the model emit another tool call/text after declaring completion.
                if runtime.finished:
                    try:
                        await handler.cancel_run()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                    break

                if isinstance(event, (ToolCall, ToolCallResult)):
                    # A tool roundtrip ends one orchestrator LLM pass. The next
                    # user-visible text belongs to a new paragraph, while remaining
                    # inside the same response/message. Multiple tool events collapse
                    # into one pending boundary.
                    emitter.mark_block_boundary()
                    continue

                if isinstance(event, AgentStream) and getattr(event, "delta", None):
                    emitter.append(
                        event.delta,
                        part_uuid=runtime.actor_part_uuid("orchestrator"),
                    )

            if not runtime.is_stopped():
                if not runtime.finished:
                    result = await handler
                    fallback = runtime._result_text(result)
                    runtime.verbose_text("ORCHESTRATOR RESULT", fallback)
                    last_output = runtime.last_orchestrator_output()
                    runtime.final_answer = fallback or last_output or "OK"
                    runtime.finished = True
                    # LlamaIndex's terminal handler result commonly repeats the
                    # exact AgentStream prose that was already persisted. Reuse
                    # that partial instead of writing/replaying the same output a
                    # second time. If the terminal result is genuinely new text,
                    # it receives its own final partial as expected.
                    if last_output and runtime.final_answer.strip() == last_output.strip():
                        runtime.mark_current_part_final()
                        emitter.accept_streamed_final()
                    else:
                        final_part = runtime._prepare_final_part()
                        emitter.start_final(
                            runtime.final_answer,
                            part_uuid=getattr(final_part, "uuid", None) if final_part is not None else None,
                        )

                final_text = runtime.final_answer or runtime.last_orchestrator_output()
                runtime.verbose_text("ORCHESTRATOR FINAL TEXT", final_text)
                memory_output = runtime.orchestrator_memory_output(final_text)
                runtime.memory_store.complete_turn(memory_turn, memory_output)
                runtime.verbose_log("MEMORY COMPLETE", {
                    "input": current_input,
                    "final_output": final_text,
                    "assistant_output": memory_output,
                    "memory_item_id": getattr(memory_turn, "id", None),
                })
        finally:
            runtime.verbose_log("RUNNER FINALIZE BEGIN", {"finished": runtime.finished, "stopped": runtime.is_stopped()})
            if stop_task is not None:
                stop_task.cancel()
                await asyncio.gather(stop_task, return_exceptions=True)
            # Provider-native hosted tools bypass local plugin CtxItems. Drain
            # their captured metadata (e.g. OpenAI web-search source URLs) before
            # the runtime is cleaned up and the final message is committed.
            runtime.collect_llm_artifacts(llm)
            await runtime.cleanup()
            runtime.export_tool_calls_to_main_ctx()
            emitter.clear_status()
            final_part = runtime._actor_part("orchestrator", create=False)
            final_part_uuid = getattr(final_part, "uuid", None) if final_part is not None else None
            emitter.finish(runtime.final_answer, part_uuid=final_part_uuid)
            runtime.verbose_log("RUNNER FINALIZE END", {"final_answer": runtime.final_answer})
