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

"""Busy indicators and visible response versus hidden reasoning activity."""

from typing import Optional
from pygpt_net.item.ctx import CtxMeta
from pygpt_net.core.events import RenderEvent


class Loading:
    """Busy indicators and visible response versus hidden reasoning activity.

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
    # Loading indicators
    # ========================================

    def state_changed(
            self,
            state: str,
            meta: CtxMeta,
            loading_delay_ms: int = 0,
            loading_wait_for_input: bool = False,
    ):
        """
        On kernel state changed event

        :param state: new state
        :param meta: context meta
        :param loading_delay_ms: optional loader visibility delay
        :param loading_wait_for_input: wait until the user row is materialized
        """
        if state == RenderEvent.STATE_BUSY:
            if meta:
                pid = self.renderer.get_pid(meta)
                if pid is not None:
                    # Repeated BUSY events are common when a mode finishes input
                    # materialization and reasserts ownership (Agents v2).  The
                    # loader may already be armed with a delayed/input-gated show;
                    # do not restart that pending gate after the inputReady event.
                    if self.state.loading_visible.get(pid, False):
                        return
                    try:
                        delay_ms = max(0, int(loading_delay_ms or 0))
                    except (TypeError, ValueError):
                        delay_ms = 0
                    wait_for_input = bool(loading_wait_for_input)
                    self.state.loading_visible[pid] = True
                    self.state.loading_reserved[pid] = False
                    self.state.loading_show_options[pid] = (delay_ms, wait_for_input)
                    node = self.renderer.get_output_node_by_pid(pid)
                    try:
                        wait_js = "true" if wait_for_input else "false"
                        node.page().runJavaScript(
                            "if (typeof window.showLoading !== 'undefined') "
                            f"showLoading({delay_ms}, {wait_js});"
                        )
                    except Exception:
                        pass

        elif state in (RenderEvent.STATE_IDLE, RenderEvent.STATE_ERROR):
            # A request completion/error belongs to one chat. Hide only that
            # chat's loader when meta is known; global events (app stop, legacy
            # callers without context) may still clear all loaders.
            if meta is not None:
                pid = self.renderer.get_pid(meta)
                target_pids = (pid,) if pid is not None else ()
            else:
                target_pids = tuple(self.state.pids.keys())

            for pid in target_pids:
                self.state.loading_visible[pid] = False
                self.state.loading_reserved[pid] = False
                self.state.loading_show_options.pop(pid, None)
                if state == RenderEvent.STATE_ERROR:
                    # Error/interruption history may intentionally retain the
                    # last workflow row. Stop its shimmer when the request is no
                    # longer running, but do not remove the row itself.
                    for key, records in self.state.workflow_statuses.items():
                        if key and key[0] == pid:
                            for record in records:
                                record["active"] = False
                node = self.renderer.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            "if (typeof window.hideLoading !== 'undefined') hideLoading();"
                            "if (typeof window.clearAgentWorking !== 'undefined') clearAgentWorking();"
                        )
                    except Exception:
                        pass

    def hide_loading_on_activity(
            self,
            meta: Optional[CtxMeta],
            pid: Optional[int] = None,
            reserve_space: bool = True,
    ) -> None:
        """Hide request spinner while optionally preserving its layout slot.

        Intermediate agent/tool/partial activity keeps the slot reserved so the
        WebView height cannot jump. The main/final response releases it.
        """
        if pid is None and meta is not None:
            pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return
        self.state.loading_visible[pid] = False
        self.state.loading_reserved[pid] = bool(reserve_space)
        self.state.loading_show_options.pop(pid, None)
        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            return
        try:
            reserve_js = "true" if reserve_space else "false"
            node.page().runJavaScript(
                "if (typeof window.hideLoading !== 'undefined') "
                f"hideLoading({reserve_js});"
            )
        except Exception:
            pass

    # ========================================
    # Response activity
    # ========================================

    def chunk_has_response_activity(self, key: tuple, text: str) -> bool:
        """Return whether a streamed chunk contains visible assistant response text.

        The parser keeps <think> state across chunks, including split opening or
        closing tags. When live reasoning is enabled, reasoning itself is visible
        activity and preserves the legacy behavior. When disabled, only text
        outside <think> may dismiss the request spinner.
        """
        raw = str(text or "")
        if not raw:
            return False

        state = self.state.reasoning_activity_state.setdefault(
            key,
            {"inside": False, "carry": ""},
        )
        value = str(state.get("carry") or "") + raw
        state["carry"] = ""
        inside = bool(state.get("inside", False))
        has_response = False
        pos = 0

        while pos < len(value):
            open_at = value.find("<think>", pos)
            close_at = value.find("</think>", pos)
            next_at = -1
            is_open = False

            if open_at != -1 and (close_at == -1 or open_at < close_at):
                next_at = open_at
                is_open = True
            elif close_at != -1:
                next_at = close_at

            if next_at == -1:
                tail = value[pos:]
                carry = self._reasoning_partial_tag_suffix(tail)
                visible_tail = tail[:-len(carry)] if carry else tail
                if not inside and visible_tail.strip():
                    has_response = True
                state["carry"] = carry
                break

            if not inside and value[pos:next_at].strip():
                has_response = True
            inside = is_open
            pos = next_at + (len("<think>") if is_open else len("</think>"))

        state["inside"] = inside
        if self._realtime_reasoning_enabled():
            return bool(raw.strip())
        return has_response

    # ========================================
    # Private: reasoning visibility
    # ========================================

    def _realtime_reasoning_enabled(self) -> bool:
        """Return True when reasoning is intentionally visible during streaming."""
        try:
            return bool(self.renderer.window.core.config.get("ctx.reasoning.show_realtime", False))
        except Exception:
            return False

    @staticmethod
    def _reasoning_partial_tag_suffix(text: str) -> str:
        """Return a trailing fragment that can still become a <think> boundary."""
        value = str(text or "")
        if not value:
            return ""
        tags = ("<think>", "</think>")
        max_len = min(len(value), max(len(tag) for tag in tags) - 1)
        for size in range(max_len, 0, -1):
            suffix = value[-size:]
            if any(tag.startswith(suffix) for tag in tags):
                return suffix
        return ""

