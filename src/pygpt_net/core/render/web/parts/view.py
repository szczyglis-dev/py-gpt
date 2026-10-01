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

"""View controls, message actions, names and theme updates."""

from pygpt_net.core.render.protocol import RenderMutation, RenderOp
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.utils import trans


class View:
    """View controls, message actions, names and theme updates.

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
    # Input and message controls
    # ========================================

    def clear_input(self):
        """Clear input"""
        self.renderer.get_input_node().clear()

    def remove_item(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        self.renderer.bridge.emit_mutation(ctx.meta, RenderMutation(
            op=RenderOp.REMOVE_MESSAGE,
            msg_id=getattr(ctx, "id", None),
        ))

    def remove_items_from(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        self.renderer.bridge.emit_mutation(ctx.meta, RenderMutation(
            op=RenderOp.REMOVE_FROM,
            msg_id=getattr(ctx, "id", None),
        ))

    def on_reply_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.remove_items_from(ctx)

    def on_edit_submit(self, ctx: CtxItem):
        """
        On edit submit

        :param ctx: context item
        """
        self.remove_items_from(ctx)

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons

        :param live: True if live mode
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.enableEditIcons !== 'undefined') enableEditIcons();")
        except Exception:
            pass

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons

        :param live: True if live mode
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.disableEditIcons !== 'undefined') disableEditIcons();")
        except Exception:
            pass

    # ========================================
    # Names and timestamps
    # ========================================

    def update_names(self, meta: CtxMeta, ctx: CtxItem):
        """
        Update names from ctx

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return
        if ctx.input_name is not None and ctx.input_name != "":
            self.state.pids[pid].name_user = ctx.input_name
        if ctx.output_name is not None and ctx.output_name != "":
            self.state.pids[pid].name_bot = ctx.output_name

    def reset_names(self, meta: CtxMeta):
        """
        Reset names

        :param meta: context meta
        """
        if meta is None:
            return
        pid = self.renderer.session.get_or_create_pid(meta)
        self.reset_names_by_pid(pid)

    def reset_names_by_pid(self, pid: int):
        """
        Reset names by PID

        :param pid: context PID
        """
        self.state.pids[pid].name_user = trans("chat.name.user")
        self.state.pids[pid].name_bot = trans("chat.name.bot")

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp

        :param live: True if live mode
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.enableTimestamp !== 'undefined') enableTimestamp();")
        except Exception:
            pass

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp

        :param live: True if live mode
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.disableTimestamp !== 'undefined') disableTimestamp();")
        except Exception:
            pass

    # ========================================
    # Output and scrolling
    # ========================================

    def clear_all(self):
        """Clear all tabs"""
        self.state.workflow_statuses.clear()
        for pid in self.state.pids:
            self.renderer.session.clear_chunks(pid)
            self.renderer.bridge.clear_nodes(pid)
            self.state.pids[pid].html = ""
            self.renderer.streaming.stream_reset(pid)

    def append_block(self):
        """Append block placeholder"""
        pass

    def scroll_to_bottom(self):
        """Scroll to bottom placeholder"""
        pass

    def resume_auto_follow_if_near_bottom(
            self,
            meta: CtxMeta,
            margin: int = 128,
            force: bool = False
    ):
        """Re-arm WebView auto-follow for a realtime response.

        Realtime can begin its provider stream immediately after APPEND_INPUT while
        the request loader is still changing document height. In that narrow race
        Chromium may report a layout-driven scroll as manual movement and leave the
        JS ScrollManager in MANUAL even though the user never moved away from the
        bottom. Normally recover only when the physical viewport remains close to
        the bottom. ``force=True`` is reserved for the first visible realtime token:
        a freshly submitted microphone turn explicitly owns FOLLOW, so that token
        must snap to the real bottom and keep the permanent bottom anchor enabled.

        This helper is invoked only by the Realtime controller and therefore does
        not alter scroll ownership in Chat/Agents/other modes.

        :param meta: context meta owning the WebView
        :param margin: maximum distance from the physical bottom in pixels
        :param force: reassert FOLLOW regardless of transient layout distance
        """
        if meta is None:
            return
        try:
            node = self.renderer.get_output_node(meta)
            if node is None:
                return
            safe_margin = max(0, int(margin))
            force_js = "true" if force else "false"
            node.page().runJavaScript(
                "(() => {"
                "const el = document.scrollingElement || document.documentElement;"
                "if (!el) return false;"
                "const d = Math.max(0, el.scrollHeight - el.clientHeight - el.scrollTop);"
                f"if ({force_js} || d <= {safe_margin}) {{"
                "if (typeof window.scrollToBottomUser === 'function') {"
                "window.scrollToBottomUser(); return true;"
                "}"
                "}"
                "return false;"
                "})()"
            )
        except Exception:
            pass

    def to_end(self, ctx: CtxItem):
        """Move cursor to end placeholder"""
        pass

    # ========================================
    # Theme and output nodes
    # ========================================

    def on_theme_change(self):
        """On theme change"""
        self.renderer.window.controller.theme.markdown.load()
        for pid in self.state.pids:
            if self.state.pids[pid].loaded:
                self.reload_css()
                return

    def reload_css(self):
        """Reload CSS – propagate theme and config to runtime"""
        to_json = self.renderer.to_json(self.renderer.body.prepare_styles())
        nodes = self.get_all_nodes()
        for pid in self.state.pids:
            if self.state.pids[pid].loaded:
                for node in nodes:
                    try:
                        node.page().runJavaScript(
                            f"if (typeof window.updateCSS !== 'undefined') updateCSS({to_json});"
                        )
                        if self.renderer.window.core.config.get('render.blocks'):
                            node.page().runJavaScript(
                                "if (typeof window.enableBlocks !== 'undefined') enableBlocks();"
                            )
                        else:
                            node.page().runJavaScript(
                                "if (typeof window.disableBlocks !== 'undefined') disableBlocks();"
                            )
                    except Exception:
                        pass
                return

    def get_all_nodes(self) -> list:
        """Return all registered nodes"""
        return self.renderer.window.core.ctx.output.get_all()

