"""Per-run LlamaIndex state using the shared Agents v2 UI/plugin transport.

The workflow owns logical boundaries; Qt owns streamed text updates. Never read
part.output to decide whether a boundary is needed: queued Qt events may lag.
"""
import asyncio
import json
from uuid import uuid4

from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
from pygpt_net.core.agents_v2.tool_history import RuntimeToolHistory
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
        self.artifacts = {key: [] for key in ("files", "images", "urls", "attachments")}
        self.tool_lock = asyncio.Lock()
        self._main_tool_call_seq = 0
        self._persisted_tool_tasks = {}
        self.return_tool_calls_to_main_ctx = True
        self.history = RuntimeToolHistory(self)
        self.calls = []
        self.part_text = {}
        self.finished = False
        if visible:
            context.ctx.extra["agent_timeline"] = True
            context.ctx.extra["agent_input"] = True
            context.ctx.extra["agent_output"] = True

    def is_stopped(self):
        return self.window.controller.kernel.stopped()

    def _promote_part_tasks(self, part):
        self.history._promote_part_tasks(part)

    def _new_tool_call_id(self, call_id=None):
        return self.history._new_tool_call_id(call_id)

    def _actor_metadata(self, actor):
        return "orchestrator", self.name, ""

    def _actor_part(self, actor="orchestrator", create=True):
        if self.part is None and create and self.visible:
            main = self.context.ctx
            # Adopt only the empty initial partial made by normal chat setup.
            initial = main.get_active_part()
            if initial is not None and not initial.output and not initial.tasks:
                self.part = initial
                initial.name = self.name
                initial.agent_id = "orchestrator"
                initial.extra.update({"agents_v2_orchestrator": True})
                # Chat setup may have created this part before the worker opted
                # into the durable timeline. Promote that same UUID to storage.
                if initial.id is None and main.id is not None:
                    initial.parent_item_id = main.id
                    self.window.core.ctx.provider.append_part(initial)
                self.window.core.ctx.update_part(main, initial, sync_item=False)
            else:
                self.part = self.window.core.ctx.begin_part(
                    main, agent_id="orchestrator", name=self.name, output="",
                    extra={"agents_v2_orchestrator": True}, joiner="\n\n",
                )
        return self.part

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
                self.history._promote_all_tasks()
                self.part = self.window.core.ctx.begin_part(
                    self.context.ctx, agent_id="orchestrator", name=self.name,
                    output="", extra={"agents_v2_orchestrator": True}, joiner="\n\n",
                )
            self.boundary_pending = False
        part = self._actor_part()
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
            self.boundary()
            if self.visible:
                if not self.window.core.command.is_tool_hidden(event.tool_name):
                    self.emitter.status(translated_status("status.agent_v2.tool", tool=event.tool_name))
                self.record_call(event)
        elif isinstance(event, ToolCallResult):
            if self.visible:
                raw_id = str(event.tool_id or "")
                pending = next((entry for entry in self.calls
                                if not entry["done"] and entry["name"] == event.tool_name
                                and (not raw_id or entry["raw_id"] == raw_id)), None)
                if pending is None:
                    pending = self.record_call(event)
                self.history._persist_tool_result(
                    tool_result_value(event), "orchestrator", event.tool_name, pending["id"],
                )
                pending["done"] = True
            self.boundary_pending = True
            if self.visible:
                self.emitter.show_loading()
        elif isinstance(event, AgentOutput):
            # This is a model-pass output, not necessarily the workflow's final.
            # Supply prose for providers which do not emit AgentStream at all.
            if not event.tool_calls:
                value = result_text(event)
                if value and not self.text:
                    await self.append(value)

    def record_call(self, event):
        raw_id = str(event.tool_id or "")
        # IDs are only guaranteed unique inside a child agent invocation. Keep
        # repeated IDs from later workflow nodes as separate durable executions.
        call_id = raw_id if raw_id and not any(e["id"] == raw_id for e in self.calls) else None
        persisted = self.history._persist_tool_call(
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
            # A separate context for EVERY call prevents late callbacks and
            # parallel tools from sharing results, artifacts or pending state.
            source = self.context.ctx
            tool_ctx = CtxItem()
            tool_ctx.meta = source.meta
            tool_ctx.mode = source.mode
            tool_ctx.model = source.model
            tool_ctx.agent_call = True
            tool_ctx.async_disabled = False
            tool_ctx.internal = True
            tool_ctx.hidden = True
            tool_ctx.reply = False
            tool_ctx.extra["agent_input"] = True
            response = await self.emitter.execute_plugin(
                tool_ctx, [{"cmd": name, "params": params}], self.is_stopped,
            )
            for key, values in self.artifacts.items():
                for value in getattr(tool_ctx, key, None) or []:
                    if value not in values:
                        values.append(value)
            if isinstance(response, (dict, list)):
                return json.dumps(response, ensure_ascii=False, default=str)
            return "" if response is None else str(response)

    async def finish(self, terminal):
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
            part = self._actor_part()
            if self.visible:
                self.emitter.mark_block_boundary()
                part.extra["agents_v2_final"] = True
                self.window.core.ctx.update_part(self.context.ctx, part, sync_item=False)
                self.history._promote_all_tasks()
                self.emitter.accept_streamed_final()
                self.emitter.finish(final, part_uuid=part.uuid, artifacts=self.artifacts)
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
            self.history._promote_all_tasks()
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
