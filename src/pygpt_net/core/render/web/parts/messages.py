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

"""Message identity and construction of frontend render blocks."""

import json
import os
import re
from datetime import datetime
from typing import Optional, Tuple
from pygpt_net.core.render.protocol import RenderMutation, RenderOp
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.utils import trans
from .block import RenderBlock


class Messages:
    """Message identity and construction of frontend render blocks.

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
    # Input messages
    # ========================================

    def prepare_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False) -> Optional[str]:
        """
        Prepare text input (raw, no HTML)

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush input area (legacy)
        :param append: True if append to input area (legacy)
        :return: prepared text or None
        """
        if ctx.input is None or ctx.input == "":
            return

        text = ctx.input
        if isinstance(ctx.extra, dict) and "sub_reply" in ctx.extra and ctx.extra["sub_reply"]:
            try:
                json_encoded = json.loads(text)
                if isinstance(json_encoded, dict):
                    if "expert_id" in json_encoded and "result" in json_encoded:
                        tmp = "@" + str(ctx.input_name) + ":\n\n" + str(json_encoded["result"])
                        text = tmp
            except json.JSONDecodeError:
                pass

        if ctx.internal \
                and not ctx.first \
                and not ctx.input.strip().startswith("user: ") \
                and not ctx.input.strip().startswith("@"):
            return
        else:
            if ctx.internal and ctx.input.startswith("user: "):
                text = re.sub(r'^user: ', '> ', ctx.input)

        return str(text).strip()

    def append_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False):
        """
        Append user input as RenderBlock JSON

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush input area (legacy)
        :param append: True if append to input area (legacy)
        """
        self.renderer.tools.tool_output_end()
        pid = self.renderer.session.get_or_create_pid(meta)
        if not flush:
            self.renderer.session.clear_chunks_input(pid)

        self.renderer.view.update_names(meta, ctx)
        text = self.prepare_input(meta, ctx, flush, append)
        if text:
            date_label = self.renderer.history.get_live_input_date_label(meta, ctx)
            if flush:
                if self.renderer.is_stream() and not append:
                    # legacy streaming input (leave as-is)
                    content = self.prepare_node(meta, ctx, text, self.renderer.NODE_INPUT)
                    self.renderer.streaming.append_chunk_input(
                        meta,
                        ctx,
                        content,
                        begin=False,
                        date_label=date_label,
                    )
                    return
            block = self.build_render_block(
                meta,
                ctx,
                input_text=text,
                output_text=None,
                history_date_label=date_label,
            )
            if block:
                self.renderer.bridge.emit_mutation(meta, RenderMutation(
                    op=RenderOp.APPEND_INPUT,
                    msg_id=getattr(ctx, "id", None),
                    block=block.to_dict(),
                ))

    def build_input_block(self, meta: CtxMeta, ctx: CtxItem) -> Optional[RenderBlock]:
        """Build one durable user block without touching the DOM."""
        if ctx is None or getattr(ctx, "id", None) is None:
            return None
        input_text = self.prepare_input(meta, ctx, flush=False, append=True)
        if not input_text:
            return None
        return self.build_render_block(
            meta,
            ctx,
            input_text=input_text,
            output_text=None,
            history_date_label=self.renderer.history.get_live_input_date_label(meta, ctx),
        )

    # ========================================
    # Output messages
    # ========================================

    def prepare_output(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True,
                       prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None) -> Optional[str]:
        """
        Prepare text output (raw markdown text)

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush output area (legacy)
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared text or None
        """
        output = ctx.output
        if isinstance(ctx.extra, dict) and ctx.extra.get("output"):
            if self.renderer.window.core.config.get("agent.output.render.all", False):
                output = ctx.output  # full agent output
            else:
                output = ctx.extra["output"]  # final output only

        # Agents v2 keeps the compact authoritative final in ctx_item.output.
        # Full-workflow display, when enabled, is reconstructed separately from
        # durable partials by _build_partial_timeline(); this baseline output stays
        # final-only so model-facing/storage semantics are not coupled to the UI.
        final_agent_output = ctx.get_agents_v2_response_output()
        if final_agent_output is not None:
            output = final_agent_output
        else:
            streamed_final = ctx.get_agents_v2_final_output()
            if streamed_final is not None:
                output = streamed_final
        # Readable provider reasoning is requested/persisted only when live
        # reasoning is enabled. In that mode it may also be used as a fallback
        # when the regular assistant output is empty.
        if final_agent_output is None and self.renderer.window.core.config.get("ctx.reasoning.show_realtime", False):
            output = ctx.get_display_output(output or "")
        return str(output).strip() if output else None

    def append_output(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True,
                      prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None):
        """
        Append bot output as RenderBlock JSON

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush output area (legacy)
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        self.renderer.tools.tool_output_end()
        output = self.prepare_output(meta=meta, ctx=ctx, flush=flush, prev_ctx=prev_ctx, next_ctx=next_ctx)
        visible_part_tools = self.renderer.helpers.extract_extra_tool_calls(
            ctx.get_part_tool_calls(visible_only=True)
        )
        if output or visible_part_tools:
            self.renderer.history.hide_previous_agent_action_icons(meta, ctx)
            input_text = self.prepare_input(meta, ctx, flush=False, append=True)
            block = self.build_render_block(
                meta, ctx, input_text=input_text, output_text=output,
                prev_ctx=prev_ctx, next_ctx=next_ctx,
                history_date_label=self.renderer.history.get_live_input_date_label(meta, ctx),
            )
            if block:
                self.renderer.bridge.emit_mutation(meta, RenderMutation(
                    op=RenderOp.APPEND_OUTPUT,
                    msg_id=getattr(ctx, "id", None),
                    block=block.to_dict(),
                    replace_text=True,
                ))

    def build_output_block(self, meta: CtxMeta, ctx: CtxItem) -> Optional[RenderBlock]:
        """Build the current assistant block without touching the DOM."""
        if ctx is None or getattr(ctx, "id", None) is None:
            return None
        input_text = self.prepare_input(meta, ctx, flush=False, append=True)
        output = self.prepare_output(meta=meta, ctx=ctx, flush=False)
        visible_part_tools = self.renderer.helpers.extract_extra_tool_calls(
            ctx.get_part_tool_calls(visible_only=True)
        )
        if not output and not visible_part_tools and not getattr(ctx, "parts", None):
            # Still allow input-only/structure-only snapshots.
            output = ""
        return self.build_render_block(
            meta,
            ctx,
            input_text=input_text,
            output_text=output,
            history_date_label=self.renderer.history.get_live_input_date_label(meta, ctx),
        )

    # ========================================
    # Message payloads
    # ========================================

    def build_render_block(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            input_text: Optional[str],
            output_text: Optional[str],
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None,
            action_state: Optional[dict] = None,
            rebuild: bool = False,
            is_latest_ctx: bool = False,
            history_date_label: Optional[str] = None,
    ) -> Optional[RenderBlock]:
        """
        Build RenderBlock for given ctx and payloads (input/output).

        - if input_text or output_text is None, that part is skipped.
        Visibility is resolved by the calling history/live rendering path.
        Workflow and tool-only turns may produce output without ordinary text.
        Returns None if no output PID can be resolved.

        :param meta: CtxMeta object
        :param ctx: CtxItem object
        :param input_text: Input text (raw, un-formatted)
        :param prev_ctx: Previous CtxItem (for context, optional)
        :param next_ctx: Next CtxItem (for context, optional)
        :param action_state: Optional footer/action routing state
        :return: RenderBlock object or None
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return

        if action_state is None:
            action_state = self.renderer.history.get_action_state_for_ctx(ctx)

        block = RenderBlock(id=getattr(ctx, "id", None), meta_id=getattr(meta, "id", None))

        user_images, user_files, _, _ = self.renderer.body.build_extras_dicts(ctx, pid, origin="user")
        block.extra["user_attachments"] = {"images": user_images, "files": user_files}

        # input
        if input_text:
            # Keep raw; formatting is a template duty (escape/BR etc.)
            block.input = {
                "type": "user",
                "name": self.state.pids[pid].name_user,
                "avatar_img": None,  # no user avatar by default
                "text": str(input_text),
                "timestamp": ctx.input_timestamp if hasattr(ctx, "input_timestamp") else None,
                "time_label": datetime.fromtimestamp(ctx.input_timestamp).strftime("%H:%M") if ctx.input_timestamp else "",
                "edit_title": trans("ctx.extra.edit"),
                "edit_icon": "file://" + os.path.join(self.renderer.window.core.config.get_app_path(), "data", "icons", "edit.svg").replace("\\", "/"),
            }
            if history_date_label:
                block.input["date_label"] = history_date_label

        workflow = self.renderer.agents.build_presentation(
            ctx, rebuild=rebuild, is_latest_ctx=is_latest_ctx,
        )
        show_tool_chain = workflow.show_tool_chain
        partial_timeline = workflow.partial_timeline
        collapsed_workflow = workflow.collapsed_workflow

        part_tool_calls = [] if partial_timeline or collapsed_workflow or not show_tool_chain else self.renderer.helpers.extract_extra_tool_calls(
            ctx.get_part_tool_calls(visible_only=True)
        )
        if output_text or part_tool_calls or partial_timeline:
            # New contexts render structured DB tasks. Legacy contexts still fall
            # back to <tool> tags / display-only Agents v2 metadata. A partial
            # timeline owns its tool/text rendering and must not also be flattened
            # into the block-level output/tool wrapper.
            legacy_output_calls = self.renderer.helpers.extract_tool_calls(output_text or "")
            tool_calls = [] if partial_timeline or collapsed_workflow or not show_tool_chain else (
                part_tool_calls or legacy_output_calls
            )
            if (show_tool_chain
                    and not tool_calls
                    and isinstance(ctx.extra, dict)
                    and ctx.extra.get("agents_v2_tool_calls_display") is True):
                tool_calls = self.renderer.helpers.extract_extra_tool_calls(ctx.extra.get("tool_calls"))
            visible_output_text = "" if partial_timeline else self.renderer.helpers.strip_tool_calls(
                output_text or ""
            )

            # Pre/post format raw markdown via Helpers to preserve placeholders ([!cmd], think) and workdir tokens.
            md_src = self.renderer.helpers.pre_format_text(visible_output_text, ctx=ctx)
            md_text = self.renderer.helpers.post_format_text(md_src)
            name, avatar, personalize = self._output_identity(ctx)
            show_output_identity = self._show_output_identity(ctx, prev_ctx)
            # The same transition that suppresses a repeated avatar/name also marks
            # a tool-call block as a continuation of the previous tool request.
            # Frontend uses this explicit flag to group only real tool chains, not
            # merely adjacent assistant messages that happen to contain tools.
            tool_chain_continuation = not show_output_identity

            tool_result = self.renderer.tools.build_result(ctx, next_ctx, tool_calls)

            block.output = {
                "type": "bot",
                "name": name or self.state.pids[pid].name_bot,
                "avatar_img": avatar,
                "text": md_text,
                "timestamp": ctx.output_timestamp if hasattr(ctx, "output_timestamp") else None,
            }
            agent_name_prefix = self.renderer.agents.legacy_agent_name_prefix(ctx, prefer_final=True)
            if agent_name_prefix:
                block.output["agent_name_prefix"] = agent_name_prefix

            self.renderer.artifacts.apply_to_block(block, ctx, pid, action_state)
            block.extra.update(tool_result)

            block.extra.update({
                "tool_calls": tool_calls,
                "partial_timeline": partial_timeline,
                "collapsed_workflow": collapsed_workflow,
                "agents_v2_compact_final": workflow.compact_final,
                "tool_chain_continuation": bool(tool_chain_continuation),
                "footer_icons": bool(action_state.get("footer_icons", True)),
                "personalize": bool(personalize and show_output_identity),
            })

        # carry ctx.extra flags as-is (do not collide with our own keys)
        if isinstance(ctx.extra, dict):
            block.extra.setdefault("ctx_extra", ctx.extra)

        # debug
        if self.renderer.is_debug():
            print(block.debug())
            block.extra["debug_html"] = self.renderer.append_debug(ctx, pid, "output")

        return block

    def prepare_node(self, meta: CtxMeta, ctx: CtxItem, html: str, type: int = 1,
                     prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None) -> str:
        """
        Compatibility shim: convert single input/output into markdown/raw for JS templates.

        :param meta: context meta
        :param ctx: context item
        :param html: HTML content
        :param type: NODE_INPUT or NODE_OUTPUT
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared text
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        if type == self.renderer.NODE_OUTPUT:
            return str(html)
        elif type == self.renderer.NODE_INPUT:
            return str(html)

    # ========================================
    # Names and timestamps
    # ========================================

    def get_name_header(self, ctx: CtxItem, stream: bool = False) -> str:
        """
        Legacy - kept for stream header text (avatar + name string)

        :param ctx: context item
        :param stream: True if streaming mode
        :return: HTML string
        """
        meta = ctx.meta
        if meta is None:
            return ""

        # Consecutive tool replies form one visual assistant turn. The identity
        # belongs to the first tool request only, not to later tool calls/final reply.
        if not self._show_output_identity(ctx):
            return ""

        # Agent-provided display name override:
        # If ctx.get_agent_name() returns a non-empty name, force "fake personalize":
        # - use that name
        # - optionally attach default avatar when enabled via config
        # - treat as personalized header regardless of preset
        agent_name = self._get_agent_name(ctx)
        if agent_name:
            avatar_html = ""
            try:
                use_default = self.renderer.window.core.config.get("agent.avatar.default", True)
                # if use_default and os.path.exists(self._agent_avatar):
                    # avatar_html = f"<img src=\"{self._file_prefix}{self._agent_avatar}\" class=\"avatar\"> "
            except Exception:
                pass
            if stream:
                return f"{avatar_html}{agent_name}"
            else:
                return f"<div class=\"name-header name-bot\">{avatar_html}{agent_name}</div>"

        preset_id = meta.preset
        if preset_id is None or preset_id == "":
            return ""
        preset = self.renderer.window.core.presets.get(preset_id)
        if preset is None:
            return ""
        if not preset.ai_personalize:
            return ""

        output_name = ""
        avatar_html = ""
        if preset.ai_name:
            output_name = preset.ai_name
        if preset.ai_avatar:
            # prefer thumbnail "thumb_<name>" when available
            avatar_fs = self._resolve_avatar_fs_path(preset.ai_avatar)
            if avatar_fs:
                avatar_html = f"<img src=\"{self.renderer._file_prefix}{avatar_fs}\" class=\"avatar\"> "

        if not output_name and not avatar_html:
            return ""

        if stream:
            return f"{avatar_html}{output_name}"
        else:
            return f"<div class=\"name-header name-bot\">{avatar_html}{output_name}</div>"

    def append_timestamp(self, ctx: CtxItem, text: str, type: Optional[int] = None) -> str:
        """
        Append timestamp to text (legacy HTML path)

        :param ctx: context item
        :param text: text to append timestamp to
        :param type: NODE_INPUT or NODE_OUTPUT
        :return: text with timestamp
        """
        if ctx is not None and ctx.input_timestamp is not None:
            timestamp = None
            if type == self.renderer.NODE_INPUT:
                timestamp = ctx.input_timestamp
            elif type == self.renderer.NODE_OUTPUT:
                timestamp = ctx.output_timestamp
            if timestamp is not None:
                ts = datetime.fromtimestamp(timestamp)
                hour = ts.strftime("%H:%M:%S")
                text = f'<span class="ts">{hour}: </span>{text}'
        return text

    # ========================================
    # Private: message identity
    # ========================================

    def _get_agent_name(self, ctx: CtxItem) -> Optional[str]:
        """
        Resolve agent-provided name from ctx if available.

        This is used to force "fake personalize" on the UI:
        - when present and non-empty, we use this name,
        - optionally attach default avatar when enabled via config,
        - we set personalize flag to True in node payloads.
        """
        try:
            if hasattr(ctx, "get_agent_name"):
                name = ctx.get_agent_name()
                if isinstance(name, str):
                    name = name.strip()
                return name or None
        except Exception:
            pass
        return None

    def _resolve_avatar_fs_path(self, basename: str) -> Optional[str]:
        """
        Resolve avatar file system path preferring a local thumbnail named 'thumb_<basename>'.

        Returns:
        - Absolute path to thumbnail when exists,
        - Otherwise absolute path to original when exists,
        - Otherwise None.
        """
        if not basename:
            return None
        try:
            presets_dir = self.renderer.window.core.config.get_user_dir("presets")
            avatars_dir = os.path.join(presets_dir, "avatars")
            thumb = os.path.join(avatars_dir, f"thumb_{basename}")
            original = os.path.join(avatars_dir, basename)
            if os.path.exists(thumb):
                return thumb
            if os.path.exists(original):
                return original
        except Exception:
            pass
        return None

    def _output_identity(self, ctx: CtxItem) -> Tuple[str, Optional[str], bool]:
        """
        Resolve output identity (name, avatar file:// path) based on preset or ctx-provided agent name.

        :param ctx: context item
        :return: (name, avatar, personalize)
        """
        # 1) Agent-provided name override -> force personalize, optionally default avatar
        agent_name = self._get_agent_name(ctx)
        if agent_name:
            avatar = None
            try:
                pass
                # if self.window.core.config.get("agent.avatar.default", True) and os.path.exists(self._agent_avatar):
                    # avatar = f"{self._file_prefix}{self._agent_avatar}"
            except Exception:
                pass
            return agent_name, avatar, True

        # 2) Fallback to preset-based personalize
        meta = ctx.meta
        if meta is None:
            return "", None, False

        pid = self.renderer.session.get_or_create_pid(meta)
        default_name = self.state.pids[pid].name_bot if pid in self.state.pids else ""

        preset_id = meta.preset
        if not preset_id:
            return default_name, None, False

        preset = self.renderer.window.core.presets.get(preset_id)
        if preset is None or not preset.ai_personalize:
            return default_name, None, False

        name = preset.ai_name or default_name
        avatar = None
        if preset.ai_avatar:
            # prefer thumbnail URL if available
            avatar_fs = self._resolve_avatar_fs_path(preset.ai_avatar)
            if avatar_fs:
                avatar = f"{self.renderer._file_prefix}{avatar_fs}"
        return name, avatar, True

    def _show_output_identity(
            self,
            ctx: Optional[CtxItem],
            prev_ctx: Optional[CtxItem] = None
    ) -> bool:
        """
        Return True when the bot identity should be rendered for this output.

        A tool-call continuation is one visual assistant turn even though it is
        persisted as multiple context items. Keep the avatar/name on the first
        item which starts the tool chain and suppress it on every internal reply
        that follows, including subsequent tool calls and the final response.

        ``ctx.prev_ctx`` is used by live/stream paths where an explicit previous
        item is not passed to the renderer. History rendering passes ``prev_ctx``
        directly, so the same rule also works after a context reload.

        :param ctx: Current context item
        :param prev_ctx: Previous context item, if already known
        :return: True if avatar/name may be shown
        """
        if ctx is None:
            return True

        previous = prev_ctx
        if previous is None:
            try:
                previous = getattr(ctx, "prev_ctx", None)
            except Exception:
                previous = None

        if previous is not None and self.renderer.tools.is_tool_reply_transition(previous, ctx):
            return False
        return True
