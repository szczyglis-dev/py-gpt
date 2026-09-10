#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 18:55:00                  #
# ================================================== #

from typing import Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_EXPERT,
    TOOL_EXPERT_CALL_NAME,
)
from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.item.ctx import CtxItem


class Experts:
    def __init__(self, window=None):
        """
        Experts controller

        :param window: Window instance
        """
        self.window = window
        self.is_stop = False

    def append_prompts(
            self,
            mode: str,
            sys_prompt: str,
    ) -> str:
        """
        Append prompt to the window

        :param mode: Mode
        :param sys_prompt: Prompt text
        :return: Updated system prompt
        """
        core = self.window.core
        controller = self.window.controller

        # if agent enabled
        if controller.agent.legacy.enabled():
            prev_prompt = sys_prompt
            # Upgrade the historical self-dialogue default at runtime while
            # preserving genuinely custom user prompts. This avoids a config
            # migration and makes existing installations use the new loop.
            sys_prompt = controller.agent.legacy.normalize_instruction_prompt(
                core.prompt.get("agent.instruction")
            )
            if prev_prompt is not None and prev_prompt.strip() != "":
                sys_prompt = sys_prompt + "\n\n" + prev_prompt  # append previous prompt

        # if expert or agent mode
        if self.enabled() or controller.agent.legacy.enabled(check_inline=False):  # master expert has special prompt
            if controller.agent.legacy.enabled():  # if agent then leave agent prompt
                sys_prompt += "\n\n" + core.experts.get_prompt()  # both, agent + experts
            else:
                sys_prompt = core.experts.get_prompt()
                # mode = "chat"  # change mode to chat for expert

        # if global mode is agent
        if mode == MODE_AGENT:
            sys_prompt = controller.agent.legacy.on_system_prompt(
                sys_prompt,
                append_prompt=None,  # sys prompt from preset is used here
                auto_stop=core.config.get('agent.auto_stop'),
            )

        return sys_prompt

    def _get_expert_tool_calls(self, ctx: CtxItem, mentions: dict) -> list:
        """Return provider-shaped expert_call records for durable UI tasks."""
        calls = []

        # Preserve native provider identifiers when the call arrived natively.
        for call in list(getattr(ctx, "tool_calls", None) or []):
            if not isinstance(call, dict):
                continue
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            if str(fn.get("name") or "") == TOOL_EXPERT_CALL_NAME:
                calls.append(call)
        if calls:
            return calls

        # Legacy/non-native calls have already been normalized to cmds_before by
        # chat.output.handle_after(). Rebuild only the expert subset as structured
        # task records; these are display-only and are not injected into provider
        # history by record_tool_calls().
        source_cmds = list(getattr(ctx, "cmds_before", None) or getattr(ctx, "cmds", None) or [])
        for cmd in source_cmds:
            if not isinstance(cmd, dict) or str(cmd.get("cmd") or "") != TOOL_EXPERT_CALL_NAME:
                continue
            params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
            expert_id = params.get("id")
            if expert_id is not None and str(expert_id) not in {str(value) for value in mentions.keys()}:
                continue
            calls.append({
                "type": "function",
                "function": {
                    "name": TOOL_EXPERT_CALL_NAME,
                    "arguments": dict(params),
                },
            })

        # Compatibility fallback for older contexts which expose only extracted
        # mentions at this point.
        if not calls:
            for expert_id, query in mentions.items():
                calls.append({
                    "type": "function",
                    "function": {
                        "name": TOOL_EXPERT_CALL_NAME,
                        "arguments": {"id": expert_id, "query": query},
                    },
                })
        return calls

    def _begin_expert_tool_ui(self, ctx: CtxItem, mentions: dict) -> None:
        """Show expert-as-tool waiting state and persist its future Tool button."""
        calls = self._get_expert_tool_calls(ctx, mentions)
        if not calls:
            return

        # Expert replies use their historical Experts round-trip rather than a
        # provider-native function_call_output message. Keep these tasks UI-only
        # so history projection cannot manufacture a second tool protocol turn.
        self.window.core.ctx.record_tool_calls(
            ctx,
            calls,
            update_legacy_cache=False,
            ui_visible=True,
            provider_history=False,
        )
        self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {
            "meta": ctx.meta,
            "ctx": ctx,
        }))
        self.window.dispatch(RenderEvent(RenderEvent.TOOL_BEGIN, {
            "meta": ctx.meta,
            "ctx": ctx,
            "tool_names": [TOOL_EXPERT_CALL_NAME for _ in calls],
        }))

    def handle(self, ctx: CtxItem) -> int:
        """
        Handle mentions (calls) to experts

        :param ctx: CtxItem
        :return: Number of calls made to experts
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        log = self.log
        stream = core.config.get('stream')
        num_calls = 0

        # extract expert mentions
        if self.enabled() or controller.agent.legacy.enabled(check_inline=False):
            # re-send to master
            if ctx.sub_reply:
                core.ctx.update_item(ctx)
                core.experts.reply(ctx)
            else:
                # abort if reply
                if ctx.reply:
                    return num_calls

                # call experts
                mentions = core.experts.extract_calls(ctx, prepared=True)

                if mentions:
                    log("Calling experts...")
                    dispatch(RenderEvent(RenderEvent.END, {
                        "meta": ctx.meta,
                        "ctx": ctx,
                        "stream": stream,
                    }))  # close previous render

                    # The legacy <tool>{...}</tool> payload has already been
                    # stripped from visible text. Replace it with the same waiting
                    # status/Tool accordion lifecycle used by ordinary tool calls.
                    self._begin_expert_tool_ui(ctx, mentions)

                    for expert_id in mentions:
                        if not core.experts.exists(expert_id):
                            log(f"Expert not found: {expert_id}")
                            continue

                        log(f"Calling: {expert_id}")
                        ctx.sub_calls += 1

                        # add to reply stack
                        reply = ReplyContext()
                        reply.type = ReplyContext.EXPERT_CALL
                        reply.ctx = ctx
                        reply.parent_id = expert_id
                        reply.input = mentions[expert_id]

                        # send to kernel
                        context = BridgeContext()
                        context.ctx = ctx
                        context.reply_context = reply
                        dispatch(KernelEvent(KernelEvent.AGENT_CALL, {
                            'context': context,
                            'extra': {},
                        }))
                        num_calls += 1

        return num_calls

    def enabled(self, check_inline: bool = True) -> bool:
        """
        Check if experts are enabled

        :param check_inline: check inline mode
        :return: True if experts are enabled
        """
        modes = [MODE_EXPERT]
        mode = self.window.core.config.get('mode')
        if not check_inline:
            return mode in modes
        else:
            return mode in modes or self.window.controller.plugins.is_type_enabled("expert")

    def stopped(self) -> bool:
        """
        Check if experts are stopped

        :return: True if experts are stopped
        """
        return self.is_stop

    def stop(self):
        """Stop experts"""
        self.is_stop = True

    def unlock(self):
        """Unlock experts"""
        self.is_stop = False

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)