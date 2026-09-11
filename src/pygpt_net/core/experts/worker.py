#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 21:45:00                  #
# ================================================== #

from PySide6.QtCore import QRunnable, QObject, Signal, Slot

from pygpt_net.core.agents_v2.expert import ExpertAgentBridge
from pygpt_net.core.types import MODE_EXPERT
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, RenderEvent
from pygpt_net.item.ctx import CtxItem


class WorkerSignals(QObject):
    """Signals for worker to communicate with main thread."""
    finished = Signal()
    response = Signal(object, str)
    error = Signal(str)
    event = Signal(object)
    output = Signal(object, str)
    lock_input = Signal()
    cmd = Signal(object, object, str, str, str)


class ExpertWorker(QRunnable):
    """Run an Expert preset as a headless Agents v2 agent."""

    def __init__(self, window, master_ctx: CtxItem, expert_id: str, request=None, query=None):
        super().__init__()
        self.window = window
        self.master_ctx = master_ctx
        self.expert_id = expert_id
        if request is None:
            request = query  # compatibility with pre-2.8.16 direct callers/tests
        if isinstance(request, dict):
            self.instruction = str(request.get("instruction") or request.get("query") or "").strip()
            self.system_prompt = str(request.get("system_prompt") or "").strip()
        else:
            self.instruction = str(request or "").strip()
            self.system_prompt = ""
        self.query = self.instruction  # legacy attribute kept for compatibility
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        master_ctx = self.master_ctx
        expert_id = self.expert_id
        instruction = self.instruction

        try:
            slave = self.window.core.ctx.get_or_create_slave_meta(master_ctx, expert_id)
            expert = self.window.core.experts.get_expert(expert_id)
            if expert is None:
                raise RuntimeError(f"Expert preset not found: {expert_id}")
            # Expert memory lives only in the child/slave meta and is not rendered
            # as a regular conversation turn in the main context.
            hidden = True
            base_mode = self.window.core.config.get("mode")
            model = expert.model
            expert_name = expert.name
            model_data = self.window.core.models.get(model)
            if model_data is None:
                raise RuntimeError(f"Expert model is not configured: {model}")
            if not instruction:
                raise ValueError("Expert instruction is empty.")

            ctx = CtxItem()
            ctx.meta = slave
            ctx.internal = False
            ctx.hidden = hidden
            ctx.current = True
            ctx.mode = MODE_EXPERT
            ctx.model = model
            ctx.set_input(instruction, "")
            ctx.set_output(None, expert_name)
            ctx.sub_call = True
            ctx.agent_call = True
            ctx.use_agent_final_response = True
            ctx.pid = master_ctx.pid

            event = RenderEvent(RenderEvent.BEGIN, {
                "meta": ctx.meta,
                "ctx": ctx,
                "stream": False,
            })
            self.signals.event.emit(event)
            self.window.core.ctx.provider.append_item(slave, ctx)

            bridge = ExpertAgentBridge(self.window, self.signals)
            raw_system_prompt = bridge.compose_system_prompt(expert.prompt, self.system_prompt)
            event = Event(Event.PRE_PROMPT, {
                "mode": MODE_EXPERT,
                "value": raw_system_prompt,
                "is_expert": True,
            })
            self.signals.event.emit(event)
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

            # Match the final prompt stages used by BridgeWorker/Chat with Agents.
            # Plugins such as Real Time and Files I/O append runtime-only context
            # here; Experts must receive the same additions before Agents v2 starts.
            for event_name in (Event.POST_PROMPT_ASYNC, Event.POST_PROMPT_END):
                event = Event(event_name, {
                    "mode": MODE_EXPERT,
                    "reply": ctx.reply,
                    "value": system_prompt,
                })
                event.ctx = ctx
                self.window.dispatch(event)
                system_prompt = event.data["value"]

            db_idx = expert.idx
            if self.window.core.idx.is_valid(db_idx):
                self.window.core.experts.last_idx = db_idx
            else:
                self.window.core.experts.last_idx = None
                db_idx = None

            history = self.window.core.ctx.all(meta_id=slave.id)
            bridge_context = BridgeContext(
                ctx=ctx,
                history=history,
                mode=MODE_EXPERT,
                parent_mode=base_mode,
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

            self.signals.lock_input.emit()
            result = bridge.call(bridge_context, instruction)
            if not result:
                self.signals.error.emit("No response from expert.")
                return

            ctx.current = False
            ctx.output = result
            ctx.reply = False
            self.window.core.ctx.update_item(ctx)

            reply_ctx = CtxItem()
            reply_ctx.from_dict(ctx.to_dict())
            reply_ctx.meta = master_ctx.meta
            reply_ctx.output = result
            reply_ctx.input_name = expert_name
            reply_ctx.output_name = ""
            reply_ctx.cmds = []
            reply_ctx.sub_call = True
            self.signals.response.emit(reply_ctx, str(expert_id))

        except Exception as e:
            self.window.core.debug.log(e)
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
            self.cleanup()

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass
