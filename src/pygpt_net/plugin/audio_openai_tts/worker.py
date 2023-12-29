#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

import pygame

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
        self.client = None
        self.model = None
        self.path = None
        self.text = None
        self.voice = None

    @Slot()
    def run(self):
        self.stop_playback()  # stop previous playback
        try:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=self.text
            )
            response.stream_to_file(self.path)
            pygame.mixer.init()
            playback = pygame.mixer.Sound(self.path)
            playback.play()
            self.send(playback)  # send playback object to main thread
            self.status('')
        except Exception as e:
            self.error(e)

    def send(self, playback):
        """Send playback object to main thread"""
        self.signals.playback.emit(playback)

    def stop_playback(self):
        """Stop audio playback"""
        self.status('')
        self.stop()

    def stop(self):
        """Send stop signal to main thread"""
        self.signals.stop.emit()



