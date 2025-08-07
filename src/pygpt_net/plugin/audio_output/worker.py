#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.07 03:00:00                  #
# ================================================== #

import time

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    volume_changed = Signal(float)  # Emits the volume level
    playback = Signal(str)
    stop = Signal()
    error_playback = Signal(object)


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.text = None
        self.event = None
        self.cache_file = None  # path to cache file
        self.mode = "generate"  # generate|playback
        self.audio_file = None
        self.is_stopped = False
        self.p = None
        self.stream = None

    @Slot()
    def run(self):
        try:
            if self.mode == "generate":
                self.generate()
            elif self.mode == "playback":
                self.play()
        except Exception as e:
            self.error(e)
        finally:
            self.on_destroy()

    def on_destroy(self):
        """Handle destroyed event."""
        self.p = None
        self.stream = None
        self.is_stopped = True
        self.event = None
        self.cleanup()

    def generate(self):
        """Generate and play audio file"""
        if self.text is None or self.text == "":
            time.sleep(0.2)  # wait
            return
        path = self.plugin.get_provider().speech(self.text)
        if path:
            self.play_audio(path)
            # store in cache if enabled
            if self.cache_file:
                self.cache_audio_file(path, self.cache_file)

    def play(self):
        """Play audio file only"""
        if self.audio_file:
            self.play_audio(self.audio_file)

    def play_audio(self, audio_file: str):
        """
        Play audio file using PyAudio

        :param audio_file: audio file path
        """
        try:
            self.plugin.window.core.audio.output.play(
                audio_file=audio_file,
                event_name=self.event,
                stopped=self.stopped,
                signals=self.signals
            )
        except Exception as e:
            self.signals.volume_changed.emit(0)
            self.signals.error_playback.emit(e)

    def cache_audio_file(self, src: str, dst: str):
        """
        Store audio file in cache

        :param src: source path
        :param dst: destination path
        """
        import shutil
        try:
            shutil.copy(src, dst)
            # print("Cached audio file:", dst)
        except Exception as e:
            self.error(e)

    def send(self, playback):
        """
        Send playback object to main thread

        :param playback: playback object
        """
        self.signals.playback.emit(playback, self.event)

    def stop_playback(self):
        """Stop audio playback"""
        self.stop()

    def stop(self):
        """Send stop signal to main thread"""
        self.is_stopped = True

    def stopped(self) -> bool:
        """
        Check if playback is stopped

        :return: True if stopped
        """
        return self.is_stopped
