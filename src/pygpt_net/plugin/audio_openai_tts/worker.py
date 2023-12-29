#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 03:00:00                  #
# ================================================== #

import pygame

from PySide6.QtCore import QRunnable, Slot, QObject, Signal


class WorkerSignals(QObject):
    playback = Signal(object)
    stop = Signal()
    status = Signal(object)
    error = Signal(object)


class Worker(QRunnable):
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
        self.stop()  # stop previous playback
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
            self.signals.playback.emit(playback)  # send playback object to main thread
            self.signals.status.emit('')
        except Exception as e:
            self.signals.error.emit(e)

    def stop(self):
        """Stop TTS thread"""
        self.signals.status.emit('')
        self.signals.stop.emit()



