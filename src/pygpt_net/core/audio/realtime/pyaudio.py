#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

import threading
from typing import Optional

import numpy as np

from PySide6.QtCore import QTimer, QObject, Qt


class RealtimeSessionPyAudio(QObject):
    """
    Realtime PCM playback session using PyAudio in callback mode.
    Consumes already-converted PCM frames, keeps GUI responsive and emits volume updates.
    """

    def __init__(
            self,
            device_index: int,
            rate: int,
            channels: int,
            width_bytes: int = 2,
            parent: Optional[QObject] = None,
            volume_emitter: Optional[callable] = None,
    ):
        super().__init__(parent)
        import pyaudio  # local import to keep backend import-safe
        self._pa = pyaudio.PyAudio()
        self.device_index = int(device_index)
        self.rate = int(rate)
        self.channels = int(channels)
        self.width = int(width_bytes)
        self.frame_bytes = max(1, self.channels * self.width)
        self.bytes_per_ms = max(1, int(self.rate * self.frame_bytes / 1000))

        # choose PyAudio format from width
        self.pa_format = self._pa.get_format_from_width(
            self.width,
            unsigned=(self.width == 1)
        )

        # internal buffers/flags
        self._buffer = bytearray()
        self._buf_lock = threading.Lock()
        self._final = False
        self._tail_ms = 60  # add a small silence tail to avoid clicks

        # volume metering
        self._volume_emitter = volume_emitter
        self._vol_buffer = bytearray()
        self._vol_lock = threading.Lock()
        self._vol_timer = QTimer(self)
        self._vol_timer.setTimerType(Qt.PreciseTimer)
        self._vol_timer.setInterval(33)  # ~30 Hz meter
        self._vol_timer.timeout.connect(self._emit_volume_tick)
        self._vol_timer.start()

        # open callback-based output stream
        self._stream = self._pa.open(
            format=self.pa_format,
            channels=self.channels,
            rate=self.rate,
            output=True,
            output_device_index=self.device_index,
            stream_callback=self._callback,
            frames_per_buffer=max(256, int(self.rate / 100))  # ~10 ms
        )
        try:
            self._stream.start_stream()
        except Exception:
            pass

        # stop callback (set by backend)
        self.on_stopped = None

    def is_active(self) -> bool:
        """
        Return True if PortAudio stream is active.

        :return: True if active
        """
        try:
            return self._stream is not None and self._stream.is_active()
        except Exception:
            return False

    def is_finalized(self) -> bool:
        """
        Return True if session was marked final.

        :return: True if final
        """
        return bool(self._final)

    def feed(self, data: bytes) -> None:
        """
        Append PCM bytes (already in session/device format).

        :param data: bytes to append
        """
        if not data:
            return
        with self._buf_lock:
            self._buffer.extend(data)
        # push to volume window from the same bytes
        self._vol_push(data)

    def mark_final(self) -> None:
        """No more data will be supplied; add a small silence tail."""
        if not self._final:
            pad = self.bytes_per_ms * self._tail_ms
            pad -= (pad % self.frame_bytes)
            if pad > 0:
                with self._buf_lock:
                    self._buffer.extend(self._silence(pad))
        self._final = True

    def stop(self) -> None:
        """Stop playback and free resources."""
        try:
            if self._vol_timer:
                self._vol_timer.stop()
        except Exception:
            pass
        try:
            if self._stream and self._stream.is_active():
                self._stream.stop_stream()
        except Exception:
            pass
        try:
            if self._stream:
                self._stream.close()
        except Exception:
            pass
        try:
            if self._pa:
                self._pa.terminate()
        except Exception:
            pass

        # zero the meter
        try:
            if self._volume_emitter:
                self._volume_emitter(0)
        except Exception:
            pass

        self._stream = None
        self._pa = None

        cb = self.on_stopped
        self.on_stopped = None
        if cb:
            try:
                cb()
            except Exception:
                pass

        self.deleteLater()

    # ---- internal ----

    def _callback(self, in_data, frame_count, time_info, status):
        """
        PortAudio callback: deliver frames from buffer.

        :param in_data: input data (ignored)
        :param frame_count: number of frames requested
        :param time_info: timing info (ignored)
        :param status: status flags (ignored)
        """
        import pyaudio
        need = frame_count * self.frame_bytes
        out = b""
        with self._buf_lock:
            if len(self._buffer) >= need:
                out = bytes(self._buffer[:need])
                del self._buffer[:need]
            elif len(self._buffer) > 0:
                out = bytes(self._buffer)
                self._buffer.clear()

        if len(out) < need:
            out += self._silence(need - len(out))

        # meter push from what is actually written
        self._vol_push(out)

        # auto-finish: when final and nothing more to play, complete and stop()
        if self._final and self._buffer_empty():
            QTimer.singleShot(0, self.stop)  # stop on the GUI thread
            return out, pyaudio.paComplete

        return out, pyaudio.paContinue

    def _buffer_empty(self) -> bool:
        """
        Check if internal buffer is empty.

        :return: True if empty
        """
        with self._buf_lock:
            return len(self._buffer) == 0

    def _silence(self, n: int) -> bytes:
        """
        Generate n bytes of silence.

        :param n: number of bytes
        :return: bytes of silence
        """
        if n <= 0:
            return b""
        if self.width == 1:
            return bytes([128]) * n  # silence for unsigned 8-bit
        return b"\x00" * n

    def _vol_push(self, chunk: bytes) -> None:
        """
        Push chunk to volume buffer and trim if needed.

        :param chunk: bytes to push to volume buffer
        """
        if not chunk:
            return
        with self._vol_lock:
            self._vol_buffer.extend(chunk)
            max_bytes = max(1, self.bytes_per_ms * 100)  # ~100 ms window
            if len(self._vol_buffer) > max_bytes:
                del self._vol_buffer[:len(self._vol_buffer) - max_bytes]

    def _emit_volume_tick(self) -> None:
        """Emit volume level based on current volume buffer."""
        if self._volume_emitter is None:
            return
        with self._vol_lock:
            buf = bytes(self._vol_buffer)
        if not buf:
            try:
                self._volume_emitter(0)
            except Exception:
                pass
            return
        try:
            # decode by sample width
            if self.width == 1:
                arr = np.frombuffer(buf, dtype=np.uint8).astype(np.int16)
                arr = (arr - 128).astype(np.float32) / 128.0
            elif self.width == 2:
                arr = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
            elif self.width == 4:
                arr = np.frombuffer(buf, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                arr = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0

            if arr.size == 0:
                self._volume_emitter(0)
                return

            rms = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
            db = -60.0 if rms <= 1e-9 else 20.0 * float(np.log10(min(1.0, rms)))
            db = max(-60.0, min(0.0, db))
            volume = int(((db + 60.0) / 60.0) * 100.0)
            self._volume_emitter(volume)
        except Exception:
            pass