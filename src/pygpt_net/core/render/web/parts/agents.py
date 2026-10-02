#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""Runtime workflow statuses and agent display policy."""

import json
from dataclasses import dataclass
import time
from typing import Optional
from pygpt_net.core.types import agent as agent_policy

from pygpt_net.core.types import MODE_AGENT_LLAMA
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.utils import trans
from .policy import SHOW_LEGACY_AGENT_NAME_PREFIX, WORKFLOW_SINGLE_STATUS_PER_PART_HISTORY_DEFAULT, WORKFLOW_SINGLE_STATUS_PER_PART_HISTORY_KEY, WORKFLOW_SINGLE_STATUS_PER_PART_LIVE_DEFAULT, WORKFLOW_SINGLE_STATUS_PER_PART_LIVE_KEY


@dataclass(frozen=True)
class WorkflowPresentation:
    """Display policy resolved once for a live or replayed assistant turn."""
    show_tool_chain: bool
    partial_timeline: list
    collapsed_workflow: Optional[dict]
    compact_final: Optional[dict]


class Agents:
    """Runtime workflow statuses and agent display policy.

    The renderer supplies session services and the shared session state.
    Collaborators are called explicitly through their component APIs.
    """

    # ========================================
    # Initialization
    # ========================================

    def __init__(self, renderer):
        self.renderer = renderer
        self.state = renderer.state

    # ========================================
    # Workflows
    # ========================================

    def build_presentation(self, ctx: CtxItem, *, rebuild=False, is_latest_ctx=False) -> WorkflowPresentation:
        """Resolve timeline, status replay and compact-final policy together."""
        # output
        # Runtime statuses are not persisted assistant content. During a history
        # rebuild they may be replayed only for the newest unfinished turn that
        # already owns textual model output. Therefore status-only turns collapse
        # back to the user message, while persisted tools/extras keep their normal
        # rendering semantics. Live rendering remains unchanged.
        runtime_status_records = self.workflow_status_records(ctx)
        replay_statuses = (
            True
            if not rebuild
            else self._should_replay_workflow_statuses(ctx, is_latest_ctx)
        )
        # Workflow statuses are intentionally runtime-only. A completed Agents v2
        # turn normally hides them during a history rebuild, but immediately after
        # finalization the current renderer still owns their in-memory timeline.
        # Preserve that timeline in the just-completed accordion without persisting
        # it. A fresh history load has no records here, so old completed turns keep
        # the previous final-only behavior.
        if (rebuild
                and CtxItem.uses_agent_timeline(ctx)
                and self.ctx_has_final_answer(ctx)
                and runtime_status_records):
            replay_statuses = True

        if CtxItem.uses_agent_timeline(ctx) and runtime_status_records:
            replay_statuses = True
        show_tool_chain = self.renderer.tools.show_tool_chain_for_ctx(ctx)
        completed_agents_v2_output = None
        if (CtxItem.uses_agent_timeline(ctx)
                and (rebuild or self.ctx_has_final_answer(ctx))):
            # Support both a full context rebuild and the direct runtime render
            # path used right after the final response has been committed.
            completed_agents_v2_output = ctx.get_agents_v2_response_output()

        full_workflow = self.display_full_agent_workflow_for_ctx(ctx)
        timeline_kwargs = dict(
            include_workflow_statuses=replay_statuses,
            include_tool_calls=show_tool_chain,
            compact_workflow_statuses=bool(
                replay_statuses
                and (
                    self._workflow_single_status_history()
                    if rebuild
                    else self.workflow_single_status_live()
                )
            ),
        )
        collapsed_workflow = None
        compact_agents_v2_final = None
        if completed_agents_v2_output is not None and not full_workflow:
            final_part_key = self._agent_v2_final_part_key(ctx)
            workflow_timeline = self.renderer.timeline.build_partial_timeline(
                ctx,
                final_only_text=False,
                final_output_text=completed_agents_v2_output,
                **timeline_kwargs,
            )
            workflow_timeline = self.agent_v2_timeline_without_final_text(
                ctx,
                workflow_timeline,
            )
            workflow_step_count = self.agent_v2_collapsed_workflow_step_count(
                workflow_timeline
            )
            # ``agents_v2_compact_final`` is an instruction to the incremental
            # frontend that there is *pre-final workflow DOM to fold away*.  Do
            # not emit it for a plain one-shot final response.  Previously every
            # completed Agents v2 turn carried this marker, so the JS collapse
            # path could run even when the final response was the only timeline
            # segment.
            if workflow_step_count > 0:
                # A plain one-shot answer produces zero pre-final workflow
                # segments. Anything above zero means there was real visible work
                # before the authoritative final response (partial/status/tool),
                # even if it was only one step. Keep that work reachable through
                # the Processed accordion instead of deleting it as a supposedly
                # trivial single response.
                compact_agents_v2_final = {
                    "final_part_id": final_part_key,
                    "workflow_steps": workflow_step_count,
                }
                collapsed_workflow = {
                    "label": self._format_agent_v2_processing_label(ctx),
                    "expanded": False,
                    "timeline": workflow_timeline,
                    # Runtime finalization uses this key to preserve the exact
                    # streamed final DOM node while collapsing all preceding
                    # workflow partials around it.
                    "final_part_id": final_part_key,
                }
            # Keep the authoritative final answer as the normal message body.
            # The preceding workflow is carried separately and starts collapsed.
            partial_timeline = []
        else:
            partial_timeline = self.renderer.timeline.build_partial_timeline(
                ctx,
                final_only_text=False,
                final_output_text=completed_agents_v2_output,
                **timeline_kwargs,
            )

        return WorkflowPresentation(
            show_tool_chain=show_tool_chain,
            partial_timeline=partial_timeline,
            collapsed_workflow=collapsed_workflow,
            compact_final=compact_agents_v2_final,
        )

    def display_full_agent_workflow_for_ctx(self, ctx: CtxItem) -> bool:
        """Return whether completed Chat with Agents partials stay visible.

        This is a UI-only preference. It does not change durable partial storage
        or the separate model-facing history replay policy.
        """
        if not CtxItem.uses_agent_timeline(ctx):
            return False
        return bool(self.renderer.window.core.config.get("agent.v2.display_full_workflow", True))

    def ctx_has_final_answer(self, ctx: Optional[CtxItem]) -> bool:
        """Return True when the durable turn is known to have completed."""
        if ctx is None:
            return False

        try:
            final = ctx.get_agents_v2_final_output()
        except Exception:
            final = None
        if self._has_text_payload(final):
            return True

        extra = getattr(ctx, "extra", None)
        if isinstance(extra, dict) and extra.get("response_final") is True:
            return True

        if getattr(ctx, "use_agent_final_response", False) \
                and self._has_text_payload(getattr(ctx, "agent_final_response", None)):
            return True
        return False

    def agent_v2_final_begin(self, meta: CtxMeta, ctx: CtxItem):
        """Reset only the live stream before the final chronological segment."""
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return
        # Discard Python-side chunks from the working phase before clearing the
        # DOM; otherwise a delayed micro-batch timer could re-append stale prose.
        self.renderer.streaming.stream_reset(pid)
        self.renderer.streaming.partial_stream_reset(pid)
        self.state.loading_visible[pid] = False
        self.state.loading_reserved[pid] = False
        pctx = self.state.pids[pid]
        pctx.item = ctx
        try:
            pctx.header = self.renderer.messages.get_name_header(ctx, stream=True)
        except Exception:
            pctx.header = ""
        try:
            node = self.renderer.get_output_node(meta)
            page = node.page()
            # Use the same QWebChannel chunk path as streamed text so the final
            # reset is ordered strictly before subsequent final-answer chunks.
            # The JS handler keeps the materialized workflow node and clears only
            # transient stream/status containers.
            page.bridge.chunk.emit("", str(getattr(ctx, "id", None) or ""), "final_reset")
        except Exception:
            try:
                self.renderer.get_output_node(meta).page().runJavaScript(
                    "if (typeof window.clearAgentWorking !== 'undefined') window.clearAgentWorking();"
                    "if (typeof window.clearAgentStatus !== 'undefined') window.clearAgentStatus();"
                    "if (typeof window.clearStream !== 'undefined') window.clearStream();"
                )
            except Exception:
                pass
        self.renderer.view.update_names(meta, ctx)

    @staticmethod
    def agent_v2_timeline_without_final_text(ctx: CtxItem, timeline: list) -> list:
        """Remove only the authoritative final prose from a workflow timeline."""
        final_uuid = ""
        final_id = None
        for part in reversed(list(getattr(ctx, "parts", None) or [])):
            part_extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if part_extra.get("agents_v2_final") is True:
                final_uuid = str(getattr(part, "uuid", "") or "")
                final_id = getattr(part, "id", None)
                break
        if not final_uuid and final_id is None:
            return []

        out = []
        for segment in list(timeline or []):
            item = dict(segment)
            is_final = bool(final_uuid and str(item.get("part_uuid") or "") == final_uuid)
            if not is_final and final_id is not None:
                is_final = item.get("part_id") == final_id
            if is_final and item.get("text"):
                item["text"] = ""
            if (item.get("text") or item.get("tool_calls")
                    or item.get("status_id") or item.get("status_kind")):
                out.append(item)
        return out

    @staticmethod
    def agent_v2_collapsed_workflow_step_count(timeline: list) -> int:
        """Count meaningful pre-final workflow segments for the collapsed UI.

        Runtime worker progress is represented by workflow-status/tool segments
        attached to the durable parent rather than by worker-owned partial rows.
        Counting only orchestrator CtxItemPart objects therefore hid the
        ``Processed for...`` accordion whenever the visible work happened in a
        worker. Count the rendered chronological segments instead.
        """
        count = 0
        for segment in list(timeline or []):
            if not isinstance(segment, dict):
                continue
            calls = list(segment.get("tool_calls") or [])
            if calls:
                count += max(1, len(calls))
                continue
            if (segment.get("text")
                    or segment.get("status_id")
                    or segment.get("status_kind")
                    or segment.get("inline_message")):
                count += 1
        return count

    # ========================================
    # Status
    # ========================================

    def agent_status(self, meta: CtxMeta, ctx: CtxItem, status: str, owner=None):
        """Append a live agent status inside the current durable turn."""
        value_text = str(status or "").strip()
        if not value_text:
            self.agent_status_clear(meta, ctx)
            return
        _key, _pid, resolved_ctx = self.workflow_status_key(meta, ctx)
        if resolved_ctx is None:
            resolved_ctx = ctx
        if CtxItem.uses_agent_timeline(resolved_ctx) and not owner:
            # Plugin progress arrives directly through RenderEvent, outside the
            # runtime emitter. Keep it in the same durable partial status slot.
            part = resolved_ctx.get_active_part()
            if part is not None:
                part.extra = dict(part.extra or {})
                progress = dict(part.extra.get("agents_v2_progress") or {})
                progress["text"] = value_text
                part.extra["agents_v2_progress"] = progress
                self.renderer.window.core.ctx.update_part(resolved_ctx, part, sync_item=False)
                owner = {"part_uuid": str(part.uuid), "progress": progress}
        if CtxItem.uses_agent_timeline(resolved_ctx) and owner and owner.get("progress"):
            part = next((p for p in resolved_ctx.parts or [] if str(p.uuid) == owner.get("part_uuid")), None)
            if part is not None:
                # The queued event owns its status snapshot. Runtime/renderer
                # partial objects can already contain a newer or stale label.
                part.extra = dict(part.extra or {})
                part.extra["agents_v2_progress"] = dict(owner["progress"])
                self.renderer.window.core.ctx.update_part(resolved_ctx, part, sync_item=False)
            record = next((r for r in self.progress_records(resolved_ctx) if r["part_uuid"] == owner.get("part_uuid")), None)
            if record:
                value_text = str(owner["progress"].get("text") or value_text)
                owner = {**owner, "hierarchy": record["hierarchy"]}
        else:
            record = None
        self.update_agent_working(meta, resolved_ctx)
        status_id = self.workflow_status_add(
            meta, resolved_ctx, kind="agent", text=value_text, owner=owner,
        )
        if record:
            status_id = record["id"]
        try:
            value = json.dumps(value_text, ensure_ascii=False)
            parent_id = json.dumps(
                str(getattr(resolved_ctx, "id", "") or ""), ensure_ascii=False
            )
            sid = json.dumps(str(status_id or ""), ensure_ascii=False)
            self.renderer.get_output_node(meta).page().runJavaScript(
                "if (typeof window.setAgentStatus !== 'undefined') "
                f"window.setAgentStatus({value}, {parent_id}, {sid}, {json.dumps(owner, ensure_ascii=False)});"
            )
        except Exception:
            pass

    def agent_status_clear(self, meta: CtxMeta, ctx: CtxItem):
        """Freeze the active status; historical workflow rows stay visible."""
        _key, _pid, resolved_ctx = self.workflow_status_key(meta, ctx)
        if resolved_ctx is None:
            resolved_ctx = ctx
        self.workflow_status_freeze(meta, resolved_ctx)
        try:
            parent_id = json.dumps(
                str(getattr(resolved_ctx, "id", "") or ""), ensure_ascii=False
            )
            self.renderer.get_output_node(meta).page().runJavaScript(
                "if (typeof window.freezeWorkflowStatus !== 'undefined') "
                f"window.freezeWorkflowStatus({parent_id});"
            )
        except Exception:
            pass

    def agent_working_payload(self, ctx: CtxItem, tool_started: bool = False):
        """Describe real multi-step work, never a one-shot agent answer."""
        if ctx is None or not CtxItem.uses_agent_timeline(ctx):
            return None
        extra = ctx.extra if isinstance(ctx.extra, dict) else {}
        parts = list(ctx.parts or [])
        if (ctx.stopped or extra.get("response_final") or extra.get("response_interrupted")
                or any((part.extra or {}).get("agents_v2_final") for part in parts)):
            return None
        if not (tool_started or len(parts) > 1 or any(part.tasks for part in parts)):
            return None
        return {
            "started": float(ctx.input_timestamp or time.time()),
            "label": trans("ctx.agent.workflow.working"),
            "units": [trans("ctx.agent.workflow.time.hour"),
                      trans("ctx.agent.workflow.time.minute"),
                      trans("ctx.agent.workflow.time.second")],
        }

    def update_agent_working(self, meta: CtxMeta, ctx: CtxItem, tool_started: bool = False):
        payload = self.agent_working_payload(ctx, tool_started)
        if payload is None:
            return
        parent = json.dumps(str(ctx.id or ""))
        data = json.dumps(payload, ensure_ascii=False)
        self.renderer.get_output_node(meta).page().runJavaScript(
            "if (typeof window.setAgentWorking !== 'undefined') "
            f"window.setAgentWorking({parent}, {data});"
        )

    # ========================================
    # Workflow status records
    # ========================================

    def workflow_status_key(self, meta: CtxMeta, ctx: Optional[CtxItem] = None):
        pid, ctx = self._workflow_status_ctx(meta, ctx)
        parent_id = getattr(ctx, "id", None) if ctx is not None else None
        if pid is None or parent_id is None:
            return None, pid, ctx
        return (pid, str(parent_id)), pid, ctx

    def workflow_status_add(
            self,
            meta: CtxMeta,
            ctx: Optional[CtxItem],
            *,
            kind: str,
            text: str = "",
            tool_names: Optional[list] = None,
            aggregate: bool = False,
            owner: Optional[dict] = None,
    ) -> Optional[str]:
        """Append one UI-only workflow event in strict display order.

        The record stores whether it happened before or after the currently
        active partial. This matters when a status is emitted before the first
        model token: once that partial later receives text, the status still
        has to stay above that text after a full WebView reload.
        """
        key, _pid, ctx = self.workflow_status_key(meta, ctx)
        if key is None or ctx is None:
            return None

        records = self.state.workflow_statuses.setdefault(key, [])
        names = [str(name) for name in (tool_names or []) if str(name)]
        value = str(text or "")
        part = ctx.get_active_part() if hasattr(ctx, "get_active_part") else None
        if owner and owner.get("part_uuid"):
            part = next((p for p in ctx.parts if str(p.uuid) == str(owner["part_uuid"])), None)
        part_uuid = str(getattr(part, "uuid", "") or "") or None
        if part is None:
            placement = "head"
        else:
            has_payload = bool(str(getattr(part, "output", None) or "").strip()) \
                or bool(getattr(part, "tasks", None))
            placement = "after" if has_payload else "before"

        if owner and owner.get("placement") in {"before", "after"}:
            placement = owner["placement"]

        current_bucket = ("part", part_uuid) if part_uuid else ("head", "")

        # Compact tool-status mode keeps one row for the whole durable turn.
        # Re-activate and move that row to the newest chronological position
        # instead of appending a new status after every tool execution.
        if aggregate:
            aggregate_record = next(
                (record for record in reversed(records) if record.get("kind") == kind),
                None,
            )
            if aggregate_record is not None:
                for record in records:
                    if record.get("active"):
                        record["active"] = False
                self.state.workflow_status_seq += 1
                aggregate_record.update({
                    "text": value,
                    "tool_names": names,
                    "part_uuid": part_uuid,
                    "placement": placement,
                    "after_part_uuid": part_uuid if placement == "after" else None,
                    "active": True,
                    "seq": self.state.workflow_status_seq,
                })
                self.renderer.loading.hide_loading_on_activity(meta, pid=_pid)
                return str(
                    aggregate_record.get("live_id")
                    or aggregate_record.get("id")
                    or ""
                ) or None

        # Repeated updates of the currently active row are idempotent.
        if records:
            last = records[-1]
            if (last.get("active")
                    and last.get("kind") == kind
                    and str(last.get("text") or "") == value
                    and list(last.get("tool_names") or []) == names
                    and self._workflow_status_part_key(last) == current_bucket):
                self.renderer.loading.hide_loading_on_activity(meta, pid=_pid)
                if self.workflow_single_status_live():
                    return str(last.get("live_id") or last.get("id") or "") or None
                return str(last.get("id") or "") or None

        # Only the newest row shimmers. Historical rows remain visible.
        for record in records:
            if record.get("active"):
                record["active"] = False

        self.state.workflow_status_seq += 1
        status_id = f"wf-{key[0]}-{key[1]}-{self.state.workflow_status_seq}"
        live_id = status_id
        if self.workflow_single_status_live():
            # Keep the complete event history in Python so the history/reload
            # policy can still be toggled independently. Only the live DOM slot
            # is reused per part via ``live_id``.
            for record in reversed(records):
                if self._workflow_status_part_key(record) == current_bucket:
                    live_id = str(record.get("live_id") or record.get("id") or status_id)
                    break
        records.append({
            "id": status_id,
            "live_id": live_id,
            "kind": str(kind or "agent"),
            "agent_name": str((owner or {}).get("agent_name") or ""),
            "text": value,
            "tool_names": names,
            "part_uuid": part_uuid,
            "placement": placement,
            # Backward-compatible field for code that may inspect old records.
            "after_part_uuid": part_uuid if placement == "after" else None,
            "active": True,
            "seq": self.state.workflow_status_seq,
        })
        self.renderer.loading.hide_loading_on_activity(meta, pid=_pid)
        return live_id if self.workflow_single_status_live() else status_id

    def workflow_status_freeze(
            self,
            meta: CtxMeta,
            ctx: Optional[CtxItem] = None,
            kind: Optional[str] = None,
    ) -> None:
        """Deactivate current status rows but never remove timeline history."""
        key, _pid, _ctx = self.workflow_status_key(meta, ctx)
        if key is None:
            return
        for record in self.state.workflow_statuses.get(key, []):
            if kind is None or record.get("kind") == kind:
                record["active"] = False

    def workflow_status_remove(
            self,
            meta: CtxMeta,
            ctx: Optional[CtxItem] = None,
            kind: Optional[str] = None,
    ) -> None:
        """Remove transient workflow rows from runtime history.

        Tool waiting rows are only placeholders until the durable Tool/Tools
        block becomes UI-ready. Keeping them after TOOL_CLEAR allows a later
        partial/reload of the same CtxItem to replay a stale ``Tool: ...`` row
        between already materialized message segments.
        """
        key, _pid, _ctx = self.workflow_status_key(meta, ctx)
        if key is None:
            return
        records = self.state.workflow_statuses.get(key)
        if not records:
            return
        if kind is None:
            self.state.workflow_statuses.pop(key, None)
            return
        kept = [record for record in records if record.get("kind") != kind]
        if kept:
            self.state.workflow_statuses[key] = kept
        else:
            self.state.workflow_statuses.pop(key, None)

    def progress_records(self, ctx):
        records = []
        for index, part in enumerate(ctx.parts or []):
            progress = (part.extra or {}).get("agents_v2_progress")
            if not isinstance(progress, dict):
                continue
            calls = []
            swarm = progress.get("swarm") is True
            workers = {key: dict(value, calls=[]) for key, value in (progress.get("workers") or {}).items()}
            raw = ctx.get_part_tool_calls(visible_only=False, part=part) if agent_policy.AGENTS_V2_TOOL_CALLS_ENABLED else []
            for task in (part.tasks or []) if agent_policy.AGENTS_V2_TOOL_CALLS_ENABLED else []:
                name = (task.extra or {}).get("tool_name") or task.task_name
                if not name or self.renderer.window.core.command.is_tool_hidden(name):
                    continue
                normalized = self.renderer.helpers.extract_extra_tool_calls([
                    call for call in raw if call.get("call_id") == (task.tool_call_id or task.uuid)
                ])
                actor = str(task.agent_id or "orchestrator")
                if actor == "orchestrator" or not swarm:
                    calls.extend(normalized)
                else:
                    worker = workers.setdefault(actor, {"id": actor, "name": (task.extra or {}).get("agent_name") or actor, "text": "", "calls": []})
                    worker["calls"].extend(normalized)
            label = progress.get("text")
            if not label or label == "Tools":
                label = trans("status.agent_v2.thinking")
            records.append({
                "id": "progress-" + str(part.uuid), "kind": "agent",
                "part_uuid": str(part.uuid), "placement": "after", "seq": index,
                "text": label, "active": False,
                "hierarchy": ({"calls": calls, "workers": list(workers.values()) if swarm else [],
                               "group_tools": agent_policy.AGENTS_V2_GROUP_TOOL_CALLS}
                              if agent_policy.AGENTS_V2_TOOL_CALLS_ENABLED else None),
            })
        return records

    def workflow_status_records(
            self,
            ctx: CtxItem,
            compact: bool = False,
            live_ids: bool = False,
    ) -> list[dict]:
        meta = getattr(ctx, "meta", None)
        key, _pid, _ctx = self.workflow_status_key(meta, ctx) if meta is not None else (None, None, ctx)
        if CtxItem.uses_agent_timeline(ctx):
            return self.progress_records(ctx)
        if key is None:
            return []
        records = [dict(record) for record in self.state.workflow_statuses.get(key, [])]
        if compact:
            records = self._compact_workflow_status_records(records)
        if live_ids:
            for record in records:
                record["id"] = str(record.get("live_id") or record.get("id") or "")
        return records

    def workflow_status_drop_pid(self, pid: Optional[int]) -> None:
        if pid is None:
            return
        for key in list(self.state.workflow_statuses):
            if key and key[0] == pid:
                self.state.workflow_statuses.pop(key, None)

    def workflow_single_status_live(self) -> bool:
        """Return current live single-status policy from Settings."""
        return bool(self.renderer.window.core.config.get(
            WORKFLOW_SINGLE_STATUS_PER_PART_LIVE_KEY,
            WORKFLOW_SINGLE_STATUS_PER_PART_LIVE_DEFAULT,
        ))

    # ========================================
    # Agent identity
    # ========================================

    def legacy_agent_name_prefix(
            self,
            ctx: Optional[CtxItem],
            part=None,
            part_key: Optional[object] = None,
            prefer_final: bool = False,
    ) -> str:
        """Return a UI-only actor label for one legacy LlamaIndex partial."""
        if (not SHOW_LEGACY_AGENT_NAME_PREFIX
                or ctx is None
                or str(getattr(ctx, "mode", "") or "") != MODE_AGENT_LLAMA):
            return ""

        parts = list(getattr(ctx, "parts", None) or [])
        if part is None and part_key not in (None, ""):
            wanted = str(part_key)
            for candidate in parts:
                if (str(getattr(candidate, "uuid", "") or "") == wanted
                        or str(getattr(candidate, "id", "") or "") == wanted):
                    part = candidate
                    break

        if part is None and prefer_final:
            for candidate in reversed(parts):
                extra = candidate.extra if isinstance(getattr(candidate, "extra", None), dict) else {}
                if extra.get("agents_v2_final") is True:
                    part = candidate
                    break

        if part is None and parts:
            part = parts[-1]
        if part is None:
            try:
                part = ctx.get_active_part()
            except Exception:
                part = None

        return str(getattr(part, "name", "") or "").strip() if part is not None else ""

    # ========================================
    # Private: status context and compaction
    # ========================================

    def _workflow_status_ctx(self, meta: CtxMeta, ctx: Optional[CtxItem] = None):
        """Resolve the durable turn used by a live workflow status.

        Tool feedback can use an ephemeral provider continuation. UI status rows
        must always attach to its durable parent item, never to that temporary
        continuation (which has no stable msg-box in the WebView).
        """
        if meta is None and ctx is not None:
            meta = getattr(ctx, "meta", None)
        if meta is None:
            return None, ctx
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return None, ctx
        if ctx is None and pid in self.state.pids:
            ctx = self.state.pids[pid].item
        parent = getattr(ctx, "turn_parent", None) if ctx is not None else None
        if parent is not None:
            ctx = parent
        return pid, ctx

    def _workflow_single_status_history(self) -> bool:
        """Return current unfinished-history single-status policy from Settings."""
        return bool(self.renderer.window.core.config.get(
            WORKFLOW_SINGLE_STATUS_PER_PART_HISTORY_KEY,
            WORKFLOW_SINGLE_STATUS_PER_PART_HISTORY_DEFAULT,
        ))

    @staticmethod
    def _workflow_status_part_key(record: dict) -> tuple:
        """Return the logical part bucket used by single-status rendering."""
        part_uuid = str(record.get("part_uuid") or record.get("after_part_uuid") or "")
        if part_uuid:
            return ("part", part_uuid)
        # All statuses emitted before the first durable part belong to the one
        # turn-head slot and should update that slot instead of accumulating.
        return ("head", "")

    @classmethod
    def _compact_workflow_status_records(cls, records: list[dict]) -> list[dict]:
        """Keep only the newest workflow status for every logical part."""
        latest = {}
        for record in records:
            bucket = cls._workflow_status_part_key(record)
            previous = latest.get(bucket)
            if previous is None or int(record.get("seq", 0) or 0) >= int(previous.get("seq", 0) or 0):
                latest[bucket] = record
        return sorted(
            (dict(record) for record in latest.values()),
            key=lambda record: int(record.get("seq", 0) or 0),
        )

    # ========================================
    # Private: workflow replay and final response
    # ========================================

    def _has_text_payload(self, value: object) -> bool:
        """Return True only for user-visible assistant prose.

        Tool protocol markup is not textual output. This distinction is used
        only when rebuilding a persisted/history view; live tool/status rows are
        still rendered immediately while the turn is running.
        """
        if value is None:
            return False
        text = str(value)
        if not text.strip():
            return False
        try:
            text = self.renderer.helpers.strip_tool_calls(text)
        except Exception:
            pass
        return bool(str(text or "").strip())

    def _ctx_has_textual_output(self, ctx: Optional[CtxItem]) -> bool:
        """Check the durable item and its visible partials for assistant prose."""
        if ctx is None or getattr(ctx, "hidden", False):
            return False

        # When partials exist they are the structural source of truth. Do not let
        # the compatibility ctx.output cache make a hidden worker-only partial
        # look like visible assistant prose.
        parts = list(getattr(ctx, "parts", None) or [])
        if parts:
            for part in parts:
                part_extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
                if part_extra.get("agents_v2_worker") is True or part_extra.get("ui_visible") is False:
                    continue
                if self._has_text_payload(getattr(part, "output", None)):
                    return True
        elif self._has_text_payload(getattr(ctx, "output", None)):
            return True

        extra = getattr(ctx, "extra", None)
        if isinstance(extra, dict) and self._has_text_payload(extra.get("output")):
            return True

        if self._has_text_payload(getattr(ctx, "agent_final_response", None)):
            return True
        return False

    def _should_replay_workflow_statuses(
            self,
            ctx: Optional[CtxItem],
            is_latest_ctx: bool,
    ) -> bool:
        """Replay transient statuses only for the newest unfinished turn."""
        return bool(
            is_latest_ctx
            and not self.ctx_has_final_answer(ctx)
            and (
                self._ctx_has_textual_output(ctx)
                or bool(self.workflow_status_records(ctx))
            )
        )

    @staticmethod
    def _agent_v2_final_part_key(ctx: CtxItem) -> str:
        """Return the durable key of the authoritative final partial."""
        for part in reversed(list(getattr(ctx, "parts", None) or [])):
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("agents_v2_final") is not True:
                continue
            value = str(getattr(part, "uuid", "") or "")
            if value:
                return value
            part_id = getattr(part, "id", None)
            if part_id is not None:
                return str(part_id)
        return ""

    # ========================================
    # Private: processing time
    # ========================================

    def _agent_v2_processing_seconds(self, ctx: CtxItem) -> Optional[int]:
        """Return stable Agents v2 processing time in whole seconds.

        New turns persist the duration in ``ctx.extra``. For already stored turns,
        derive it from the user input timestamp and the durable final partial's
        last update timestamp, both of which are already stored in the database.
        """
        extra = ctx.extra if isinstance(getattr(ctx, "extra", None), dict) else {}
        stored = extra.get("agents_v2_processing_seconds")
        if stored is not None:
            try:
                return max(0, int(stored))
            except (TypeError, ValueError):
                pass

        final_part = None
        for part in reversed(list(getattr(ctx, "parts", None) or [])):
            part_extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if part_extra.get("agents_v2_final") is True:
                final_part = part
                break
        if final_part is None:
            return None

        try:
            started_at = int(getattr(ctx, "input_timestamp", None) or 0)
        except (TypeError, ValueError):
            started_at = 0
        if started_at <= 0:
            starts = []
            for part in list(getattr(ctx, "parts", None) or []):
                try:
                    value = int(getattr(part, "created_at", None) or 0)
                except (TypeError, ValueError):
                    value = 0
                if value > 0:
                    starts.append(value)
            started_at = min(starts) if starts else 0

        try:
            finished_at = int(getattr(final_part, "updated_at", None) or 0)
        except (TypeError, ValueError):
            finished_at = 0
        if started_at <= 0 or finished_at < started_at:
            return None
        return finished_at - started_at

    def _format_agent_v2_processing_label(self, ctx: CtxItem) -> str:
        """Build the localized collapsed-workflow label."""
        seconds = self._agent_v2_processing_seconds(ctx)
        if seconds is None:
            return trans("ctx.agent.workflow.processed.no_time")

        remaining = max(0, int(seconds))
        hours, remaining = divmod(remaining, 3600)
        minutes, secs = divmod(remaining, 60)
        values = []
        if hours:
            values.append(f"{hours}{trans('ctx.agent.workflow.time.hour')}")
        if minutes:
            values.append(f"{minutes}{trans('ctx.agent.workflow.time.minute')}")
        if secs or not values:
            values.append(f"{secs}{trans('ctx.agent.workflow.time.second')}")
        duration = " ".join(values)
        return trans("ctx.agent.workflow.processed").replace("{duration}", duration)
