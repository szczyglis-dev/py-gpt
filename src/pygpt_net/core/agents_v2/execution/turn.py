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

import asyncio
from .preparation import TurnPreparation
from .events import TurnEvents
from .completion import TurnCompletion
from .finalization import TurnFinalization


class AgentTurn:
    """The lifecycle of one user turn; each phase owns its implementation."""

    def __init__(self, runtime, emitter):
        self.preparation = TurnPreparation(runtime)
        self.events = TurnEvents(runtime, emitter)
        self.completion = TurnCompletion(runtime, emitter)
        self.finalization = TurnFinalization(runtime, emitter)
        self.emitter = emitter

    async def run(self, context):
        prepared = await self.preparation.prepare(context, self.emitter)
        stop_task = None
        try:
            handler = self.preparation.start(context, prepared)
            stop_task = asyncio.create_task(self.events.watch_stop(handler), name="agents-v2:stop-watch")
            await self.events.consume(handler)
            await self.completion.complete(handler, prepared)
        finally:
            await self.finalization.finish(prepared, self.events, stop_task)
