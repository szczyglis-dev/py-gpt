#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

import json
from typing import Any, Optional

from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.llms.artifacts import drain_llm_urls

from .state import WorkerState


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

    def collect_artifacts(self, source_ctx: CtxItem, worker: Optional[WorkerState] = None):
        """Merge worker artifacts into the user-visible context and worker status payload."""
        main = self.runtime.context.ctx
        if source_ctx is None or main is None or source_ctx is main:
            return
        # Raw plugin `results` are model-facing tool responses, not user artifacts.
        # Propagating them into the main CtxItem can make the regular renderer treat
        # an Agents v2 turn like a legacy tool-reply chain. Only durable artifacts
        # are exported to the user-visible context.
        for attr in ("files", "images", "urls", "attachments"):
            values = getattr(source_ctx, attr, None) or []
            target = getattr(main, attr, None)
            if target is None:
                target = []
                setattr(main, attr, target)
            for value in values:
                try:
                    key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                except Exception:
                    key = repr(value)
                if key in self.runtime._artifact_seen[attr]:
                    continue
                self.runtime._artifact_seen[attr].add(key)
                target.append(value)
                if worker is not None:
                    worker.artifacts[attr].append(value)
                self.runtime.verbose.log("ARTIFACT", {"type": attr, "value": value}, actor=getattr(worker, "id", "orchestrator") if worker is not None else "orchestrator")
        try:
            self.runtime.window.core.ctx.update_item(main)
        except Exception:
            pass

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
