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

import io
import threading
import wave as _wave

from PySide6.QtCore import QTimer

class _FilePlaybackThread(threading.Thread):
    """
    File playback worker that owns its PyAudio instance and stream.
    All creation and teardown happen inside this thread to avoid cross-thread closes.
    """
    def __init__(self, device_index: int, audio_file: str, signals):
        """
        Initialize the playback thread.

        :param device_index: output device index
        :param audio_file: path to audio file
        :param signals: signals object to emit volume changes
        """
        super().__init__(daemon=True)
        self.device_index = int(device_index)
        self.audio_file = audio_file
        self.signals = signals
        self._stop_evt = threading.Event()

    def request_stop(self):
        """Ask the worker to stop gracefully."""
        self._stop_evt.set()

    def _emit_main(self, fn, *args):
        """
        Emit via Qt main thread.

        :param fn: function to call
        :param args: arguments to pass
        """
        try:
            QTimer.singleShot(0, lambda: fn(*args))
        except Exception:
            pass

    def run(self):
        """Thread entry point: play the audio file and emit volume changes."""
        import pyaudio
        import numpy as np
        from pydub import AudioSegment

        pa = None
        wf = None
        stream = None
        try:
            # prepare WAV in memory (normalize rate to 44100 to be safe)
            audio = AudioSegment.from_file(self.audio_file)
            audio = audio.set_frame_rate(44100)
            wav_io = io.BytesIO()
            audio.export(wav_io, format='wav')
            wav_io.seek(0)
            wf = _wave.open(wav_io, 'rb')

            pa = pyaudio.PyAudio()

            def _try_open(idx: int):
                s = pa.open(
                    format=pa.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                    output_device_index=idx,
                    frames_per_buffer=1024,
                )
                try:
                    s.start_stream()
                except Exception:
                    pass
                return s

            # open output; if the specific device fails, try fallbacks
            try:
                stream = _try_open(self.device_index)
            except Exception:
                # try default
                try:
                    di = pa.get_default_output_device_info()
                    stream = _try_open(int(di.get('index')))
                except Exception:
                    # scan first output-capable
                    for i in range(pa.get_device_count()):
                        try:
                            di = pa.get_device_info_by_index(i)
                            if di.get('maxOutputChannels', 0) > 0:
                                stream = _try_open(i)
                                break
                        except Exception:
                            continue

            if stream is None:
                return  # no device available

            # dtype for meter
            sw = wf.getsampwidth()
            if sw == 1:
                dtype = np.uint8
                max_value = 255.0
                offset = 128.0
                is_u8 = True
            elif sw == 2:
                dtype = np.int16
                max_value = 32767.0
                offset = 0.0
                is_u8 = False
            elif sw == 4:
                dtype = np.int32
                max_value = 2147483647.0
                offset = 0.0
                is_u8 = False
            else:
                dtype = np.int16
                max_value = 32767.0
                offset = 0.0
                is_u8 = False

            chunk = 1024
            data = wf.readframes(chunk)

            while data and not self._stop_evt.is_set():
                try:
                    stream.write(data)
                except Exception:
                    break

                # volume meter (emit on GUI thread)
                if self.signals is not None:
                    try:
                        arr = np.frombuffer(data, dtype=dtype).astype(np.float32)
                        if arr.size > 0:
                            if is_u8:
                                arr -= offset
                                denom = 127.0
                            else:
                                denom = max_value
                            rms = float(np.sqrt(np.mean(arr * arr)))
                            if denom > 0.0 and rms > 0.0:
                                db = 20.0 * float(np.log10(max(1e-12, rms / denom)))
                                db = max(-60.0, min(0.0, db))
                                vol = int(((db + 60.0) / 60.0) * 100.0)
                            else:
                                vol = 0
                        else:
                            vol = 0
                        self._emit_main(self.signals.volume_changed.emit, vol)
                    except Exception:
                        pass

                data = wf.readframes(chunk)

        finally:
            # teardown in the SAME thread
            try:
                if stream is not None:
                    try:
                        if stream.is_active():
                            stream.stop_stream()
                    except Exception:
                        pass
                    stream.close()
            except Exception:
                pass
            try:
                if pa is not None:
                    pa.terminate()
            except Exception:
                pass
            try:
                if wf is not None:
                    wf.close()
            except Exception:
                pass

            if self.signals is not None:
                try:
                    self._emit_main(self.signals.volume_changed.emit, 0)
                except Exception:
                    pass