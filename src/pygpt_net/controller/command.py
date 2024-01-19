#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 02:00:00                  #
# ================================================== #

import json

from PySide6.QtCore import QObject, Signal

from pygpt_net.core.dispatcher import Event
from pygpt_net.core.worker import Worker


class WorkerSignals(QObject):
    finished = Signal(object)


class Command:
    def __init__(self, window=None):
        """
        Command  controller

        :param window: Window instance
        """
        self.window = window
        self.stop = False

    def dispatch(self, event: Event):
        """
        Dispatch cmd execute event (command execution)

        :param event: event object
        """
        self.dispatch_sync(event)
        # self.dispatch_async(event)  # TODO: async execution

    def dispatch_sync(self, event: Event):
        """
        Dispatch cmd event (command execution)

        :param event: event object
        """
        for id in self.window.core.plugins.get_ids():
            if self.window.controller.plugins.is_enabled(id):
                if event.stop or (event.name == Event.CMD_EXECUTE and self.is_stop()):
                    if self.is_stop():
                        self.stop = False  # unlock needed here
                    break
                self.window.core.dispatcher.apply(id, event, is_async=False)

        # WARNING: do not emit finished signal here if event is internal (otherwise it will be emitted twice)
        # it is handled already in internal event, in synchronous way
        if event.ctx is not None and event.ctx.internal:
            return

        self.handle_finished(event)  # emit finished signal only for non-internal events

    def dispatch_async(self, event: Event):
        """
        Dispatch cmd event (command execution)

        :param event: event object
        """
        worker = Worker(self.worker)
        worker.signals = WorkerSignals()
        worker.signals.finished.connect(self.handle_finished)
        worker.kwargs['event'] = event
        worker.kwargs['window'] = self.window
        worker.kwargs['finished_signal'] = worker.signals.finished
        self.window.threadpool.start(worker)

    def worker(self, event: Event, window, finished_signal: Signal):
        """
        Command worker callback

        :param event: event object
        :param window: Window instance
        :param finished_signal: WorkerSignals: finished signal
        """
        for id in window.core.plugins.get_ids():
            if window.controller.plugins.is_enabled(id):
                if event.stop or (event.name == Event.CMD_EXECUTE and self.is_stop()):
                    if self.is_stop():
                        self.stop = False  # unlock needed here
                    break
                window.core.dispatcher.apply(id, event, is_async=True)
        finished_signal.emit(event)

    def is_stop(self):
        """
        Check if stop is requested

        :return: True if stop is requested
        :rtype: bool
        """
        return self.stop

    def handle_debug(self, data):
        """
        Handle thread debug log

        :param data
        """
        self.window.controller.debug.log(str(data))

    def handle_finished(self, event: Event):
        """
        Handle thread command execution finish

        :param event: event object
        """
        ctx = event.ctx
        self.window.ui.status("")  # Clear status
        if ctx.reply:
            self.window.controller.chat.input.send(json.dumps(ctx.results), force=True, internal=ctx.internal)

