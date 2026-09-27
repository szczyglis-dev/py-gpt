"""Per-run LlamaIndex state using the shared Agents v2 UI/plugin transport.

The workflow owns logical boundaries; Qt owns streamed text updates. Never read
part.output to decide whether a boundary is needed: queued Qt events may lag.
"""
import asyncio
import base64
import json
import os
from types import SimpleNamespace
from uuid import uuid4

from pygpt_net.core.agents_v2.context import RuntimeContext
from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
from pygpt_net.core.agents_v2.tools import WorkerToolFactory
from pygpt_net.core.agents_v2.tool_history import RuntimeToolHistory
from pygpt_net.core.agents_v2.utils import tool_result_value, translated_status
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.llms.artifacts import drain_llm_urls


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
        self.context_api = RuntimeContext(self)
        # Keep legacy LlamaIndex sessions on the same multimodal input path as
        # Agents v2. RuntimeContext deliberately calls back through the runtime
        # wrappers below, so expose them before building/persisting turn context.
        self._persist_input_images()
        self.shared_context_text = self._build_shared_context()
        self.tool_factory = WorkerToolFactory(self)
        self.provider_ctx = self._make_tool_ctx("orchestrator")
        self.llm = None
        self.actor = SimpleNamespace(
            id="orchestrator",
            name=self.name,
            progress="",
            stop_requested=False,
            tool_ctx=self.provider_ctx,
            artifacts=self.artifacts,
        )
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

    def _make_tool_ctx(self, actor_id: str) -> CtxItem:
        parent = self.context.ctx
        ctx = CtxItem(getattr(parent, "mode", None))
        ctx.meta = getattr(parent, "meta", None)
        ctx.meta_id = getattr(parent, "meta_id", None)
        ctx.model = getattr(parent, "model", None)
        if parent is not None:
            ctx.images = list(getattr(parent, "images", None) or [])
            ctx.attachments = list(getattr(parent, "attachments", None) or [])
            ctx.additional_ctx = list(getattr(parent, "additional_ctx", None) or [])
            ctx.doc_ids = list(getattr(parent, "doc_ids", None) or [])
            ctx.hidden_input = getattr(parent, "hidden_input", None)
        ctx.agent_call = True
        ctx.async_disabled = False
        ctx.internal = True
        ctx.hidden = True
        ctx.current = False
        ctx.extra = {
            "agent_legacy_actor": actor_id,
            "run_id": self.run_id,
            # Reuse the same async plugin completion bridge as Agents v2.
            "agents_v2_async_tool": True,
        }
        return ctx

    def _input_image_paths(self):
        """Return native image inputs using the shared Agents v2 resolver."""
        return self.context_api._input_image_paths()

    def _persist_input_images(self):
        """Persist native image inputs on the durable turn, matching Agents v2."""
        return self.context_api._persist_input_images()

    def _build_shared_context(self):
        return self.context_api._build_shared_context()

    def build_user_message(self, text: str):
        return self.context_api.build_user_message(text)

    def build_worker_message(self, text: str):
        value = str(text or "")
        if self.shared_context_text:
            value += (
                "\n\n<shared_attachment_context>\n"
                + self.shared_context_text
                + "\n</shared_attachment_context>"
            )
        return self.context_api.build_user_message(value)

    def bind_llm(self, llm):
        self.llm = llm
        return llm

    def collect_llm_artifacts(self, response=None):
        if self.llm is None:
            return []
        try:
            urls = drain_llm_urls(
                self.provider_ctx,
                self.llm,
                response=response,
                on_error=self.window.core.debug.log,
            )
            self.collect_artifacts(self.provider_ctx)
            return urls or []
        except Exception as exc:
            self.window.core.debug.log(exc)
            return []

    def _show_tool_status(self, tool_name: str) -> bool:
        return not self.window.core.command.is_tool_hidden(tool_name)

    def emit_runtime_status(self, key: str, **kwargs):
        if not self.visible:
            return
        tool = kwargs.get("tool")
        if tool:
            self.emitter.status(translated_status(key, tool=tool))

    def register_local_plugin_tool(self, name: str):
        return None

    def record_local_plugin_tool_call(self, name, params, actor="orchestrator"):
        return self.history._persist_tool_call(name, params, actor)

    def record_local_plugin_tool_result(self, call_id, name, response, actor="orchestrator"):
        self.history._persist_tool_result(response, actor, name, call_id)

    def collect_artifacts(self, source_ctx: CtxItem, worker=None):
        if source_ctx is None:
            return
        # Files are deliberately opt-in, exactly as in Agents v2. Merely reading
        # a file must not attach it to the user's final response.
        for attr in ("images", "urls", "attachments"):
            target = self.artifacts[attr]
            for value in getattr(source_ctx, attr, None) or []:
                if value not in target:
                    target.append(value)

    def register_delivery_files(self, files, worker=None):
        exported = []
        for entry in files or []:
            path = str(entry.get("path") if isinstance(entry, dict) else entry or "").strip()
            if path and path not in self.artifacts["files"]:
                self.artifacts["files"].append(path)
                exported.append(path)
        return exported

    def register_provider_image_base64(self, data: str, actor_id=None):
        if not data:
            return None
        try:
            raw = base64.b64decode(data)
            path = self.window.core.image.gen_unique_path(self.provider_ctx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(raw)
            local = self.window.core.filesystem.make_local(path, ctx=self.provider_ctx)
            if local not in self.provider_ctx.images:
                self.provider_ctx.images.append(local)
            runtime_artifact = self.window.core.filesystem.materialize_runtime_artifact(
                path, ctx=self.provider_ctx,
            )
            self.collect_artifacts(self.provider_ctx)
            return runtime_artifact
        except Exception as exc:
            self.window.core.debug.log(exc)
            return None

    def register_provider_container_files(self, files, actor_id=None):
        if not files:
            return []
        try:
            downloaded = self.window.core.api.openai.container.download_files(
                self.provider_ctx, list(files)
            )
            # Provider container files are generated outputs, not arbitrary files
            # observed by a read/search tool, so they are valid response artifacts.
            for value in downloaded or []:
                path = str(value.get("path") if isinstance(value, dict) else value or "").strip()
                if path and path not in self.artifacts["files"]:
                    self.artifacts["files"].append(path)
            self.collect_artifacts(self.provider_ctx)
            return downloaded or []
        except Exception as exc:
            self.window.core.debug.log(exc)
            return []

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
        self.collect_llm_artifacts(response=event)
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
            # Isolate every plugin invocation while reusing the Agents v2 transport
            # contract for runtime attachments and explicit user-delivery files.
            tool_ctx = self._make_tool_ctx("orchestrator")
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
            self.collect_artifacts(tool_ctx)
            if delivery_files:
                self.register_delivery_files(delivery_files)
            tool_ctx.reply = False

            if runtime_attachments:
                return self.tool_factory._runtime_attachment_blocks(
                    display_response, runtime_attachments
                )
            return self.tool_factory._response_text(display_response)

    async def finish(self, terminal):
        self.collect_llm_artifacts(response=terminal)
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
