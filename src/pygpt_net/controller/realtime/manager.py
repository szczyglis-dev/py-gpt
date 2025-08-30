#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

from typing import Optional

from pygpt_net.core.realtime.worker import RealtimeWorker, RealtimeOptions
from pygpt_net.item.ctx import CtxItem

class Manager:
    """
    Manager that mirrors chat.stream controller shape.

    Starts a RealtimeWorker and routes text events and lifecycle to the UI.
    Audio is forwarded by the main-thread via AUDIO_OUTPUT_CHUNK events.
    """
    def __init__(self, window=None):
        self.window = window
        self.worker: Optional[RealtimeWorker] = None
        self.ctx: Optional[CtxItem] = None
        self.provider: Optional[str] = None
        self.opts: Optional[RealtimeOptions] = None

    def start(
            self,
            ctx: CtxItem,
            opts: RealtimeOptions
    ):
        """
        Start realtime worker

        :param ctx: CtxItem
        :param opts: RealtimeOptions
        """
        self.ctx = ctx
        self.opts = opts
        self.provider = opts.provider

        worker = RealtimeWorker(self.window, ctx, opts)
        self.worker = worker
        self.window.core.debug.info(f"[realtime] Begin: provider={opts.provider}, model={opts.model}")
        self.window.threadpool.start(worker)

    def shutdown(self):
        """Shutdown realtime worker"""
        self.worker = None
