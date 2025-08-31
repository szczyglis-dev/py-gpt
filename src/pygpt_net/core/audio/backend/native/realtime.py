#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QAudioFormat, QAudioSink
from PySide6.QtCore import QTimer, QObject


class RealtimeSession(QObject):
    """Global realtime session: pumps PCM bytes to QAudioSink without blocking the GUI."""
    def __init__(
            self,
            device,
            fmt: QAudioFormat,
            parent=None,
            volume_emitter: callable = None
    ):
        """
        Initialize the session.

        :param device: QAudioDeviceInfo
        :param fmt: QAudioFormat
        :param parent: QObject
        :param volume_emitter: optional callable to emit volume level (0-100)
        """
        super().__init__(parent)
        self._device = device
        self.format = fmt

        # NOTE: very simple sink with modest HW buffer (~300 ms) to avoid underruns
        self.sink = QAudioSink(device, fmt)
        hw_ms = 300
        bs = int(max(fmt.sampleRate() * fmt.channelCount() * fmt.bytesPerSample() * (hw_ms / 1000.0), 8192))
        self.sink.setBufferSize(bs)

        self.io = self.sink.start()
        if self.io is None:
            raise RuntimeError("QAudioSink.start() returned None (no IO for writing)")

        # user buffer and simple timing
        self.buffer = bytearray()
        self.final = False

        # format helpers
        self.frame_bytes = max(1, fmt.channelCount() * fmt.bytesPerSample())
        self.bytes_per_ms = max(1, int(fmt.sampleRate() * fmt.channelCount() * fmt.bytesPerSample() / 1000))

        # NOTE: keep writes reasonably sized
        self.min_write_bytes = max(self.bytes_per_ms * 20, self.frame_bytes)  # ~20 ms
        self.max_write_bytes = max(self.bytes_per_ms * 100, self.frame_bytes) # ~100 ms

        # small tail of silence to avoid end clicks
        self.tail_ms = 60  # ~60 ms

        # very small pump
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setInterval(10)  # ~10 ms
        self.timer.timeout.connect(self._pump)
        self.timer.start()

        # simple volume metering (optional)
        self.volume_emitter = volume_emitter
        self.vol_window_bytes = max(1, self.bytes_per_ms * 100)  # ~100 ms
        self.vol_buffer = bytearray()
        self.vol_timer = QTimer(self)
        self.vol_timer.setTimerType(Qt.PreciseTimer)
        self.vol_timer.setInterval(33)
        self.vol_timer.timeout.connect(self._emit_volume_tick)
        self.vol_timer.start()
        self._sf = fmt.sampleFormat()

        self.on_stopped = None  # callback set by NativeBackend

    def feed(self, data: bytes) -> None:
        """
        Feed PCM bytes (already in device format).

        :param data: bytes
        """
        if not data or self.io is None:
            return
        self.buffer.extend(data)
        # NOTE: try pump quickly (non-blocking)
        self._pump()

    def mark_final(self) -> None:
        """Mark no-more-data and add small silence tail."""
        if not self.final:
            pad = self._align_down(self.bytes_per_ms * self.tail_ms)
            if pad > 0:
                self.buffer.extend(self._silence(pad))
        self.final = True
        self._pump()

    def stop(self) -> None:
        """Stop the session and clean up."""
        try:
            if self.timer:
                self.timer.stop()
        except Exception:
            pass
        try:
            if self.vol_timer:
                self.vol_timer.stop()
        except Exception:
            pass
        try:
            if self.sink:
                self.sink.stop()
        except Exception:
            pass

        # zero volume instantly
        try:
            self.vol_buffer.clear()
            if self.volume_emitter:
                self.volume_emitter(0)
        except Exception:
            pass

        self.io = None
        self.sink = None

        cb = self.on_stopped
        self.on_stopped = None
        if cb:
            try:
                cb()
            except Exception:
                pass

        self.deleteLater()

    def _pump(self) -> None:
        """Write as much as device can take right now."""
        if self.io is None:
            return

        free = int(self.sink.bytesFree()) if self.sink else 0
        if free <= 0 and not self.buffer:
            return

        to_write = min(len(self.buffer), free, self.max_write_bytes)
        to_write = self._align_down(to_write)

        # avoid tiny writes unless finishing
        if not self.final and 0 < to_write < self.min_write_bytes:
            return

        if to_write > 0:
            chunk = bytes(self.buffer[:to_write])
            written = self.io.write(chunk)
            if written and written > 0:
                del self.buffer[:written]
                # simple volume window
                self._vol_push(chunk[:self._align_down(written)])

        # stop when: final AND our buffer empty AND device queue empty
        if self.final and not self.buffer:
            pend = 0
            try:
                pend = int(self.sink.bufferSize()) - int(self.sink.bytesFree())
            except Exception:
                pass
            if pend <= 0:
                self.stop()

    def _align_down(self, n: int) -> int:
        """
        Align to frame boundary.

        :param n: number of bytes
        :return: aligned number of bytes
        """
        if self.frame_bytes <= 1:
            return n
        rem = n % self.frame_bytes
        return n - rem

    def _silence(self, n: int) -> bytes:
        """
        Generate n bytes of silence.
        NOTE: for Int16 silence is all zeros; for UInt8 it is 0x80.

        :param n: number of bytes
        :return: bytes of silence
        """
        if n <= 0:
            return b""
        sf = self.format.sampleFormat()
        if sf == QAudioFormat.SampleFormat.UInt8:
            return bytes([128]) * n
        return b"\x00" * n

    def _vol_push(self, chunk: bytes) -> None:
        """
        Push chunk to volume buffer and trim if needed.

        :param chunk: bytes to push to volume buffer
        """
        if not chunk:
            return
        self.vol_buffer.extend(chunk)
        if len(self.vol_buffer) > self.vol_window_bytes:
            del self.vol_buffer[:len(self.vol_buffer) - self.vol_window_bytes]

    def _emit_volume_tick(self) -> None:
        """Emit volume level (0-100) based on current vol_buffer content."""
        if self.volume_emitter is None:
            return
        try:
            if not self.vol_buffer:
                self.volume_emitter(0)
                return

            sf = self._sf
            if sf == QAudioFormat.SampleFormat.UInt8:
                arr = np.frombuffer(self.vol_buffer, dtype=np.uint8).astype(np.int16)
                arr = (arr - 128).astype(np.float32) / 128.0
            elif sf == QAudioFormat.SampleFormat.Int16:
                arr = np.frombuffer(self.vol_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            elif sf == QAudioFormat.SampleFormat.Int32:
                arr = np.frombuffer(self.vol_buffer, dtype=np.int32).astype(np.float32) / 2147483648.0
            elif sf == QAudioFormat.SampleFormat.Float:
                arr = np.frombuffer(self.vol_buffer, dtype=np.float32).astype(np.float32)
            else:
                arr = np.frombuffer(self.vol_buffer, dtype=np.int16).astype(np.float32) / 32768.0

            if arr.size == 0:
                self.volume_emitter(0)
                return

            rms = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
            db = -60.0 if rms <= 1e-9 else 20.0 * float(np.log10(min(1.0, rms)))
            db = max(-60.0, min(0.0, db))
            volume = int(((db + 60.0) / 60.0) * 100.0)
            self.volume_emitter(volume)
        except Exception:
            pass