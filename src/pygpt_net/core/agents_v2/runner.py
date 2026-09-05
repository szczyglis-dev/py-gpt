#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
from typing import Optional

from llama_index.core.agent.workflow import AgentStream

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
                emitter.status("Agents v2 failed")
                emitter.finish(f"Agents v2 error: {exc}")
            except Exception:
                pass
            return True

    async def _run(self, context, extra, signals, emitter: RuntimeEmitter):
        runtime = AgentsV2Runtime(self.window, context, extra, signals, emitter)
        emitter.begin()
        emitter.status("Planning task")

        history = runtime.memory_store.load_history(
            context.ctx,
            context.preset,
            model=context.model,
            current_input=str(getattr(context.ctx, "input", "") or context.prompt or ""),
        )
        llm = self.window.core.idx.llm.get(context.model, stream=True)
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
            handler = orchestrator.run(
                user_msg=runtime.build_user_message(str(context.prompt or "") + shared),
                chat_history=history,
                max_iterations=48,
                early_stopping_method="generate",
            )

            async def watch_stop():
                while not runtime.finished:
                    if runtime.is_stopped():
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

                if isinstance(event, AgentStream) and getattr(event, "delta", None):
                    emitter.append(event.delta)

            if not runtime.is_stopped():
                if not runtime.finished:
                    result = await handler
                    fallback = runtime._result_text(result)
                    runtime.final_answer = fallback or emitter.text.strip() or "Task completed."
                    runtime.finished = True
                    if fallback and fallback.strip() not in emitter.text.strip():
                        emitter.append(("\n\n" if emitter.text.strip() else "") + fallback)

                final_text = runtime.final_answer or emitter.text.strip()
                runtime.memory_store.append_turn(
                    context.ctx,
                    context.preset,
                    str(getattr(context.ctx, "input", "") or context.prompt or ""),
                    final_text,
                )
        finally:
            if stop_task is not None:
                stop_task.cancel()
                await asyncio.gather(stop_task, return_exceptions=True)
            await runtime.cleanup()
            emitter.clear_status()
            emitter.finish(runtime.final_answer)
