#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 21:15:00                  #
# ================================================== #

from __future__ import annotations

from ..utils import result_text


class TurnCompletion:
    """Resolve the authoritative answer, then accept its stream or deliver it once."""

    def __init__(self, runtime, emitter):
        self.runtime = runtime
        self.emitter = emitter

    async def complete(self, handler, prepared):
        runtime = self.runtime
        if runtime.is_stopped():
            return
        if not runtime.finished:
            result = await handler
            runtime.artifacts.collect_from_llm(
                getattr(prepared.agent, "llm", None) or prepared.llm,
                response=result,
                actor_id="orchestrator",
            )
            fallback = result_text(result)
            runtime.verbose.text(runtime.main_event("RESULT"), fallback)
            already_streamed = self._resolve_answer(prepared.agent, fallback)
            runtime.finished = True
            await self._deliver_answer(already_streamed)
        runtime.verbose.text(runtime.main_event("FINAL TEXT"),
                             runtime.final_answer or runtime.timeline.last_output())

    # ========================================
    # Answer policy
    # ========================================

    def _resolve_answer(self, agent, fallback):
        runtime = self.runtime
        exhausted = getattr(agent, "iteration_limit_reached", False) is True
        stalled = getattr(agent, "stalled", False) is True
        if exhausted or stalled:
            reason = "Iteration limit reached" if exhausted else "Agent repeated an unchanged checkpoint"
            runtime.final_answer = reason + "; task may be incomplete.\n\n" + fallback
            return False
        if runtime.uses_workflow_finish:
            return self._resolve_workflow_answer(fallback)
        runtime.final_answer = runtime.timeline.resolve_final(fallback) or "OK"
        runtime.verbose.text("PRIMARY AGENT RESOLVED FINAL", runtime.final_answer)
        runtime.timeline.detach_final_suffix(runtime.final_answer)
        return self._matches_last_output()

    def _resolve_workflow_answer(self, fallback):
        runtime = self.runtime
        if runtime.workflow.final_requested:
            streamed = runtime.timeline.final_output()
            runtime.final_answer = (streamed or runtime.timeline.resolve_final(fallback)
                                    or runtime.workflow.final_hint or fallback or "OK")
            return bool(runtime.workflow.final_stream_started and streamed)
        runtime.final_answer = fallback or runtime.timeline.last_output() or "OK"
        return self._matches_last_output()

    def _matches_last_output(self):
        last_output = self.runtime.timeline.last_output()
        return bool(last_output and self.runtime.final_answer.strip() == last_output.strip())

    # ========================================
    # Delivery
    # ========================================

    async def _deliver_answer(self, already_streamed):
        if already_streamed:
            self.runtime.timeline.mark_final()
            self.emitter.accept_streamed_final()
            return
        part = self.runtime.timeline.prepare_final()
        await self.emitter.stream_final(
            self.runtime.final_answer,
            part_uuid=getattr(part, "uuid", None) if part is not None else None,
        )
