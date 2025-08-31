#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 04:00:00                  #
# ================================================== #

from typing import Optional, Callable

import os
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from ..shared import compute_envelope_from_file

class NativePlayer(QObject):
    """
    Thin wrapper around QtMultimedia audio playback with level metering.
    """
    def __init__(self, window=None, chunk_ms: int = 10):
        super().__init__(window)
        self.window = window
        self.chunk_ms = int(chunk_ms)
        self.audio_output: Optional[QAudioOutput] = None
        self.player: Optional[QMediaPlayer] = None
        self.playback_timer: Optional[QTimer] = None
        self.volume_timer: Optional[QTimer] = None
        self.envelope = []

    def stop_timers(self):
        """Stop playback timers."""
        if self.playback_timer is not None:
            self.playback_timer.stop()
            self.playback_timer = None
        if self.volume_timer is not None:
            self.volume_timer.stop()
            self.volume_timer = None

    def stop(self, signals=None):
        """
        Stop playback and timers.

        :param signals: Signals to emit on stop
        """
        if self.player is not None:
            try:
                self.player.stop()
            except Exception:
                pass
        self.stop_timers()
        if signals is not None:
            try:
                signals.volume_changed.emit(0)
            except Exception:
                pass

    def update_volume(self, signals=None):
        """
        Update the volume based on the current position in the audio file.

        :param signals: Signals to emit volume changes
        """
        if not self.player:
            return
        pos = self.player.position()
        index = int(pos / self.chunk_ms)
        volume = self.envelope[index] if index < len(self.envelope) else 0
        if signals is not None:
            signals.volume_changed.emit(volume)

    def play_after(
        self,
        audio_file: str,
        event_name: str,
        stopped: Callable[[], bool],
        signals=None,
        auto_convert_to_wav: bool = False,
        select_output_device: Optional[Callable[[], object]] = None,
    ):
        """
        Start audio playback using QtMultimedia with periodic volume updates.

        :param audio_file: Path to audio file
        :param event_name: Event name to emit on playback start
        :param stopped: Callable returning True when playback should stop
        :param signals: Signals to emit on playback
        :param auto_convert_to_wav: auto convert mp3 to wav if True
        :param select_output_device: callable returning QAudioDevice for output
        """
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)

        if callable(select_output_device):
            try:
                self.audio_output.setDevice(select_output_device())
            except Exception:
                pass

        if auto_convert_to_wav and audio_file.lower().endswith('.mp3'):
            tmp_dir = self.window.core.audio.get_cache_dir()
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            dst_file = os.path.join(tmp_dir, "_" + base_name + ".wav")
            wav_file = self.window.core.audio.mp3_to_wav(audio_file, dst_file)
            if wav_file:
                audio_file = wav_file

        def check_stop():
            if stopped():
                self.stop(signals=signals)
            else:
                if self.player:
                    if self.player.playbackState() == QMediaPlayer.StoppedState:
                        self.stop(signals=signals)

        self.envelope = compute_envelope_from_file(audio_file, chunk_ms=self.chunk_ms)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(audio_file))
        self.player.play()

        self.playback_timer = QTimer()
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(check_stop)

        self.volume_timer = QTimer(self)
        self.volume_timer.setInterval(10)
        self.volume_timer.timeout.connect(lambda: self.update_volume(signals))

        self.playback_timer.start()
        self.volume_timer.start()
        if signals is not None:
            signals.volume_changed.emit(0)
            signals.playback.emit(event_name)