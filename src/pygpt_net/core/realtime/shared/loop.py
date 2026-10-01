#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Optional

class BackgroundLoop:
    """
    Dedicated background asyncio loop running in its own thread.
    Safe cross-thread scheduling and sync wrappers.
    """
    def __init__(self, name: str = "RT-Loop"):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._name = name

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self._loop

    def ensure(self):
        if self._loop and self._loop.is_running():
            return
        self._loop = asyncio.new_event_loop()

        def _runner(loop: asyncio.AbstractEventLoop):
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                # Do not leave websocket/tasks attached to an unclosed loop on
                # application shutdown. Give cancelled tasks one short drain pass.
                try:
                    pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.wait(pending, timeout=0.5))
                except Exception:
                    pass
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_runner, args=(self._loop,), name=self._name, daemon=True)
        self._thread.start()

    async def run(self, coro):
        if not self._loop:
            raise RuntimeError("Owner loop is not running")
        cfut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return await asyncio.wrap_future(cfut)

    def run_sync(self, coro, timeout: float = 5.0):
        if not self._loop or not self._loop.is_running():
            return None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return fut.result(timeout=timeout)
        except FutureTimeoutError:
            # A synchronous realtime call that has timed out must not remain queued
            # on the owner loop. Otherwise stale microphone chunks/commits can run
            # later, after a lock is released, and contaminate a subsequent turn.
            fut.cancel()
            return None
        except Exception:
            return None

    def stop(self, timeout: float = 2.0):
        loop, thread = self._loop, self._thread
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._loop = None
        self._thread = None