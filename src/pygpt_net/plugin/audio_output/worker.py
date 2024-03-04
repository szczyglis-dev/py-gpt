#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.04 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    playback = Signal(object)
    stop = Signal()


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.text = None

    @Slot()
    def run(self):
        from pygame import mixer
        try:
            path = self.plugin.get_provider().speech(self.text)
            if path:
                mixer.init()
                playback = mixer.Sound(path)
                self.stop_playback()  # stop previous playback
                playback.play()
                self.send(playback)  # send playback object to main thread
        except Exception as e:
            self.error(e)

    def send(self, playback):
        """
        Send playback object to main thread

        :param playback: playback object
        """
        self.signals.playback.emit(playback)

    def stop_playback(self):
        """Stop audio playback"""
        self.stop()

    def stop(self):
        """Send stop signal to main thread"""
        self.signals.stop.emit()



