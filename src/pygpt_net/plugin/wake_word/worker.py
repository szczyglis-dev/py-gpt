#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : PYGPT Contributors                   #
# Updated Date: 2026.03.11 00:00:00                  #
# ================================================== #

import time

import numpy as np
from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    wake_word_detected = Signal(str)


class WakeWordWorker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(WakeWordWorker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.model_paths = None
        self.threshold = 0.5
        self.cooldown_seconds = 3

    @Slot()
    def run(self):
        """Run wake word listener in background thread."""
        oww = None
        stream = None
        pa = None
        try:
            import openwakeword
            from openwakeword.model import Model as OWWModel
            import pyaudio

            # Load model
            openwakeword.utils.download_models()

            model_kwargs = {}
            if self.model_paths:
                model_kwargs["wakeword_models"] = self.model_paths
            oww = OWWModel(**model_kwargs)

            # Audio stream config
            chunk_size = 1280  # 80ms at 16kHz
            sample_rate = 16000

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk_size,
            )

            self.log("Wake word listener started")
            self.status("Listening for wake word...")

            last_detection_time = 0

            while self.plugin and self.plugin.listening and not self.is_stopped():
                try:
                    audio_data = stream.read(chunk_size, exception_on_overflow=False)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)

                    # Run prediction
                    prediction = oww.predict(audio_array)

                    for model_name, score in prediction.items():
                        if score >= self.threshold:
                            now = time.time()
                            if now - last_detection_time >= self.cooldown_seconds:
                                last_detection_time = now
                                self.log(
                                    "Wake word detected: {} (score: {:.2f})".format(
                                        model_name, score
                                    )
                                )
                                if self.signals is not None:
                                    self.signals.wake_word_detected.emit(model_name)
                                # Reset model state after detection
                                oww.reset()
                                break
                except OSError:
                    # Audio buffer overflow, skip
                    continue

        except ImportError as e:
            self.error(
                "Wake word dependencies not installed. "
                "Run: pip install openwakeword pyaudio. Error: {}".format(e)
            )
        except Exception as e:
            self.error(e)
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass
            self.log("Wake word listener stopped")
            self.status("")
            self.destroyed()
            self.cleanup()
