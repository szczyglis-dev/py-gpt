"""Forward nested workflow events without leaking terminal/control events."""
import asyncio
from contextlib import suppress

from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult
from workflows.errors import WorkflowCancelledByUser


async def consume_handler(handler, on_event, stopped):
    """Drain events and await completion concurrently, including silent failures."""
    async def consume():
        async for event in handler.stream_events():
            if stopped():
                raise WorkflowCancelledByUser()
            await on_event(event)

    async def result():
        return await handler

    async def watch():
        while True:
            if stopped():
                await handler.cancel_run()
                raise WorkflowCancelledByUser()
            await asyncio.sleep(0.1)

    consumer = asyncio.create_task(consume())
    terminal = asyncio.create_task(result())
    watcher = asyncio.create_task(watch())
    complete = False
    try:
        pending = {consumer, terminal}
        while pending:
            done, _ = await asyncio.wait(pending | {watcher}, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                # A workflow can fail without putting a StopEvent into its event
                # queue. Await the result concurrently so this cannot hang chat.
                task.result()
            pending -= done
        if stopped():
            raise WorkflowCancelledByUser()
        complete = True
        return terminal.result()
    finally:
        # Cancel the workflow before cancelling the task awaiting its result:
        # cancelling that task first can bypass LlamaIndex's graceful cleanup.
        watcher.cancel()
        if not complete:
            with suppress(asyncio.CancelledError, Exception):
                await handler.cancel_run()
        for task in (consumer, terminal, watcher):
            if not task.done():
                task.cancel()
        await asyncio.gather(consumer, terminal, watcher, return_exceptions=True)


async def forward_handler(handler, ctx, stopped, *, name=None, text_filter=None,
                          emit_text=True):
    """Forward child text/tools, keeping child terminal/control events private."""
    pieces = []

    async def forward(event):
        if isinstance(event, AgentStream):
            delta = event.delta or ""
            if text_filter is not None:
                delta = text_filter(delta)
            if emit_text and delta:
                pieces.append(delta)
                ctx.write_event_to_stream(event.model_copy(update={
                    "delta": delta, "current_agent_name": name or event.current_agent_name,
                }))
        elif isinstance(event, (ToolCall, ToolCallResult)):
            ctx.write_event_to_stream(event)
        # The parent owns fallback prose; AgentOutput may contain routing JSON.

    result = await consume_handler(handler, forward, stopped)
    return result, "".join(pieces)


class CodeActTextFilter:
    """Remove executable protocol blocks even when tags span provider deltas.

    Calls/results are displayed once by the tool timeline, not as raw XML or a
    second copy of the code in assistant prose.
    """
    def __init__(self):
        self.pending = ""
        self.closing = None

    def feed(self, delta, final=False):
        self.pending += delta or ""
        visible = []
        while self.pending:
            tags = (self.closing,) if self.closing else ("<execute>", "<tool>")
            matches = [(self.pending.find(tag), tag) for tag in tags if tag in self.pending]
            if matches:
                index, tag = min(matches)
                if self.closing is None:
                    visible.append(self.pending[:index])
                    self.closing = "</execute>" if tag == "<execute>" else "</tool>"
                else:
                    self.closing = None
                self.pending = self.pending[index + len(tag):]
                continue
            keep = 0
            if not final:
                for tag in tags:
                    for count in range(1, len(tag)):
                        if self.pending.endswith(tag[:count]):
                            keep = max(keep, count)
            value = self.pending[:-keep] if keep else self.pending
            if self.closing is None:
                visible.append(value)
            self.pending = self.pending[-keep:] if keep else ""
            break
        return "".join(visible)
