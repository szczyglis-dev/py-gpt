#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import pygame
import requests

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
        self.api_key = None
        self.region = None
        self.text = None
        self.voice = None
        self.path = None

    @Slot()
    def run(self):
        try:
            url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
            }
            body = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' " \
                   f"xml:lang='en-US'><voice name='{self.voice}'>{self.text}</voice></speak>"
            response = requests.post(url, headers=headers, data=body.encode('utf-8'))
            if response.status_code == 200:
                with open(self.path, "wb") as file:
                    file.write(response.content)
                pygame.mixer.init()
                playback = pygame.mixer.Sound(self.path)
                self.stop_playback()  # stop previous playback
                playback.play()
                self.send(playback)  # send playback object to main thread
            else:
                msg = "Error: {} - {}".format(response.status_code, response.text)
                self.error(msg)
        except Exception as e:
            self.error(e)

    def send(self, playback):
        """Send playback object to main thread"""
        self.signals.playback.emit(playback)

    def stop_playback(self):
        """Stop audio playback"""
        self.stop()

    def stop(self):
        """Send stop signal to main thread"""
        self.signals.stop.emit()



