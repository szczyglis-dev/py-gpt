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

"""Chronological assembly of partial text, tools and workflow statuses."""

from typing import Optional
from pygpt_net.item.ctx import CtxItem


class Timeline:
    """Chronological assembly of partial text, tools and workflow statuses.

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
    # Chronological timeline
    # ========================================

    def build_partial_timeline(
            self,
            ctx: CtxItem,
            include_workflow_statuses: bool = True,
            include_tool_calls: bool = True,
            final_only_text: bool = False,
            final_output_text: Optional[str] = None,
            compact_workflow_statuses: bool = False,
    ) -> list:
        """Build one chronological timeline for a durable assistant turn.

        Structured/legacy tool calls are included only when ``include_tool_calls``
        is true. Runtime-only workflow statuses are included only when requested by
        the history/reload policy. For a completed Agents v2 history rebuild,
        ``final_only_text`` suppresses working orchestrator prose while preserving
        the optional structured tool chain; the authoritative final response is
        rendered once at its final partial (or at the tail for legacy rows).
        Footer/actions are intentionally rendered after the whole timeline.
        """
        workflow_statuses = sorted(
            self.renderer.agents.workflow_status_records(
                ctx,
                compact=compact_workflow_statuses,
            ) if include_workflow_statuses else [],
            key=lambda record: int(record.get("seq", 0) or 0),
        )

        all_parts = []
        for part in list(getattr(ctx, "parts", None) or []):
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("agents_v2_worker") is True or extra.get("ui_visible") is False:
                continue
            all_parts.append(part)

        anchored_uuids = {
            str(record.get("part_uuid") or record.get("after_part_uuid") or "")
            for record in workflow_statuses
            if str(record.get("part_uuid") or record.get("after_part_uuid") or "")
        }
        parts = []
        for part in all_parts:
            part_uuid = str(getattr(part, "uuid", "") or "")
            part_extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            visible_part_tools = bool(include_tool_calls) and bool(
                self.renderer.helpers.extract_extra_tool_calls(
                    ctx.get_part_tool_calls(visible_only=True, part=part)
                )
            )
            has_inline_messages = bool(self.renderer.get_inline_messages(part_extra))
            if (getattr(part, "output", None) not in (None, "")
                    or visible_part_tools
                    or has_inline_messages
                    or part_uuid in anchored_uuids):
                parts.append(part)

        if not parts and not workflow_statuses:
            return []

        has_visible_structured_tools = bool(include_tool_calls) and any(
            bool(self.renderer.helpers.extract_extra_tool_calls(
                ctx.get_part_tool_calls(visible_only=True, part=part)
            ))
            for part in parts
        )
        has_inline_messages = any(
            bool(self.renderer.get_inline_messages(
                part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            ))
            for part in parts
        )
        # A single plain text part needs no sub-timeline. Any status, tool, inline
        # message or multiple partials do, because relative ordering matters.
        if (len(parts) == 1 and not has_visible_structured_tools
                and not has_inline_messages and not workflow_statuses):
            return []

        timeline = []
        seq = 0
        base_id = getattr(ctx, "id", None)
        try:
            base_id = abs(int(base_id or 0)) + 1
        except (TypeError, ValueError):
            base_id = 1

        def append_segment(part, text="", tool_calls=None):
            nonlocal seq
            tool_calls = list(tool_calls or [])
            if not text and not tool_calls:
                return
            seq += 1
            md_text = ""
            if text:
                md_src = self.renderer.helpers.pre_format_text(str(text), ctx=ctx)
                md_text = self.renderer.helpers.post_format_text(md_src)
            timeline.append({
                "part_id": getattr(part, "id", None),
                "part_uuid": getattr(part, "uuid", None),
                "render_id": -(base_id * 10000 + seq),
                "text": md_text,
                "tool_calls": tool_calls,
                "agent_name_prefix": (
                    self.renderer.agents.legacy_agent_name_prefix(ctx, part=part) if text else ""
                ),
            })

        def append_status(record):
            nonlocal seq
            seq += 1
            timeline.append({
                "part_id": None,
                "part_uuid": None,
                "render_id": -(base_id * 10000 + seq),
                "text": "",
                "tool_calls": [],
                "status_id": str(record.get("id") or ""),
                "status_kind": str(record.get("kind") or "agent"),
                "status_text": str(record.get("text") or ""),
                "status_tool_names": list(record.get("tool_names") or []),
                "status_active": bool(record.get("active")),
                "status_live_tool_calls": list(record.get("live_tool_calls") or []) if include_tool_calls else [],
            })

        def append_inline_message(part, message):
            """Add one UI-only inline message associated with a durable partial."""
            nonlocal seq
            if not isinstance(message, dict):
                return
            value = str(message.get("text") or "").strip()
            if not value:
                return
            msg_type = str(message.get("type") or "message").strip() or "message"
            label = self.renderer.get_inline_message_label(msg_type)
            seq += 1
            timeline.append({
                "part_id": getattr(part, "id", None),
                "part_uuid": getattr(part, "uuid", None),
                "render_id": -(base_id * 10000 + seq),
                "text": value,
                "tool_calls": [],
                "inline_message": True,
                "inline_message_type": msg_type,
                "inline_message_label": label,
            })

        part_by_uuid = {
            str(getattr(part, "uuid", "") or ""): part
            for part in parts
            if str(getattr(part, "uuid", "") or "")
        }
        head_statuses = []
        before_by_part = {}
        after_by_part = {}
        tail_statuses = []

        for record in workflow_statuses:
            anchor = str(record.get("part_uuid") or record.get("after_part_uuid") or "")
            placement = str(record.get("placement") or ("after" if record.get("after_part_uuid") else "tail"))
            if placement == "head":
                head_statuses.append(record)
            elif anchor and anchor in part_by_uuid:
                target = before_by_part if placement == "before" else after_by_part
                target.setdefault(anchor, []).append(record)
            else:
                # Legacy/unanchored runtime records belong to this turn but have
                # no reliable partial boundary; retain arrival order at the tail.
                tail_statuses.append(record)

        for record in head_statuses:
            append_status(record)

        def visible_tool_names(part):
            if not include_tool_calls:
                return set()
            calls = self.renderer.helpers.extract_extra_tool_calls(
                ctx.get_part_tool_calls(visible_only=True, part=part)
            )
            return {
                str(call.get("name") or "")
                for call in calls
                if isinstance(call, dict) and call.get("name")
            }

        def append_part_statuses(records, part):
            names = visible_tool_names(part)
            for record in records:
                # A pending "Using tool" row is the temporary representation of
                # the real structured tool block. Once that block is UI-ready,
                # keep only the actual Tool/Tools accordion, not both copies.
                record_names = {str(name) for name in record.get("tool_names", []) if str(name)}
                if (record.get("kind") == "tool" and record_names
                        and record_names.issubset(names)):
                    continue
                append_status(record)

        final_text_emitted = False
        for part in parts:
            part_uuid = str(getattr(part, "uuid", "") or "")
            append_part_statuses(before_by_part.get(part_uuid, []), part)

            part_extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            for inline_message in self.renderer.get_inline_messages(part_extra):
                append_inline_message(part, inline_message)
            source_text = str(getattr(part, "output", None) or "")
            if final_only_text:
                if part_extra.get("agents_v2_final") is True:
                    raw_text = str(final_output_text if final_output_text is not None else source_text)
                    if raw_text.strip():
                        final_text_emitted = True
                else:
                    raw_text = ""
            else:
                raw_text = source_text
            try:
                text_after_round = int(part_extra.get("text_after_tool_round", 0) or 0)
            except (TypeError, ValueError):
                text_after_round = 0

            round_ids = set()
            if include_tool_calls:
                for task in getattr(part, "tasks", None) or []:
                    extra = task.extra if isinstance(getattr(task, "extra", None), dict) else {}
                    if not (task.tool_call_id or extra.get("tool_name")):
                        continue
                    if not task.is_ui_ready() or extra.get("ui_visible") is False:
                        continue
                    tool_name = str(extra.get("tool_name") or task.task_name or task.name or "tool")
                    if self.renderer.window.core.command.is_tool_hidden(tool_name):
                        continue
                    try:
                        round_ids.add(max(1, int(extra.get("tool_round") or 1)))
                    except (TypeError, ValueError):
                        round_ids.add(1)

            text_emitted = False
            if round_ids:
                # Structured tasks are authoritative; strip compatibility <tool>
                # tags so the request is never rendered twice.
                visible_text = self.renderer.helpers.strip_tool_calls(raw_text)
                for round_id in sorted(round_ids):
                    calls = self.renderer.helpers.extract_extra_tool_calls(
                        ctx.get_part_tool_calls(
                            visible_only=True,
                            part=part,
                            tool_round=round_id,
                        )
                    )
                    if visible_text and not text_emitted and round_id > text_after_round:
                        append_segment(part, text=visible_text)
                        text_emitted = True
                    append_segment(part, tool_calls=calls)
                if visible_text and not text_emitted:
                    append_segment(part, text=visible_text)
            else:
                # Strip persisted compatibility tags even when tool-chain display
                # is disabled, otherwise old Agents v2 turns could leak raw
                # <tool> payloads into the assistant text.
                legacy_calls = self.renderer.helpers.extract_tool_calls(source_text)
                visible_text = self.renderer.helpers.strip_tool_calls(raw_text)
                if visible_text:
                    append_segment(part, text=visible_text)
                if include_tool_calls and legacy_calls:
                    append_segment(part, tool_calls=legacy_calls)

            append_part_statuses(after_by_part.get(part_uuid, []), part)

        for record in tail_statuses:
            append_status(record)

        if final_only_text and not final_text_emitted and final_output_text:
            # Legacy completed rows may have only the compact parent final and no
            # explicitly marked final partial. Keep any requested tool chain, then
            # place that authoritative response once at the end of the timeline.
            anchor_part = parts[-1] if parts else None
            append_segment(anchor_part, text=str(final_output_text))

        return self.renderer.tools.group_adjacent_calls(timeline)
