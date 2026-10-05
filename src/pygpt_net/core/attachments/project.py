#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.05 16:00:00                  #
# ================================================== #
"""Deliver project sources according to the receiving conversation's memory.

Source discovery/storage stays in attachments.context. This module owns delivery
fingerprints and model-facing history; all source text uses the global summarizer.
"""
import copy
import hashlib
import os
from dataclasses import dataclass, field

from pygpt_net.core.types import MODE_AGENT_LLAMA, MODE_AGENT_OPENAI, MODE_AGENT_V2, MODE_ASSISTANT


@dataclass
class ProjectDelivery:
    text: str = ""
    family: str = "runtime"
    sources: dict = field(default_factory=dict)
    state: str = ""

    @property
    def retained(self):
        return self.family != "runtime"


class ProjectContext:
    HISTORY_KEY = "project_context"

    def __init__(self, window):
        self.window = window

    def delivery_family(self, context):
        """Use protocol capabilities, rather than a model name, to select policy."""
        core = self.window.core
        if context.mode == MODE_AGENT_V2:
            return "agent-memory"  # v2 always restores its root-conversation memory
        if not core.config.get("use_context", False):
            return "runtime"
        if context.mode in (MODE_AGENT_LLAMA, MODE_AGENT_OPENAI):
            return "agent-memory"
        if context.mode == MODE_ASSISTANT:
            return "assistant-thread"
        model = context.model
        provider = getattr(model, "provider", "")
        if provider in ("openai", "azure_openai"):
            from pygpt_net.provider.api.openai.responses import Responses
            if Responses(self.window).is_enabled(model, context.mode, context.parent_mode,
                                                  context.is_expert_call, context.preset):
                return f"responses:{provider}:{model.id}"
        elif provider == "x_ai" and not str(model.id).startswith("grok-3"):
            llm = core.llm.get("x_ai")
            stored = llm.get_remote_tool_config("store_messages")
            from pygpt_net.utils import is_image
            has_images = any(is_image(str(getattr(item, "path", "") or "")) for item in context.attachments.values())
            if stored is not False and not has_images:
                return f"responses:{provider}:{model.id}"
        return "runtime"

    @staticmethod
    def fingerprint(item, path):
        try:
            stat = os.stat(path)
        except OSError:
            return None
        value = (item.get("uuid"), path, stat.st_mtime_ns, stat.st_size,
                 item.get("share_revision", 0))
        return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()

    @classmethod
    def strip_history_item(cls, item):
        """Copy only rows whose project block needs removal; never rewrite saved history."""
        extra = getattr(item, "extra", None)
        marker = extra.get(cls.HISTORY_KEY) if isinstance(extra, dict) else None
        if not isinstance(marker, dict):
            return item
        result = copy.copy(item)
        result.extra = dict(extra)
        result.extra.pop(cls.HISTORY_KEY, None)
        text = marker.get("text", "")
        if text:
            result.hidden_input = (getattr(item, "hidden_input", "") or "").replace(text, "").strip()
        return result

    def sanitize_history(self, history, meta, family):
        attachment = self.window.core.attachments.context
        active = {}
        if attachment.is_project_share_enabled(meta):
            for item in attachment.get_project_items(meta):
                if attachment.is_shared(item) and attachment.is_active(item) and item.get("type") in ("local_file", "url"):
                    active[item["uuid"]] = self.fingerprint(item, attachment.get_text_path(meta, item))
        result = []
        for row in history:
            extra = getattr(row, "extra", None)
            marker = extra.get(self.HISTORY_KEY) if isinstance(extra, dict) else None
            if isinstance(marker, dict) and (family == "runtime" or marker.get("family") != family
                    or any(active.get(uid) != stamp for uid, stamp in marker.get("sources", {}).items())):
                row = self.strip_history_item(row)
            result.append(row)
        return result

    @staticmethod
    def successful(row):
        extra = getattr(row, "extra", None)
        extra = extra if isinstance(extra, dict) else {}
        return bool(not getattr(row, "stopped", False) and not extra.get("response_interrupted")
                    and (getattr(row, "msg_id", None) or getattr(row, "output", None)
                         or extra.get("response_final") is True))

    def prepare(self, context):
        attachment = self.window.core.attachments.context
        meta = context.ctx.meta
        family = self.delivery_family(context)
        delivery = ProjectDelivery(family=family)
        available = []
        if attachment.is_project_share_enabled(meta):
            for item in attachment.get_project_items(meta):
                if not attachment.is_shared(item) or not attachment.is_active(item) or item.get("type") not in ("local_file", "url"):
                    continue
                path = attachment.get_text_path(meta, item)
                fingerprint = self.fingerprint(item, path)
                if fingerprint:
                    available.append((item, path, fingerprint))
        active = {item["uuid"]: fingerprint for item, _, fingerprint in available}
        delivery.state = hashlib.sha256(repr((family, sorted(active.items()))).encode("utf-8")).hexdigest()
        known = {}
        history = []
        changed = False
        for row in context.history:
            extra = getattr(row, "extra", None)
            marker = extra.get(self.HISTORY_KEY) if isinstance(extra, dict) else None
            if not isinstance(marker, dict):
                history.append(row)
                continue
            valid = (delivery.retained and marker.get("family") == family
                     and all(active.get(uid) == stamp for uid, stamp in marker.get("sources", {}).items()))
            if not valid:
                history.append(self.strip_history_item(row))
                changed = True
            else:
                history.append(row)
                # Failed/interrupted requests must not consume one-time delivery.
                if self.successful(row):
                    known.update(marker.get("sources", {}))
        context.history = history
        previous_state = next(((getattr(row, "extra", None) or {}).get("project_context_state")
                               for row in reversed(context.history) if self.successful(row)), None)
        if changed and previous_state != delivery.state:
            context.ctx.extra = dict(context.ctx.extra or {})
            context.ctx.extra["project_context_reset"] = True
            agents = getattr(self.window.core, "agents", None)
            clear = getattr(agents, "clear_session_memory", None)
            if callable(clear):
                clear(meta)
        # When local history is compacted, memory/server-chain replay may no
        # longer contain the original turn. Such sources need delivery again.
        core = self.window.core
        manager = getattr(core, "context_manager", None)
        getter = getattr(core.ctx, "get_history", None)
        if delivery.retained and callable(getter) and manager is not None:
            prior = [row for row in history if row is not context.ctx]
            last = prior[-1] if prior else None
            server_keeps_history = (family.startswith("responses:") and not changed
                and last is not None and getattr(last, "msg_id", None) and self.successful(last)
                and not manager.should_break_server_chain(prior, context.ctx))
            if not server_keeps_history:
                budget = core.summarizer.budget(context)
                used = (core.summarizer.count(context.prompt, context.model)
                        + core.summarizer.count(context.system_prompt, context.model) + budget.output)
                retained = getter(prior, context.model.id, context.mode,
                                  used, budget.window, ignore_first=False)
                retained_ids = {id(row) for row in retained}
                # get_history can expand/copy items; durable ids remain stable.
                durable_ids = {row.id for row in retained if getattr(row, "id", None)}
                known = {}
                for row in prior:
                    if id(row) in retained_ids or (getattr(row, "id", None) and row.id in durable_ids):
                        marker = (row.extra or {}).get(self.HISTORY_KEY)
                        if isinstance(marker, dict) and self.successful(row):
                            known.update(marker.get("sources", {}))
        current = attachment.current_ids(context.ctx)
        blocks = []
        for item, path, fingerprint in available:
            uid = item["uuid"]
            if delivery.retained and known.get(uid) == fingerprint:
                continue
            if uid in current:
                # Current uploads/explicit references already use the ordinary gateway.
                delivery.sources[uid] = fingerprint
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
            except (OSError, UnicodeError) as error:
                self.window.core.debug.log(error)
                continue
            if not text.strip():
                continue
            blocks.append(f"Source: {attachment.get_context_filename(item)}\n{text}")
            delivery.sources[uid] = fingerprint
            source = item.get("real_path") or item.get("path")
            collection = attachment.last_urls if item.get("type") == "url" else attachment.last_files
            if source and source not in collection:
                collection.append(source)
        if blocks:
            text = "Shared project attachments:\n\n" + "\n\n".join(blocks)
            delivery.text = self.window.core.summarizer.process(text, context, "project attachments")
        return delivery

    def record(self, ctx, delivery):
        """Keep one-time input with its owning turn, so server/memory replay can restore it."""
        if not delivery.retained:
            return
        ctx.extra = dict(ctx.extra or {})
        ctx.extra["project_context_state"] = delivery.state
        if not delivery.sources:
            return
        ctx.extra[self.HISTORY_KEY] = {"family": delivery.family, "sources": delivery.sources,
                                      "text": delivery.text}
        if delivery.text:
            ctx.hidden_input = "\n\n".join(filter(None, [ctx.hidden_input, delivery.text]))

    def retrieve(self, context):
        """Compatibility entry point: prepare without committing delivery history."""
        return self.prepare(context).text
