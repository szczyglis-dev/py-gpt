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
from typing import Optional

from .emitter import RuntimeEmitter
from .runtime import AgentsV2Runtime
from .execution.turn import AgentTurn


class Runner:
    """Execute one Agents v2 user turn inside the existing BridgeWorker thread."""

    def __init__(self, window=None):
        self.window = window
        self.last_error: Optional[Exception] = None
        # Debug inspector hooks. current_runtime is live only for an active turn;
        # last_runtime remains available after completion for post-run inspection.
        self.current_runtime = None
        self.last_runtime = None

    def get_error(self):
        return self.last_error

    def call(self, context, extra, signals) -> bool:
        self.last_error = None
        emitter = RuntimeEmitter(context, extra, signals)
        try:
            asyncio.run(self.run_turn(context, extra, signals, emitter))
            return True
        except asyncio.CancelledError:
            # Cancellation is a normal control path (Stop, or Orchestrator
            # workflow_finish), not an error.
            try:
                emitter.clear_status()
                emitter.finish()
            except Exception:
                pass
            return True
        except Exception as exc:
            self.last_error = exc
            self.window.core.debug.log(exc)
            try:
                # Close the Agents v2 stream cleanly, but do not turn an exception
                # into a successful/final assistant answer. Returning False lets
                # BridgeWorker route the stored exception through the normal chat
                # error path, which shows the frontend alert and unlocks the input.
                emitter.clear_status()
                emitter.finish()
            except Exception:
                pass
            return False
        finally:
            self.current_runtime = None

    async def run_turn(self, context, extra, signals, emitter: RuntimeEmitter):
        """Create the runtime and execute its prepared turn lifecycle."""
        runtime = AgentsV2Runtime(self.window, context, extra, signals, emitter)
        self.current_runtime = self.last_runtime = runtime
        runtime.debug_event_count = 0
        runtime.debug_event_types = {}
        await AgentTurn(runtime, emitter).run(context)
