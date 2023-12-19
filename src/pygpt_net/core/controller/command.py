#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.19 22:00:00                  #
# ================================================== #
import json
import threading

from PySide6.QtCore import QObject, Signal, Slot


class Command:
    def __init__(self, window=None):
        """
        Command  controller

        :param window: Window instance
        """
        self.window = window
        self.thread = None
        self.thread_started = False
        self.force_stop = False

    def dispatch_async(self, event):
        """
        Handle thread start

        :param event: event object
        """
        worker = CommandThread(window=self.window, event=event)
        worker.finished.connect(self.handle_finished)
        worker.destroyed.connect(self.handle_destroy)

        self.thread = threading.Thread(target=worker.run)
        self.thread.start()
        self.thread_started = True

    def is_stop(self):
        """
        Check if stop is requested

        :return: true if stop is requested
        :rtype: bool
        """
        return self.force_stop

    @Slot(object)
    def handle_finished(self, event):
        ctx = event.ctx
        if ctx.reply:
            self.window.controller.input.send(json.dumps(ctx.results))
        self.thread_started = False

    @Slot()
    def handle_destroy(self):
        self.thread_started = False


class CommandThread(QObject):
    finished = Signal(object)
    destroyed = Signal()

    def __init__(self, window=None, event=None):
        """
        Run commands dispatch thread

        :param window: Window instance
        :param event: event object
        """
        super().__init__()
        self.window = window
        self.event = event

    def run(self):
        """Run thread"""
        print("Starting commands thread...")
        try:
            for id in self.window.app.plugins.plugins:
                if self.window.controller.plugins.is_enabled(id):
                    if self.event.stop or self.window.controller.command.is_stop():
                        break
                    self.window.app.dispatcher.dispatch(id, self.event)
            self.window.set_status("")  # Clear status
            self.finished.emit(self.event)
        except Exception as e:
            print(e)
        self.destroyed.emit()
        print("Commands thread finished.")
