"""Legacy session components implementing the shared runtime domain contracts."""

import base64
import os

from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.llms.artifacts import drain_llm_urls
from pygpt_net.core.agents_v2.tool_history import RuntimeToolHistory
from pygpt_net.core.agents_v2.utils import translated_status


class SessionArtifacts:
    def __init__(self, session):
        self.session = session
        self.values = {key: [] for key in ("files", "images", "urls", "attachments")}

    def tool_context(self, actor_id: str) -> CtxItem:
        parent = self.session.context.ctx
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
            "run_id": self.session.run_id,
            # Reuse the same async plugin completion bridge as Agents v2.
            "agents_v2_async_tool": True,
        }
        return ctx

    def collect_from_llm(self, response=None):
        if self.session.llm is None:
            return []
        try:
            urls = drain_llm_urls(
                self.session.provider_ctx,
                self.session.llm,
                response=response,
                on_error=self.session.window.core.debug.log,
            )
            self.collect(self.session.provider_ctx)
            return urls or []
        except Exception as exc:
            self.session.window.core.debug.log(exc)
            return []

    def collect(self, source_ctx: CtxItem, worker=None):
        if source_ctx is None:
            return
        # Files are deliberately opt-in, exactly as in Agents v2. Merely reading
        # a file must not attach it to the user's final response.
        for attr in ("images", "urls", "attachments"):
            target = self.values[attr]
            for value in getattr(source_ctx, attr, None) or []:
                if value not in target:
                    target.append(value)

    def register_files(self, files, worker=None):
        exported = []
        for entry in files or []:
            path = str(entry.get("path") if isinstance(entry, dict) else entry or "").strip()
            if path and path not in self.values["files"]:
                self.values["files"].append(path)
                exported.append(path)
        return exported

    def register_image(self, data: str, actor_id=None):
        if not data:
            return None
        try:
            raw = base64.b64decode(data)
            path = self.session.window.core.image.gen_unique_path(self.session.provider_ctx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(raw)
            local = self.session.window.core.filesystem.make_local(path, ctx=self.session.provider_ctx)
            if local not in self.session.provider_ctx.images:
                self.session.provider_ctx.images.append(local)
            runtime_artifact = self.session.window.core.filesystem.materialize_runtime_artifact(
                path, ctx=self.session.provider_ctx,
            )
            self.collect(self.session.provider_ctx)
            return runtime_artifact
        except Exception as exc:
            self.session.window.core.debug.log(exc)
            return None

    def register_container_files(self, files, actor_id=None):
        if not files:
            return []
        try:
            downloaded = self.session.window.core.api.openai.container.download_files(
                self.session.provider_ctx, list(files)
            )
            # Provider container files are generated outputs, not arbitrary files
            # observed by a read/search tool, so they are valid response artifacts.
            for value in downloaded or []:
                path = str(value.get("path") if isinstance(value, dict) else value or "").strip()
                if path and path not in self.values["files"]:
                    self.values["files"].append(path)
            self.collect(self.session.provider_ctx)
            return downloaded or []
        except Exception as exc:
            self.session.window.core.debug.log(exc)
            return []

    def pending(self):
        return self.values


class SessionTimeline:
    def __init__(self, session):
        self.session = session

    def metadata(self, actor):
        return "orchestrator", self.session.name, ""

    def part(self, actor="orchestrator", create=True):
        if self.session.part is None and create and self.session.visible:
            main = self.session.context.ctx
            # Adopt only the empty initial partial made by normal chat setup.
            initial = main.get_active_part()
            if initial is not None and not initial.output and not initial.tasks:
                self.session.part = initial
                initial.name = self.session.name
                initial.agent_id = "orchestrator"
                initial.extra.update({"agents_v2_orchestrator": True})
                # Chat setup may have created this part before the worker opted
                # into the durable timeline. Promote that same UUID to storage.
                if initial.id is None and main.id is not None:
                    initial.parent_item_id = main.id
                    self.session.window.core.ctx.provider.append_part(initial)
                self.session.window.core.ctx.update_part(main, initial, sync_item=False)
            else:
                self.session.part = self.session.window.core.ctx.begin_part(
                    main, agent_id="orchestrator", name=self.session.name, output="",
                    extra={"agents_v2_orchestrator": True}, joiner="\n\n",
                )
        elif (create and self.session.visible and self.session.part is not None
              and self.session.part.name != self.session.name):
            # A tool may be the new actor's first event, before any prose.
            self.session.tool_history.promote_all()
            self.session.part = self.session.window.core.ctx.begin_part(
                self.session.context.ctx, agent_id="orchestrator", name=self.session.name,
                output="", extra={"agents_v2_orchestrator": True}, joiner="\n\n",
            )
        return self.session.part


class SessionStatus:
    def __init__(self, session):
        self.session = session

    def show_tool(self, tool_name: str) -> bool:
        return not self.session.window.core.command.is_tool_hidden(tool_name)

    def emit(self, key: str, **kwargs):
        if not self.session.visible:
            return
        tool = kwargs.get("tool")
        if tool:
            part = self.session.timeline.part()
            self.session.emitter.status(
                translated_status(key, tool=tool),
                owner={"part_uuid": part.uuid, "agent_name": part.name, "placement": "before"},
            )


class SessionToolHistory(RuntimeToolHistory):
    def register_plugin(self, name: str):
        return None

    def record_local_call(self, name, params, actor="orchestrator"):
        return self.persist_call(name, params, actor)

    def record_local_result(self, call_id, name, response, actor="orchestrator"):
        self.persist_result(response, actor, name, call_id)
