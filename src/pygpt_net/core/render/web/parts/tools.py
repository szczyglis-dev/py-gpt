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

"""Live tool output and tool continuation policy."""

import json
from typing import Optional

from ..tool_display import project
from pygpt_net.item.ctx import CtxItem, CtxMeta


class Tools:
    """Live tool output and tool continuation policy.

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
    # Tool output lifecycle
    # ========================================

    def tool_output_begin(
            self,
            meta: CtxMeta,
            tool_names: Optional[list] = None,
            ctx: Optional[CtxItem] = None,
    ):
        """Show an animated tool row inside the chronological message body."""
        _key, _pid, working_ctx = self.renderer.agents.workflow_status_key(meta, ctx)
        if tool_names:
            self.renderer.agents.update_agent_working(meta, working_ctx, tool_started=True)
        names_list = self.renderer.window.core.command.realtime_visible_tool_names(
            list(tool_names or [])
        )
        # Non-exempt hidden tools are intentionally invisible, but they must not
        # retire the neutral request spinner. Returning before
        # _workflow_status_add() keeps the current loader state untouched while
        # the hidden tool executes.
        if not names_list:
            return
        _key, _pid, resolved_ctx = self.renderer.agents.workflow_status_key(meta, ctx)

        # Consecutive calls share one chronological row. When JSON is enabled,
        # its accordion receives task snapshots immediately; persistence readiness
        # still advances only at the next non-tool/final boundary.
        status_id = self.renderer.agents.workflow_status_add(
            meta,
            resolved_ctx,
            kind="tool",
            tool_names=names_list,
            aggregate=True,
        ) if resolved_ctx is not None else None
        try:
            names = json.dumps(names_list, ensure_ascii=False)
            parent_id = json.dumps(
                str(getattr(resolved_ctx, "id", "") or ""), ensure_ascii=False
            )
            sid = json.dumps(str(status_id or ""), ensure_ascii=False)
            self.renderer.get_output_node(meta).page().runJavaScript(
                "if (typeof window.setToolStatus !== 'undefined') "
                f"setToolStatus({names}, {parent_id}, {sid});"
                "else if (typeof window.beginToolOutput !== 'undefined') beginToolOutput();"
            )
            self.tool_output_snapshot(meta, resolved_ctx)
        except Exception:
            pass

    def tool_output_snapshot(self, meta: CtxMeta, ctx: CtxItem):
        """Publish unpromoted tasks without changing their persistence readiness.

        Scoped to a parent turn; protocol call IDs identify repeated tool names.
        This transport can also be reused by future worker status accordions.
        """
        ctx = getattr(ctx, "turn_parent", None) or ctx
        if ctx is None or not self.show_tool_chain_for_ctx(ctx):
            return
        raw_calls = []
        for part in ctx.parts or []:
            part_calls = ctx.get_part_tool_calls(visible_only=False, part=part)
            for task in getattr(part, "tasks", None) or []:
                if task.is_ui_ready() or (task.extra or {}).get("ui_visible") is False:
                    continue
                raw_calls.extend(call for call in part_calls if call.get("call_id") == (task.tool_call_id or task.uuid))
        calls = self.renderer.helpers.extract_extra_tool_calls(raw_calls)
        if not calls:
            return
        for key, records in self.state.workflow_statuses.items():
            if key[1] != str(ctx.id):
                continue
            record = next((row for row in reversed(records) if row.get("kind") == "tool"), None)
            if record is not None:
                # Promotion between provider rounds changes ui_ready, but it is
                # not a visual series boundary. Keep earlier calls in this row.
                combined = {
                    call.get("call_id") or call.get("request"): call
                    for call in record.get("live_tool_calls") or []
                }
                for call in calls:
                    combined[call.get("call_id") or call.get("request")] = call
                calls = list(combined.values())
                record["live_tool_calls"] = calls
        payload = json.dumps(calls, ensure_ascii=False)
        parent = json.dumps(str(ctx.id or ""))
        self.renderer.get_output_node(meta).page().runJavaScript(
            "if (typeof window.syncLiveTools !== 'undefined') "
            f"syncLiveTools({parent}, {payload});"
        )

    def tool_output_end(self):
        """End tool output"""
        try:
            self.renderer.get_output_node().page().runJavaScript(
                f"if (typeof window.endToolOutput !== 'undefined') endToolOutput();"
            )
        except Exception:
            pass

    def tool_output_clear(
            self,
            meta: CtxMeta,
            ctx: Optional[CtxItem] = None,
            immediate: bool = False,
    ):
        """Retire the transient tool-series status at a real series boundary.

        During a consecutive tool round the row stays active and animated; this
        method is intentionally not called after individual tool results. With
        expandable tool JSON enabled, the durable Tool/Tools block is rendered
        first and this removes its transient predecessor. In compact status mode
        the row is frozen only here, after the series has ended. STOP/error paths
        request ``immediate=True`` and remove it at once.
        """
        _key, _pid, resolved_ctx = self.renderer.agents.workflow_status_key(meta, ctx)
        durable_tool_ui = (
            self.show_tool_chain_for_ctx(resolved_ctx)
            if resolved_ctx is not None
            else self._display_tool_calls_json()
        )
        remove_status = bool(immediate or durable_tool_ui)
        if remove_status:
            self.renderer.agents.workflow_status_remove(meta, resolved_ctx, kind="tool")
        else:
            # Without the durable JSON accordion the status itself is the only
            # tool visualization. Keep it in runtime history so subsequent tool
            # calls can reuse and aggregate the same Tool/Tools row.
            self.renderer.agents.workflow_status_freeze(meta, resolved_ctx, kind="tool")
        try:
            parent_id = json.dumps(
                str(getattr(resolved_ctx, "id", "") or ""), ensure_ascii=False
            )
            remove_js = "true" if remove_status else "false"
            self.renderer.get_output_node(meta).page().runJavaScript(
                "if (typeof window.clearToolStatus !== 'undefined') "
                f"clearToolStatus({parent_id}, {remove_js});"
                "else if (typeof window.freezeWorkflowStatus !== 'undefined') "
                f"freezeWorkflowStatus({parent_id}, 'tool');"
            )
        except Exception:
            pass

    # ========================================
    # Tool output content
    # ========================================

    def tool_output_append(self, meta: CtxMeta, content: str):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content to append
        """
        if not self._display_tool_calls_json():
            return
        try:
            self.renderer.get_output_node(meta).page().runJavaScript(
                f"""if (typeof window.appendToolOutput !== 'undefined') appendToolOutput({self.renderer.to_json(
                    self.renderer.sanitize_html(content)
                )});"""
            )
        except Exception:
            pass

    def tool_output_update(self, meta: CtxMeta, content: str):
        """
        Replace tool output

        :param meta: context meta
        :param content: content to set
        """
        if not self._display_tool_calls_json():
            return
        try:
            # TOOL_UPDATE is also used for the live/final tool response before
            # the context is rebuilt.  Normalize valid JSON here as well so the
            # user never sees nested Unicode escapes during the current turn.
            display_content = self.renderer.helpers.format_cmd_data(content, indent=True)
            self.renderer.get_output_node(meta).page().runJavaScript(
                f"""if (typeof window.updateToolOutput !== 'undefined') updateToolOutput({self.renderer.to_json(
                    {"raw": self.renderer.sanitize_html(display_content), "friendly": project(display_content, window=self.renderer.window)}
                )});"""
            )
        except Exception:
            pass

    def build_result(self, ctx: CtxItem, next_ctx: Optional[CtxItem], tool_calls: list) -> dict:
        """Build UI-only tool result fields without changing stored payloads."""
        # tool output visibility (agent step / commands)
        is_cmd = (
            next_ctx is not None
            and next_ctx.internal
            and self._ctx_has_tool_request(ctx)
        )
        tool_result = ""
        tool_output = ""  # backward-compatible HTML-ready result
        tool_output_visible = bool(tool_calls)
        if is_cmd:
            if ctx.results is not None and len(ctx.results) > 0 \
                    and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
                tool_result = str(ctx.input)
                tool_output_visible = True
            else:
                tool_result = str(next_ctx.input)
                tool_output_visible = True
        elif ctx.results is not None and len(ctx.results) > 0 \
                and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
            tool_result = str(ctx.input)

        if not self._display_tool_calls_json():
            # The compact status is the complete tool visualization in this
            # mode; suppress both structured and legacy expandable wrappers.
            tool_output_visible = False

        tool_result_display = ""
        if tool_result:
            # Keep the model-facing payload untouched; normalize only the
            # UI representation.  Tool results can contain JSON serialized
            # inside JSON string fields, which otherwise leaves \uXXXX
            # escapes visible in the WebView.
            tool_result_display = self.renderer.helpers.format_cmd_data(tool_result, indent=True)
            tool_output = self.renderer.helpers.format_cmd_text(tool_result, indent=True)

        # plugin-driven extra (HTML) – keep as-is to preserve functionality
        tool_extra_html = self.renderer.body.prepare_tool_extra(ctx)

        return {
            "tool_result": tool_result_display,
            "tool_result_friendly": project(tool_result_display, tool_calls[0].get("name", "") if len(tool_calls) == 1 else "", window=self.renderer.window),
            "tool_output": tool_output,
            "tool_output_visible": tool_output_visible,
            "tool_extra_html": tool_extra_html,
        }

    # ========================================
    # Tool chains
    # ========================================

    def is_tool_reply_transition(
            self,
            ctx: Optional[CtxItem],
            next_ctx: Optional[CtxItem]
    ) -> bool:
        """
        Return True when next_ctx is an internal continuation carrying a reply
        to a tool/command request made by ctx.
        """
        return bool(
            ctx is not None
            and next_ctx is not None
            and getattr(next_ctx, "internal", False)
            and self._ctx_has_tool_request(ctx)
        )

    def show_tool_chain_for_ctx(self, ctx: CtxItem) -> bool:
        """Return whether persisted tool calls should be rendered for this turn.

        ``ctx.tool_calls.show_json`` is the global Chats -> Render preference.
        Agents v2 additionally keeps its own tool-chain visibility preference so
        changing either option also applies to already persisted conversations.
        Other modes keep their existing rendering semantics when the global
        preference is enabled.
        """
        if not self._display_tool_calls_json():
            return False
        if not CtxItem.uses_agent_timeline(ctx):
            return True
        return bool(self.renderer.window.core.config.get("agent.v2.show_tool_chain", False))

    @staticmethod
    def group_adjacent_calls(timeline: list) -> list:
        """Group consecutive tool rows, respecting text/status/message boundaries."""
        def tool_only(segment):
            return bool(segment.get("tool_calls")) and not any(
                segment.get(key)
                for key in ("text", "status_id", "status_kind", "inline_message")
            )

        grouped = []
        for segment in timeline:
            if grouped and tool_only(segment) and tool_only(grouped[-1]):
                previous = grouped[-1]
                previous["tool_calls"] = (
                    list(previous.get("tool_calls") or [])
                    + list(segment.get("tool_calls") or [])
                )
            else:
                grouped.append(segment)
        return grouped

    # ========================================
    # Private: requests and display settings
    # ========================================

    def _ctx_has_tool_request(self, ctx: Optional[CtxItem]) -> bool:
        """
        Check whether an item is the request side of a tool/command reply.

        Keep this compatible with the same signals used by tool-result rendering:
        native tool calls, legacy commands and extra context. Parsing the output is
        a fallback for persisted contexts where the explicit tool_calls field is
        not available anymore.

        :param ctx: Context item
        :return: True if the item requests a tool/command continuation
        """
        if ctx is None:
            return False

        explicit_request = False
        try:
            tool_calls = list(getattr(ctx, "tool_calls", None) or [])
            if tool_calls:
                explicit_request = True
                if self.renderer.window.core.command.visible_tools(tool_calls):
                    return True
        except Exception:
            pass

        try:
            cmds = list(getattr(ctx, "cmds", None) or [])
            if cmds:
                explicit_request = True
                if self.renderer.window.core.command.visible_tools(cmds):
                    return True
        except Exception:
            pass

        # An explicit hidden-only request must not participate in visual
        # tool-chain grouping even if it also produced extra context.
        if explicit_request:
            return False

        try:
            if getattr(ctx, "extra_ctx", None):
                return True
        except Exception:
            pass

        output = getattr(ctx, "output", None)
        if output:
            try:
                return bool(self.renderer.helpers.extract_tool_calls(str(output)))
            except Exception:
                pass
        return False

    def _display_tool_calls_json(self) -> bool:
        """Return whether expandable tool request/response blocks are enabled."""
        return bool(self.renderer.window.core.config.get("ctx.tool_calls.show_json", True))
