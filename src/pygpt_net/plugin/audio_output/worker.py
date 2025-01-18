#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.18 03:00:00                  #
# ================================================== #

import time
import pyaudio
import wave
import numpy as np
import io
from pydub import AudioSegment

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
            self.signals.playback.emit(self.event)
            audio = AudioSegment.from_file(audio_file)
            audio = audio.set_frame_rate(44100)  # resample to 44.1 kHz
            wav_io = io.BytesIO()
            audio.export(wav_io, format='wav')
            wav_io.seek(0)
            wf = wave.open(wav_io, 'rb')
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
                                      channels=wf.getnchannels(),
                                      rate=wf.getframerate(),
                                      output=True)

            sample_width = wf.getsampwidth()
            format = self.p.get_format_from_width(sample_width)

            if format == pyaudio.paInt8:
                dtype = np.int8
                max_value = 2 ** 7 - 1  # 127
                offset = 0
            elif format == pyaudio.paInt16:
                dtype = np.int16
                max_value = 2 ** 15 - 1  # 32767
                offset = 0
            elif format == pyaudio.paInt32:
                dtype = np.int32
                max_value = 2 ** 31 - 1  # 2147483647
                offset = 0
            elif format == pyaudio.paUInt8:
                dtype = np.uint8
                max_value = 2 ** 8 - 1  # 255
                offset = 128  # center unsigned data
            else:
                raise ValueError(f"Unsupported format: {format}")

            chunk_size = 512
            data = wf.readframes(chunk_size)

            while data != b'' and not self.is_stopped:
                self.stream.write(data)

                audio_data = np.frombuffer(data, dtype=dtype)
                if len(audio_data) > 0:
                    audio_data = audio_data.astype(np.float32)
                    if dtype == np.uint8:
                        audio_data -= offset

                    # compute RMS
                    rms = np.sqrt(np.mean(audio_data ** 2))

                    if rms > 0:
                        # RMS to decibels
                        db = 20 * np.log10(rms / max_value)

                        # define minimum and maximum dB levels
                        min_db = -60  # adjust as needed
                        max_db = 0

                        # clamp the db value to the range [min_db, max_db]
                        if db < min_db:
                            db = min_db
                        elif db > max_db:
                            db = max_db

                        # map decibel value to volume percentage
                        volume_percentage = ((db - min_db) / (max_db - min_db)) * 100
                    else:
                        volume_percentage = 0

                    # emit volume signal
                    self.signals.volume_changed.emit(volume_percentage)
                else:
                    # if empty audio_data
                    self.signals.volume_changed.emit(0)

                data = wf.readframes(chunk_size)

            # close the stream
            if self.stream is not None:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            if self.p is not None:
                self.p.terminate()
            wf.close()
            self.signals.volume_changed.emit(0)
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
