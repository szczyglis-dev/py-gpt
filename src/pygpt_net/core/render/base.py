#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.11 08:00:00                  #
# ================================================== #

from typing import Optional, List

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.utils import trans


class BaseRenderer:
    def __init__(self, window=None):
        """
        Base renderer

        :param window: Window instance
        """
        self.window = window
        self.tab = None

    @staticmethod
    def get_inline_messages(extra) -> list:
        """Return normalized UI-only inline messages from part extra data."""
        if not isinstance(extra, dict):
            return []

        messages = extra.get("inline_messages")
        if not isinstance(messages, list):
            return []

        normalized = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            msg_type = str(message.get("type") or "").strip()
            text = str(message.get("text") or "").strip()
            if not text:
                continue
            normalized.append({
                "type": msg_type or "message",
                "text": text,
            })
        return normalized

    @staticmethod
    def get_inline_message_label(msg_type: str) -> str:
        """Return the UI label for a normalized inline message type."""
        msg_type = str(msg_type or "message").strip() or "message"
        if msg_type == "agent_judge":
            return trans("agent.judge")
        return msg_type.replace("_", " ").strip().title()

    def set_tab(self, tab: Tab):
        """
        Append tab

        :param tab: Tab
        """
        self.tab = tab

    def prepare(self):
        """
        Prepare renderer
        """
        pass

    def fresh(self, meta: CtxMeta):
        """
        Fresh renderer

        :param meta: context PID
        """
        pass

    def get_pid(self, meta: CtxMeta):
        """
        Get PID for context meta
        
        :param meta: context PID
        """
        pass

    def get_pid_data(self, pid: int):
        """
        Get PID data for given PID

        :param pid: PID
        """
        pass

    def is_stream(self) -> bool:
        """
        Check if it is a stream

        :return: True if stream is enabled
        """
        return self.window.core.config.get("stream")

    def begin(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            stream: bool = False
    ):
        """
        Render begin
        
        :param meta: context meta
        :param ctx: context item
        :param stream: True if stream
        """
        pass

    def end(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            stream: bool = False
    ):
        """
        Render end
        
        :param meta: context meta
        :param ctx: context item
        :param stream: True if stream
        """
        pass

    def end_extra(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            stream: bool = False
    ):
        """
        Render end extra
        
        :param meta: context meta
        :param ctx: context item
        :param stream: True if stream
        """
        pass

    def stream_begin(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Render stream begin
        
        :param meta: context meta
        :param ctx: context item
        """
        pass  # do nothing

    def stream_end(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Render stream end
        
        :param meta: context meta
        :param ctx: context item
        """
        pass  # do nothing    

    def clear_output(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Clear output

        :param meta: context meta
        """
        pass

    def clear_input(self):
        """Clear input"""
        pass

    def reset(self, meta: CtxMeta = None):
        """
        Reset

        :param meta: context meta
        """
        pass

    def reload(self, meta: Optional[CtxMeta] = None):
        """Reload all outputs, called externally only on theme change to redraw content"""
        pass

    def sync_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            replace_text: bool = False,
            reason: Optional[str] = None
    ):
        """Synchronize one output message.

        Renderers without addressable message nodes may fall back to a full
        redraw. Web renderer overrides this with an in-place mutation.
        """
        self.reload(meta)

    def finalize_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            replace_text: bool = False,
            reason: Optional[str] = None
    ):
        """Finalize a live output row without changing its text by default."""
        self.sync_output(meta, ctx, replace_text=replace_text, reason=reason)

    def replace_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            reason: Optional[str] = None
    ):
        """Explicitly replace the authoritative output text."""
        self.sync_output(meta, ctx, replace_text=True, reason=reason)

    def replace_input(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            reason: Optional[str] = None
    ):
        """Explicitly replace one durable input row."""
        self.reload(meta)

    def append_context(
            self,
            meta: CtxMeta,
            items: List[CtxItem],
            clear: bool = True
    ):
        """
        Append all context to output
        
        :param meta: context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        pass

    def append_input(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            flush: bool = True,
            append: bool = False
    ):
        """
        Append text input to output
        
        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush
        :param append: True to force append node
        """
        pass

    def append_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Append text output to output
        
        :param meta: context meta
        :param ctx: context item
        """
        pass

    def append_extra(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            footer: bool = False
    ):
        """
        Append extra data (images, files, etc.) to output
        
        :param meta: context meta
        :param ctx: context item
        :param footer: True if it is a footer
        """
        pass

    def append_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append output chunk to output
        
        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        pass

    def next_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
    ):
        """
        Flush current stream and start with new chunks
        
        :param meta: context meta
        :param ctx: context item
        """
        pass

    def remove_item(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        pass

    def remove_items_from(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        pass

    def on_edit_submit(self, ctx: CtxItem):
        """
        On edit submit

        :param ctx: context item
        """
        self.window.controller.ctx.refresh(restore_model=False)  # allow model change

    def on_remove_submit(self, ctx: CtxItem):
        """
        On remove submit

        :param ctx: context item
        """
        pass

    def on_reply_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.window.controller.ctx.refresh(restore_model=False)  # allow model change

    def clear_all(self):
        """Clear all"""
        pass

    def on_load(self, meta: CtxMeta = None):
        """
        On load (meta)

        :param meta: context metam
        """
        pass

    def on_page_loaded(
            self,
            meta: Optional[CtxMeta] = None,
            tab: Optional[Tab] = None):
        """
        On page loaded callback

        :param meta: context meta
        :param tab: Tab
        """
        self.tab = tab

    def on_enable_edit(
            self,
            live: bool = True
    ):
        """
        On enable edit icons

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_disable_edit(
            self,
            live: bool = True
    ):
        """
        On disable edit icons

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_enable_timestamp(
            self,
            live: bool = True
    ):
        """
        On enable timestamp

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_disable_timestamp(
            self,
            live: bool = True
    ):
        """
        On disable timestamp

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_theme_change(self):
        """On theme change"""
        pass

    def get_scroll_position(self) -> int:
        """
        Get scroll position

        :return: scroll position
        """
        return 0

    def set_scroll_position(self, position: int):
        """
        Set scroll position

        :param position: scroll position
        """
        pass

    def tool_output_append(
            self,
            meta:
            CtxMeta,
            content: str
    ):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content
        """
        pass

    def tool_output_update(
            self,
            meta: CtxMeta,
            content: str
    ):
        """
        Replace tool output

        :param meta: context meta
        :param content: content
        """
        pass

    def tool_output_clear(
            self,
            meta: CtxMeta,
            ctx: Optional[CtxItem] = None,
            immediate: bool = False,
    ):
        """
        Clear tool output

        :param meta: context meta
        """
        pass

    def tool_output_begin(
            self,
            meta: CtxMeta,
            tool_names: Optional[list] = None,
            ctx: Optional[CtxItem] = None,
    ):
        """
        Begin tool output

        :param meta: context meta
        """
        pass

    def tool_output_end(self):
        """End tool output"""
        pass

    def state_changed(
            self,
            state: str,
            meta: CtxMeta,
            loading_delay_ms: int = 0,
            loading_wait_for_input: bool = False,
    ):
        """
        Render end

        :param state: state name
        :param meta: context meta
        :param loading_delay_ms: optional loader visibility delay
        :param loading_wait_for_input: wait until the user row is materialized
        """
        pass

    def agent_status(self, meta: CtxMeta, ctx: CtxItem, status: str):
        """Set transient agent workflow status (optional renderer capability)."""
        pass

    def agent_status_clear(self, meta: CtxMeta, ctx: CtxItem):
        """Clear transient agent workflow status (optional renderer capability)."""
        pass

    def append_live(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append live output chunk to output

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        pass

    def clear_live(self, meta: CtxMeta, ctx: CtxItem):
        """
        Clear live output

        :param meta: context meta
        :param ctx: context item
        """
        pass

    def remove_pid(self, pid: int):
        """
        Remove PID from renderer
        """
        pass

    def on_js_ready(self, pid: int) -> None:
        """On JS ready - web renderer only"""
        pass
