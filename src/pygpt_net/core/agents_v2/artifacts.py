#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.17 13:20:00                  #
# ================================================== #

from __future__ import annotations

import json
import os
from typing import Any, Optional

from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.llms.artifacts import drain_llm_urls

from .state import WorkerState


def artifact_identity(attr: str, value: Any):
    """Return a stable user-facing identity used to suppress duplicate artifacts.

    Files, images and attachment records share one delivery namespace because the
    same path may be discovered through several provider/plugin channels. URLs keep
    their own namespace so a source URL is not hidden merely because it also backs
    a generated/downloaded attachment.
    """
    family = "attachment" if attr in {"files", "images", "attachments"} else str(attr or "artifact")
    candidate = value
    if isinstance(value, dict):
        for key in ("path", "file", "filename", "url", "uri"):
            current = value.get(key)
            if current not in (None, ""):
                candidate = current
                break

    if isinstance(candidate, str):
        text = candidate.strip()
        if family == "attachment":
            lowered = text.lower()
            if lowered.startswith("file://"):
                text = text[7:]
            if not text.lower().startswith(("http://", "https://")):
                text = os.path.normpath(text).replace("\\", "/")
        return family, text

    try:
        stable = json.dumps(candidate, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        stable = repr(candidate)
    return family, stable


class RuntimeArtifacts:
    """Provider/plugin artifact collection and isolated actor tool contexts."""

    def __init__(self, runtime):
        self.runtime = runtime

    def _seed_artifact_seen(self):
        """Do not re-export user inputs that were already attached to the main message."""
        main = self.runtime.context.ctx
        if main is None:
            return
        for attr in self.runtime._artifact_seen:
            for value in (getattr(main, attr, None) or []):
                try:
                    key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                except Exception:
                    key = repr(value)
                self.runtime._artifact_seen[attr].add(key)
                self.runtime._artifact_delivery_seen.add(artifact_identity(attr, value))

    def _provider_id(self) -> str:
        try:
            getter = getattr(self.runtime.model, "get_provider", None)
            if callable(getter):
                return str(getter() or "")
        except Exception:
            pass
        return str(getattr(self.runtime.model, "provider", "") or "")

    def collect_llm_artifacts(
            self,
            llm=None,
            worker: Optional[WorkerState] = None,
            response: Any = None,
            actor_id: Optional[str] = None,
    ):
        """Collect provider-native URLs from both adapter buffers and raw events.

        Hosted/provider-side tools do not run through local PyGPT plugin CtxItems.
        LlamaIndex does, however, expose provider metadata on AgentStream/AgentOutput
        events. Capture that metadata immediately and also drain the provider adapter
        buffer as a fallback/final safety net.
        """
        resolved_id = str(actor_id or getattr(worker, "id", "") or "orchestrator")
        if worker is None and resolved_id != "orchestrator":
            worker = self.runtime.workers.get(resolved_id)

        actor = worker if worker is not None else self.runtime.orchestrator_actor
        source_ctx = getattr(actor, "tool_ctx", None)
        if source_ctx is None:
            return []
        if llm is None:
            llm = self.runtime._actor_llms.get(resolved_id)

        urls = drain_llm_urls(
            source_ctx,
            llm,
            response=response,
            provider=self.runtime._provider_id(),
            on_error=self.runtime.window.core.debug.log,
        )
        if not urls:
            return []

        self.runtime.verbose.log(
            "REMOTE TOOL ARTIFACTS",
            {"urls": urls},
            actor=resolved_id,
        )
        self.runtime.collect_artifacts(source_ctx, worker)
        return urls

    def _stage_artifact(self, attr: str, value: Any, worker: Optional[WorkerState] = None) -> bool:
        """Stage one response artifact without mutating the visible chat item yet."""
        if self.runtime.context.ctx is None:
            return False
        try:
            key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        except Exception:
            key = repr(value)
        delivery_key = artifact_identity(attr, value)
        if key in self.runtime._artifact_seen[attr] or delivery_key in self.runtime._artifact_delivery_seen:
            return False
        self.runtime._artifact_seen[attr].add(key)
        self.runtime._artifact_delivery_seen.add(delivery_key)
        self.runtime._pending_artifacts[attr].append(value)
        if worker is not None:
            worker.artifacts[attr].append(value)
        self.runtime.verbose.log(
            "ARTIFACT STAGED",
            {"type": attr, "value": value},
            actor=getattr(worker, "id", "orchestrator") if worker is not None else "orchestrator",
        )
        return True

    # Backward-compatible internal name used by older tests/integrations.
    def _append_artifact(self, attr: str, value: Any, worker: Optional[WorkerState] = None) -> bool:
        return self._stage_artifact(attr, value, worker)

    def pending_artifacts(self) -> dict:
        """Return a detached snapshot for AGENT_V2_END delivery on the UI thread."""
        return {
            key: list(values or [])
            for key, values in self.runtime._pending_artifacts.items()
            if values
        }

    def register_delivery_files(
            self,
            files,
            worker: Optional[WorkerState] = None,
    ) -> list:
        """Stage only files explicitly selected for delivery to the user.

        Internal plugin contexts often populate ``ctx.files`` by parsing tool output.
        During code/project inspection that list may contain every file merely read,
        searched or mentioned. Those paths are runtime evidence, not response
        attachments. Delivery is therefore opt-in through Files I/O
        ``deliver_file_to_user`` and remains hidden until finalization.
        """
        exported = []
        for entry in files or []:
            if isinstance(entry, dict):
                path = str(entry.get("path") or "").strip()
            else:
                path = str(entry or "").strip()
            if not path:
                continue
            if self._stage_artifact("files", path, worker):
                exported.append(path)
        return exported

    def collect_artifacts(self, source_ctx: CtxItem, worker: Optional[WorkerState] = None):
        """Stage durable non-file artifacts for final response delivery.

        ``source_ctx.files`` is intentionally excluded. Generic tool/code output can
        auto-populate it with inspected source paths, which must stay internal. A file
        reaches the response only through ``register_delivery_files()`` after an
        explicit ``deliver_file_to_user`` action.
        """
        main = self.runtime.context.ctx
        if source_ctx is None or main is None or source_ctx is main:
            return
        # Raw plugin `results` are model-facing tool responses, not user artifacts.
        # Files are opt-in because discovery/read tools can enumerate hundreds of
        # paths. Images/URLs/attachments are also staged so none of these extras can
        # appear before the authoritative final response has fully streamed.
        for attr in ("images", "urls", "attachments"):
            for value in (getattr(source_ctx, attr, None) or []):
                self._stage_artifact(attr, value, worker)

    def _make_tool_ctx(self, actor_id: str) -> CtxItem:
        """Create an isolated plugin/tool context for an Agents v2 actor.

        PyGPT plugins are built around CtxItem and may set `reply`, `results`,
        `extra.tool_output`, etc.  Those fields must never mutate the main chat
        CtxItem, otherwise the legacy reply pipeline can schedule INPUT_SYSTEM
        and create another user-visible Agents v2 turn from a tool result.
        """
        parent = self.runtime.context.ctx
        ctx = CtxItem(MODE_AGENT_V2)
        ctx.meta = parent.meta if parent else None
        ctx.meta_id = getattr(parent, "meta_id", None)
        ctx.model = getattr(parent, "model", None)
        if parent is not None:
            ctx.images = list(parent.images or [])
            ctx.attachments = list(parent.attachments or [])
            ctx.additional_ctx = list(parent.additional_ctx or [])
            ctx.doc_ids = list(parent.doc_ids or [])
            ctx.hidden_input = parent.hidden_input
        ctx.agent_call = True
        ctx.async_disabled = False
        ctx.internal = True
        ctx.hidden = True
        ctx.current = False
        ctx.extra = {
            "agents_v2_actor": actor_id,
            "run_id": self.runtime.run_id,
            # Let normal PyGPT plugins use their own QRunnable workers. The agent
            # awaits the result through the Agents v2 completion bridge instead
            # of forcing the plugin to execute synchronously on the Qt GUI thread.
            "agents_v2_async_tool": True,
        }
        return ctx

    def _make_worker_ctx(self, worker_id: str) -> CtxItem:
        ctx = self.runtime._make_tool_ctx(worker_id)
        ctx.extra["agents_v2_worker"] = worker_id
        return ctx
