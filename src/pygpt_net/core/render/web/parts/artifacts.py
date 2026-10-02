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

"""Attachment rendering and tool-chain attachment deduplication."""

import os
from typing import List, Tuple
from pygpt_net.core.render.protocol import RenderMutation, RenderOp
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.item.render_attachment import attachment_type


class Artifacts:
    """Attachment rendering and tool-chain attachment deduplication.

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
    # Attachments and source documents
    # ========================================

    def append_extra(self, meta: CtxMeta, ctx: CtxItem, footer: bool = False, render: bool = True) -> str:
        """
        Append extra data (legacy HTML way) – kept for runtime calls that append later.

        :param meta: context meta
        :param ctx: context item
        :param footer: True if append at the end (legacy)
        :param render: True if render to output (legacy)
        :return: rendered HTML
        """
        self.renderer.tools.tool_output_end()

        pid = self.renderer.get_pid(meta)
        appended = set()
        html_parts = []

        c = sum(path is not None and attachment_type(path) == "output" for path in ctx.images)
        if c > 0:
            n = 1
            for image in ctx.images:
                if image is None or attachment_type(image) == "user":
                    continue
                attachments = getattr(self.renderer.window.core, "attachments", None)
                if (attachments is not None
                        and hasattr(attachments, "is_ctx_excluded_path")
                        and attachments.is_ctx_excluded_path(image)):
                    continue
                if image in appended or image in self.state.pids[pid].images_appended:
                    continue
                try:
                    appended.add(image)
                    html_parts.append(self.renderer.body.get_image_html(image, n, c, ctx=ctx))
                    self.state.pids[pid].images_appended.append(image)
                    n += 1
                except Exception:
                    pass

        c = sum(path is not None and attachment_type(path) == "output" for path in ctx.files)
        if c > 0:
            files_html = []
            n = 1
            for file in ctx.files:
                if attachment_type(file) == "user":
                    continue
                if file in appended or file in self.state.pids[pid].files_appended:
                    continue
                try:
                    appended.add(file)
                    files_html.append(self.renderer.body.get_file_html(file, n, c, ctx=ctx))
                    self.state.pids[pid].files_appended.append(file)
                    n += 1
                except Exception:
                    pass
            if files_html:
                html_parts.append(self.renderer.body.get_collapsible_extra_rows_html(files_html))

        c = len(ctx.urls)
        if c > 0:
            urls_html = []
            n = 1
            for url in ctx.urls:
                if url in appended or url in self.state.pids[pid].urls_appended:
                    continue
                try:
                    appended.add(url)
                    urls_html.append(self.renderer.body.get_url_html(url, n, c))
                    self.state.pids[pid].urls_appended.append(url)
                    n += 1
                except Exception:
                    pass
            if urls_html:
                html_parts.append(self.renderer.body.get_collapsible_extra_rows_html(urls_html))

        if self.renderer.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                try:
                    docs = self.renderer.body.get_docs_html(ctx.doc_ids)
                    html_parts.append(docs)
                except Exception:
                    pass

        html = "".join(html_parts)
        if render and html != "":
            # Extras are a message mutation too. Keep them on the same ordered
            # transport as text/finalization instead of issuing an unrelated
            # runJavaScript call that can race a stream boundary. ``html`` is a
            # delta here (append_* tracking above filters already-rendered rows).
            self.renderer.bridge.emit_mutation(meta, RenderMutation(
                op=RenderOp.APPEND_ARTIFACTS,
                msg_id=getattr(ctx, "id", None),
                extra={
                    "html": self.renderer.sanitize_html(html),
                    "footer": bool(footer),
                },
                reason="runtime_extra",
            ))

        return html

    def apply_to_block(self, block, ctx: CtxItem, pid: int, action_state: dict) -> None:
        """Populate attachments, source documents and their action routing."""
        # extras (images/files/urls/actions)
        images, files, urls, extra_actions = self.renderer.body.build_extras_dicts(
            ctx,
            pid,
            edit_replay_id=action_state.get("edit_replay_id"),
            delete_start_id=action_state.get("delete_start_id"),
            delete_end_id=action_state.get("delete_end_id"),
        )

        # Extras carried forward through a tool-call chain are rendered only
        # at their last occurrence (the response-side item). The original
        # CtxItems remain untouched; only duplicate visual extras are filtered.
        hidden_image_keys, hidden_file_keys, hidden_url_keys = \
            self._get_hidden_tool_chain_extra_keys_for_ctx(ctx)

        images = self._filter_extras(images, hidden_image_keys, self._normalize_image_extra_key)
        files = self._filter_extras(files, hidden_file_keys, self._normalize_file_extra_key)
        urls = self._filter_extras(
            urls, hidden_url_keys, self._normalize_url_extra_key, path_first=False,
        )

        block.images = images
        block.files = files
        block.urls = urls

        # docs as raw data -> rendered in JS
        docs_norm = []
        if self.renderer.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                docs_norm = self.renderer.body.normalize_docs(ctx.doc_ids)

        block.extra["docs"] = docs_norm
        block.extra.update(extra_actions)

    # ========================================
    # Private: attachment identity
    # ========================================

    def _normalize_image_extra_key(self, image) -> str:
        """
        Return a stable key for an image attachment used by the web renderer.

        Context items may carry the same local image in slightly different URL/path
        forms (native path vs. file:// URL).  Normalize through the filesystem helper
        so duplicate detection across tool-chain items is based on the actual media
        target rather than the serialized representation.
        """
        if image is None:
            return ""
        try:
            url, path = self.renderer.window.core.filesystem.extract_local_url(str(image))
            if path:
                try:
                    return os.path.normcase(os.path.normpath(path))
                except Exception:
                    return str(path)
            if url:
                return str(url)
        except Exception:
            pass
        return str(image)

    def _normalize_file_extra_key(self, file) -> str:
        """Return a stable key for a local file attachment used by the web renderer."""
        return self._normalize_image_extra_key(file)

    def _normalize_url_extra_key(self, url) -> str:
        """Return a stable key for a URL extra used by the web renderer."""
        if url is None:
            return ""
        return str(url).strip()

    # ========================================
    # Private: tool-chain deduplication
    # ========================================

    def _get_hidden_tool_chain_extra_keys_for_ctx(self, ctx: CtxItem) -> Tuple[set, set, set]:
        """Resolve image/file/URL de-duplication state for a single context item."""
        try:
            items = self.renderer.window.core.ctx.get_items()
        except Exception:
            return set(), set(), set()

        cid = getattr(ctx, "id", None)
        for index, item in enumerate(items):
            if getattr(item, "id", None) == cid:
                return (
                    self._get_hidden_tool_chain_image_keys(items, index),
                    self._get_hidden_tool_chain_file_keys(items, index),
                    self._get_hidden_tool_chain_url_keys(items, index),
                )
        return set(), set(), set()

    def _get_hidden_tool_chain_extra_keys(
            self,
            items: List[CtxItem],
            index: int,
            attr: str,
            normalizer
    ) -> set:
        """
        Return extra keys hidden on this item when the same extra is rendered
        again later in the same tool-call continuation chain.
        """
        if index < 0 or index >= len(items):
            return set()

        ctx = items[index]
        current_values = getattr(ctx, attr, None) or []
        if not current_values:
            return set()

        # De-duplication only applies when this item actually continues into a
        # tool-result item. A normal message must keep all of its extras.
        if index + 1 >= len(items) or not self.renderer.tools.is_tool_reply_transition(ctx, items[index + 1]):
            return set()

        current_keys = {
            normalizer(value)
            for value in current_values
            if value is not None
        }
        current_keys.discard("")
        if not current_keys:
            return set()

        later_keys = set()
        pos = index + 1
        while pos < len(items):
            item = items[pos]
            for value in (getattr(item, attr, None) or []):
                if value is None:
                    continue
                key = normalizer(value)
                if key:
                    later_keys.add(key)

            # Stay strictly inside the same consecutive tool continuation chain.
            if pos + 1 >= len(items) or not self.renderer.tools.is_tool_reply_transition(item, items[pos + 1]):
                break
            pos += 1

        return current_keys.intersection(later_keys)

    def _get_hidden_tool_chain_image_keys(self, items: List[CtxItem], index: int) -> set:
        """Return duplicate image keys hidden before the final tool-chain occurrence."""
        return self._get_hidden_tool_chain_extra_keys(
            items,
            index,
            "images",
            self._normalize_image_extra_key,
        )

    def _get_hidden_tool_chain_file_keys(self, items: List[CtxItem], index: int) -> set:
        """Return duplicate file keys hidden before the final tool-chain occurrence."""
        return self._get_hidden_tool_chain_extra_keys(
            items,
            index,
            "files",
            self._normalize_file_extra_key,
        )

    def _get_hidden_tool_chain_url_keys(self, items: List[CtxItem], index: int) -> set:
        """Return duplicate URL keys hidden before the final tool-chain occurrence."""
        return self._get_hidden_tool_chain_extra_keys(
            items,
            index,
            "urls",
            self._normalize_url_extra_key,
        )

    @staticmethod
    def _filter_extras(values: dict, hidden_keys: set, normalizer, *, path_first=True) -> dict:
        """Hide carried attachments only at earlier tool-chain occurrences."""
        if not hidden_keys or not values:
            return values
        visible = (
            value for value in values.values()
            if normalizer((value.get("path") if path_first else None) or value.get("url")) not in hidden_keys
        )
        return {str(index): value for index, value in enumerate(visible, 1)}
