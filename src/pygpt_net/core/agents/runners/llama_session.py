"""Per-run LlamaIndex state using the shared Agents v2 UI/plugin transport.

The workflow owns logical boundaries; Qt owns streamed text updates. Never read
part.output to decide whether a boundary is needed: queued Qt events may lag.
"""
import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

from pygpt_net.core.agents_v2.context import RuntimeContext
from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
from pygpt_net.core.agents_v2.tools import WorkerToolFactory
from .session_components import SessionArtifacts, SessionTimeline, SessionStatus, SessionToolHistory
from pygpt_net.core.agents_v2.utils import tool_result_value, translated_status
from pygpt_net.item.ctx import CtxItem


class LlamaSession:
    def __init__(self, window, context, extra, signals, visible=True):
        self.window = window
        self.context = context
        self.visible = visible
        self.emitter = RuntimeEmitter(context, extra, signals)
        self.run_id = uuid4().hex
        self.name = "Agent"
        self.part = None
        self.text = ""
        self.completed = []
        self.boundary_pending = False
        self.final_answer = ""
        self.artifacts = SessionArtifacts(self)
        self.timeline = SessionTimeline(self)
        self.status = SessionStatus(self)
        self.model = getattr(context, "model", None)
        self.index_id = getattr(context, "idx", None)
        if self.index_id in ("_", "-"):
            self.index_id = None
        self.allow_local_tools = True
        self.is_swarm_mode = False
        self.main_agent_name = "Agent"
        self.local_tool_lock = asyncio.Lock()
        self.tool_lock = self.local_tool_lock
        self.verbose = SimpleNamespace(log=lambda *args, **kwargs: None)
        self.inputs = RuntimeContext(self)
        # Keep legacy LlamaIndex sessions on the same multimodal input path as
        # Agents v2, with input preparation owned by the inputs component.
        self.inputs.persist_images()
        self.shared_context_text = self.inputs.shared_context()
        self.tool_factory = WorkerToolFactory(self)
        self.provider_ctx = self.artifacts.tool_context("orchestrator")
        self.llm = None
        self.actor = SimpleNamespace(
            id="orchestrator",
            name=self.name,
            progress="",
            stop_requested=False,
            tool_ctx=self.provider_ctx,
            artifacts=self.artifacts.values,
        )
        self.return_tool_calls_to_main_ctx = True
        self.tool_history = SessionToolHistory(self)
        self.calls = []
        self.part_text = {}
        self.finished = False
        if visible:
            context.ctx.extra["agent_timeline"] = True
            context.ctx.extra["agent_input"] = True
            context.ctx.extra["agent_output"] = True

    def is_stopped(self):
        return self.window.controller.kernel.stopped()


    def build_worker_message(self, text: str):
        value = str(text or "")
        if self.shared_context_text:
            value += (
                "\n\n<shared_attachment_context>\n"
                + self.shared_context_text
                + "\n</shared_attachment_context>"
            )
        return self.inputs.message(value)

    def bind_llm(self, llm):
        self.llm = llm
        return llm


    def boundary(self, name=None):
        if self.visible:
            self.emitter.mark_block_boundary()
        if self.text:
            self.completed.append(self.text)
            self.text = ""
            self.boundary_pending = True
        if name:
            self.name = str(name)

    async def append(self, value):
        if not value:
            return
        if self.boundary_pending:
            if self.visible:
                self.tool_history.promote_all()
                self.part = self.window.core.ctx.begin_part(
                    self.context.ctx, agent_id="orchestrator", name=self.name,
                    output="", extra={"agents_v2_orchestrator": True}, joiner="\n\n",
                )
            self.boundary_pending = False
        part = self.timeline.part()
        if self.visible and not self.text:
            self.emitter.clear_status()
        self.text += str(value)
        if self.visible:
            self.part_text[part.uuid] = self.text
            # Text.is_stream() deliberately returns False for legacy agents:
            # it disables the generic chat worker, not this workflow's UI stream.
            # Always forward visible workflow deltas through our own lifecycle.
            await self.emitter.append_streamed(str(value), part_uuid=part.uuid, ensure_incremental=True)

    async def event(self, event):
        from llama_index.core.agent.workflow import AgentStream, AgentOutput, ToolCall, ToolCallResult
        self.artifacts.collect_from_llm(response=event)
        from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent, StatusEvent
        if isinstance(event, StatusEvent):
            if self.visible:
                self.emitter.status(event.status)
        elif isinstance(event, StepEvent):
            self.boundary((event.meta or {}).get("agent_name"))
        elif isinstance(event, AgentStream):
            name = getattr(event, "current_agent_name", None)
            if name and name != self.name:
                self.boundary(name)
            await self.append(event.delta)
        elif isinstance(event, ToolCall):
            self.boundary(getattr(event, "current_agent_name", None))
            if self.visible:
                if not self.window.core.command.is_tool_hidden(event.tool_name):
                    self.status.emit("status.agent_v2.tool", tool=event.tool_name)
                self.record_call(event)
        elif isinstance(event, ToolCallResult):
            if self.visible:
                raw_id = str(event.tool_id or "")
                pending = next((entry for entry in self.calls
                                if not entry["done"] and entry["name"] == event.tool_name
                                and (not raw_id or entry["raw_id"] == raw_id)), None)
                if pending is None:
                    pending = self.record_call(event)
                self.tool_history.persist_result(
                    tool_result_value(event), "orchestrator", event.tool_name, pending["id"],
                )
                pending["done"] = True
            self.boundary_pending = True
            if self.visible:
                self.emitter.show_loading()
        elif isinstance(event, AgentOutput):
            name = getattr(event, "current_agent_name", None)
            if name and name != self.name:
                self.boundary(name)
            # This is a model-pass output, not necessarily the workflow's final.
            # Supply prose for providers which do not emit AgentStream at all.
            if not event.tool_calls:
                value = result_text(event)
                if value and not self.text:
                    await self.append(value)

    def record_call(self, event):
        name = getattr(event, "current_agent_name", None)
        if name and name != self.name:
            self.boundary(name)
        raw_id = str(event.tool_id or "")
        # IDs are only guaranteed unique inside a child agent invocation. Keep
        # repeated IDs from later workflow nodes as separate durable executions.
        call_id = raw_id if raw_id and not any(e["id"] == raw_id for e in self.calls) else None
        persisted = self.tool_history.persist_call(
            event.tool_name, event.tool_kwargs, "orchestrator", call_id,
        )
        entry = {"raw_id": raw_id, "id": persisted, "name": event.tool_name, "done": False}
        self.calls.append(entry)
        return entry

    async def execute_plugin(self, name, params):
        if self.is_stopped():
            raise asyncio.CancelledError()
        if self.emitter.signals is None:
            raise RuntimeError("LlamaIndex plugin execution requires the UI bridge.")
        async with self.tool_lock:
            # Isolate every plugin invocation while reusing the Agents v2 transport
            # contract for runtime attachments and explicit user-delivery files.
            tool_ctx = self.artifacts.tool_context("orchestrator")
            tool_ctx.reply = False
            tool_ctx.extra["agent_input"] = True
            response = await self.emitter.execute_plugin(
                tool_ctx, [{"cmd": name, "params": params}], self.is_stopped,
            )

            runtime_attachments = self.tool_factory._extract_runtime_attachments(response)
            runtime_attachments.extend(self.tool_factory._drain_transport_images(tool_ctx))
            delivery_files = self.tool_factory._extract_delivery_files(response)
            if runtime_attachments:
                unique = []
                seen = set()
                for entry in runtime_attachments:
                    path = str(entry.get("path") or "")
                    if path and path not in seen:
                        seen.add(path)
                        unique.append(entry)
                runtime_attachments = unique

            display_response = (
                self.tool_factory._strip_private_artifact_markers(response)
                if runtime_attachments or delivery_files else response
            )
            self.artifacts.collect(tool_ctx)
            if delivery_files:
                self.artifacts.register_files(delivery_files)
            tool_ctx.reply = False

            if runtime_attachments:
                return self.tool_factory._runtime_attachment_blocks(
                    display_response, runtime_attachments
                )
            return self.tool_factory._response_text(display_response)

    async def finish(self, terminal):
        self.artifacts.collect_from_llm(response=terminal)
        final = result_text(terminal) or self.text.strip()
        # Some adapters return the accumulated prose from every model pass.
        # Strip only exact completed prefixes, retaining an already-final answer.
        for previous in self.completed:
            prefix = previous.strip()
            if prefix and final.startswith(prefix) and final[len(prefix):].strip():
                final = final[len(prefix):].strip()
        if final:
            self.context.ctx.set_agent_final_response(final)
            self.context.ctx.extra["agent_finish"] = True
            if final != self.text.strip() or self.boundary_pending:
                self.boundary()
                await self.append(final)
            part = self.timeline.part()
            if self.visible:
                self.emitter.mark_block_boundary()
                part.extra["agents_v2_final"] = True
                self.window.core.ctx.update_part(self.context.ctx, part, sync_item=False)
                self.tool_history.promote_all()
                self.emitter.accept_streamed_final()
                self.emitter.finish(final, part_uuid=part.uuid, artifacts=self.artifacts.values)
            self.final_answer = final
        elif self.visible:
            self.emitter.finish()
        self.finished = True
        self.context.ctx.set_agent_final_response(final)
        if not self.visible:
            self.context.ctx.set_output(final)

    def abort(self):
        if self.finished:
            return
        self.finished = True
        if self.visible:
            if self.is_stopped():
                # Qt intentionally drops queued appends after Stop. Preserve the
                # independently collected prefixes before closing the stream.
                for part in self.context.ctx.parts:
                    if part.uuid in self.part_text:
                        part.set_output(self.part_text[part.uuid])
                        self.window.core.ctx.update_part(self.context.ctx, part, sync_item=False)
            if self.is_stopped():
                self.context.ctx.sync_output_from_parts()
            self.tool_history.promote_all()
            self.emitter.clear_status()
            self.emitter.finish()


def result_text(result):
    """Read protocol fields, never leak Pydantic/object repr into a response."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    for key in ("final_answer", "response", "result", "content"):
        value = result.get(key) if isinstance(result, dict) else getattr(result, key, None)
        if value is not None and value is not result:
            text = result_text(value)
            if text:
                return text
    return ""
