#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 23:55:00                  #
# ================================================== #

import copy
import threading

from PySide6.QtCore import Signal, Slot

from pygpt_net.core.agents_v2.expert import ExpertAgentBridge
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event
from pygpt_net.core.types import MODE_EXPERT, TOOL_EXPERT_CALL_NAME
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.signals import BaseSignals
from pygpt_net.plugin.base.worker import BaseWorker
from pygpt_net.utils import trans


class ExpertWorkerSignals(BaseSignals):
    """Base plugin signals plus Qt-thread event forwarding for Agents v2 tools."""

    event = Signal(object)
    event_sync = Signal(object, object)


class ExpertWorker(BaseWorker):
    """Execute expert_call commands as ordinary plugin tool calls."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = ExpertWorkerSignals()

    @Slot()
    def run(self):
        responses = []
        try:
            for item in list(self.cmds or []):
                if self.window.controller.kernel.stopped():
                    break
                if item.get("cmd") != TOOL_EXPERT_CALL_NAME:
                    continue

                params = item.get("params") if isinstance(item.get("params"), dict) else {}
                request = {
                    "cmd": TOOL_EXPERT_CALL_NAME,
                    "params": copy.deepcopy(params),
                }
                try:
                    result = self._call_expert(params)
                except Exception as e:
                    self.window.core.debug.log(e)
                    result = f"{trans('expert.wait.failed')}: {e}"

                responses.append({
                    "request": request,
                    "result": str(result),
                })

            if responses and not self.window.controller.kernel.stopped():
                self.reply_more(responses)
        finally:
            self.cleanup()

    def _dispatch_sync(self, event):
        """Dispatch a prompt hook on the Qt thread and wait for mutations."""
        if self.window.controller.kernel.is_main_thread():
            self.window.dispatch(event)
            return
        done = threading.Event()
        self.signals.event_sync.emit(event, done)
        done.wait()

    def _call_expert(self, params: dict) -> str:
        master_ctx = self.ctx
        if master_ctx is None:
            raise RuntimeError("Missing master context for expert_call.")

        expert_id = str(params.get("id") or "").strip()
        instruction = str(params.get("instruction") or params.get("query") or "").strip()
        system_prompt_extra = str(params.get("system_prompt") or "").strip()
        if not expert_id:
            raise ValueError("Expert ID is empty.")
        if not instruction:
            raise ValueError("Expert instruction is empty.")

        available = self.window.core.experts.get_experts()
        expert = available.get(expert_id)
        if expert is None:
            raise RuntimeError(f"Expert preset is not available: {expert_id}")

        model = expert.model
        model_data = self.window.core.models.get(model)
        if model_data is None:
            raise RuntimeError(f"Expert model is not configured: {model}")

        name = str(expert.name or expert_id)
        self.status(f"{trans('expert.wait.status')} ({name})")

        # Persistent Expert memory is kept only in the hidden slave meta. Nothing
        # from this context is inserted into the visible master conversation.
        slave = self.window.core.ctx.get_or_create_slave_meta(master_ctx, expert_id)
        ctx = CtxItem()
        ctx.meta = slave
        ctx.internal = False
        ctx.hidden = True
        ctx.current = True
        ctx.mode = MODE_EXPERT
        ctx.model = model
        ctx.set_input(instruction, "")
        ctx.set_output(None, name)
        ctx.sub_call = True
        ctx.agent_call = True
        ctx.use_agent_final_response = True
        ctx.pid = master_ctx.pid
        self.window.core.ctx.provider.append_item(slave, ctx)

        try:
            bridge = ExpertAgentBridge(self.window, self.signals)
            raw_system_prompt = bridge.compose_system_prompt(expert.prompt, system_prompt_extra)

            # Keep the same prompt extension hooks used by the rest of the app.
            event = Event(Event.PRE_PROMPT, {
                "mode": MODE_EXPERT,
                "value": raw_system_prompt,
                "is_expert": True,
            })
            event.ctx = ctx
            self._dispatch_sync(event)
            raw_system_prompt = event.data["value"]

            system_prompt = self.window.core.prompt.prepare_sys_prompt(
                MODE_EXPERT,
                model_data,
                raw_system_prompt,
                ctx,
                True,
                False,
                is_expert=True,
            )

            for event_name in (Event.POST_PROMPT_ASYNC, Event.POST_PROMPT_END):
                event = Event(event_name, {
                    "mode": MODE_EXPERT,
                    "reply": ctx.reply,
                    "value": system_prompt,
                })
                event.ctx = ctx
                self._dispatch_sync(event)
                system_prompt = event.data["value"]

            db_idx = expert.idx
            if not self.window.core.idx.is_valid(db_idx):
                db_idx = None

            history = self.window.core.ctx.all(meta_id=slave.id)
            bridge_context = BridgeContext(
                ctx=ctx,
                history=history,
                mode=MODE_EXPERT,
                parent_mode=getattr(master_ctx, "mode", None) or self.window.core.config.get("mode"),
                model=model_data,
                system_prompt=system_prompt,
                system_prompt_raw=raw_system_prompt,
                prompt=instruction,
                stream=False,
                attachments=[],
                file_ids=[],
                assistant_id=self.window.core.config.get("assistant"),
                idx=db_idx,
                idx_mode=self.window.core.config.get("llama.idx.mode"),
                external_functions=[],
                tools_outputs=[],
                max_tokens=self.window.core.config.get("max_output_tokens"),
                is_expert_call=True,
                preset=expert,
            )

            result = bridge.call(bridge_context, instruction)
            if not result:
                raise RuntimeError("No response from expert.")

            ctx.output = str(result)
            return str(result)
        finally:
            ctx.current = False
            ctx.reply = False
            self.window.core.ctx.update_item(ctx)
            self.status("")
