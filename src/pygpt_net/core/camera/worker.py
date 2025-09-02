#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 16:00:00                  #
# ================================================== #

import time

from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QEventLoop, QTimer, Qt
from PySide6.QtGui import QImage

class CaptureSignals(QObject):
    finished = Signal()
    unfinished = Signal()
    destroyed = Signal()
    started = Signal()
    stopped = Signal()
    capture = Signal(object)
    error = Signal(object)


class CaptureWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = CaptureSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None

        # Common
        self.initialized = False
        self.allow_finish = False
        self._fps_interval = 1.0 / 30.0  # default 30 FPS throttle

        # Qt Multimedia objects (created in worker thread)
        self.session = None
        self.camera = None
        self.sink = None
        self.loop = None
        self.poll_timer = None
        self._qt_got_first_frame = False
        self._probe_loop = None

        # OpenCV fallback
        self.cv_cap = None

        # Timing (shared)
        self._last_emit = 0.0

    # =========================
    # Qt Multimedia path
    # =========================
    def _select_camera_format(self, device, target_w: int, target_h: int):
        """
        Select best matching camera format by resolution.

        :param device: QCameraDevice
        :param target_w: target width
        :param target_h: target height
        """
        try:
            formats = list(device.videoFormats())
        except Exception:
            formats = []
        if not formats:
            return None

        best = None
        best_score = float('inf')
        for f in formats:
            res = f.resolution()
            w, h = res.width(), res.height()
            score = abs(w - target_w) + abs(h - target_h)
            if score < best_score:
                best_score = score
                best = f
        return best

    def _init_qt(self) -> bool:
        """
        Try to initialize Qt camera pipeline.

        :return: True if initialized
        """
        try:
            from PySide6.QtMultimedia import (
                QCamera,
                QMediaDevices,
                QMediaCaptureSession,
                QVideoSink,
            )

            idx = int(self.window.core.config.get('vision.capture.idx') or 0)
            target_w = int(self.window.core.config.get('vision.capture.width'))
            target_h = int(self.window.core.config.get('vision.capture.height'))
            target_fps = 30
            self._fps_interval = 1.0 / float(target_fps)

            devices = list(QMediaDevices.videoInputs())
            if not devices:
                return False

            if idx < 0 or idx >= len(devices):
                idx = 0
            dev = devices[idx]

            self.camera = QCamera(dev)
            fmt = self._select_camera_format(dev, target_w, target_h)
            if fmt is not None:
                self.camera.setCameraFormat(fmt)

            self.session = QMediaCaptureSession()
            self.session.setCamera(self.camera)

            self.sink = QVideoSink()
            self.sink.videoFrameChanged.connect(self.on_qt_frame_changed, Qt.DirectConnection)
            self.session.setVideoOutput(self.sink)

            self.camera.errorOccurred.connect(self._on_qt_camera_error, Qt.QueuedConnection)
            return True

        except Exception as e:
            # Qt Multimedia not available or failed to init
            self.window.core.debug.log(e)
            return False

    def _teardown_qt(self):
        """Release Qt camera pipeline."""
        try:
            if self.sink is not None:
                try:
                    self.sink.videoFrameChanged.disconnect(self.on_qt_frame_changed)
                except Exception:
                    pass
            if self.camera is not None and self.camera.isActive():
                self.camera.stop()
        except Exception:
            pass
        finally:
            self.sink = None
            self.session = None
            self.camera = None

    def _probe_qt_start(self, timeout_ms: int = 1500) -> bool:
        """
        Wait briefly for the first frame to confirm Qt pipeline is working.

        :param timeout_ms: timeout in milliseconds
        :return: True if first frame received
        """
        try:
            if self.camera is None:
                return False

            self._qt_got_first_frame = False
            self._probe_loop = QEventLoop()

            # Timeout quits the probe loop
            QTimer.singleShot(timeout_ms, self._probe_loop.quit)

            # Start camera and wait for first frame or timeout
            self.camera.start()
            self._probe_loop.exec()

            got = self._qt_got_first_frame
            self._probe_loop = None
            return got
        except Exception as e:
            self.window.core.debug.log(e)
            return False

    @Slot(object)
    def _on_qt_camera_error(self, err):
        """
        Handle Qt camera errors.

        :param err: error object
        """
        try:
            # Stop loop if running
            if self.loop is not None and self.loop.isRunning():
                self.loop.quit()
            if self._probe_loop is not None and self._probe_loop.isRunning():
                self._probe_loop.quit()
        except Exception:
            pass
        finally:
            self.allow_finish = False
            if self.signals is not None:
                self.signals.error.emit(err)

    @Slot(object)
    def on_qt_frame_changed(self, video_frame):
        """
        Convert QVideoFrame to RGB numpy array and emit.

        :param video_frame: QVideoFrame
        """
        try:
            # Mark that we have a first frame for probe
            if not self._qt_got_first_frame:
                self._qt_got_first_frame = True
                # If we are probing, quit the probe loop immediately
                if self._probe_loop is not None and self._probe_loop.isRunning():
                    self._probe_loop.quit()

            # Throttle FPS for normal operation path
            now = time.monotonic()
            if self.loop is not None and self.loop.isRunning():
                if (now - self._last_emit) < self._fps_interval:
                    return

            img = video_frame.toImage()
            if img.isNull():
                return

            img = img.convertToFormat(QImage.Format.Format_RGB888)

            w = img.width()
            h = img.height()
            bpl = img.bytesPerLine()

            ptr = img.bits()
            size = bpl * h
            try:
                ptr.setsize(size)
            except Exception:
                # Some bindings may not require setsize; ignore if unsupported
                pass

            import numpy as np
            arr = np.frombuffer(ptr, dtype=np.uint8)

            if bpl != w * 3:
                arr = arr.reshape(h, bpl)[:, : w * 3]
                arr = arr.reshape(h, w, 3).copy()
            else:
                arr = arr.reshape(h, w, 3).copy()

            if self.signals is not None:
                self.signals.capture.emit(arr)
            self._last_emit = now

        except Exception as e:
            self.window.core.debug.log(e)

    # =========================
    # OpenCV fallback path
    # =========================
    def _init_cv2(self) -> bool:
        """
        Try to initialize OpenCV VideoCapture fallback.

        :return: True if initialized
        """
        try:
            import cv2
            idx = int(self.window.core.config.get('vision.capture.idx'))
            target_w = int(self.window.core.config.get('vision.capture.width'))
            target_h = int(self.window.core.config.get('vision.capture.height'))
            target_fps = 30
            self._fps_interval = 1.0 / float(target_fps)

            cap = cv2.VideoCapture(idx)
            if not cap or not cap.isOpened():
                return False

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_h)
            self.cv_cap = cap
            return True
        except Exception as e:
            self.window.core.debug.log(e)
            return False

    def _teardown_cv2(self):
        """Release OpenCV capture."""
        try:
            if self.cv_cap is not None and self.cv_cap.isOpened():
                self.cv_cap.release()
        except Exception:
            pass
        finally:
            self.cv_cap = None

    # =========================
    # Runner
    # =========================
    @Slot()
    def run(self):
        """Run capture using Qt first; fall back to OpenCV if needed."""
        self.allow_finish = True
        self._last_emit = 0.0

        used_backend = None
        try:
            # Try Qt Multimedia
            if self._init_qt():
                if self._probe_qt_start(timeout_ms=1500):
                    # Qt confirmed working; start main event-driven loop
                    used_backend = 'qt'
                    self.initialized = True
                    if self.signals is not None:
                        self.signals.started.emit()

                    self.loop = QEventLoop()

                    self.poll_timer = QTimer()
                    self.poll_timer.setTimerType(Qt.PreciseTimer)
                    self.poll_timer.setInterval(30)
                    self.poll_timer.timeout.connect(self._poll_stop_qt, Qt.DirectConnection)
                    self.poll_timer.start()

                    self.loop.exec()

                    if self.signals is not None:
                        self.signals.stopped.emit()
                else:
                    # Fallback to OpenCV if no frames arrive quickly
                    print("QT camera init failed, trying CV2 fallback...")
                    self._teardown_qt()
            else:
                # Qt init failed outright, fallback to CV2
                print("QT camera init failed, trying CV2 fallback...")

            # Try OpenCV fallback if Qt was not used
            if used_backend is None:
                if self._init_cv2():
                    used_backend = 'cv2'
                    self.initialized = True
                    if self.signals is not None:
                        self.signals.started.emit()

                    import cv2
                    target_fps = 30
                    fps_interval = 1.0 / float(target_fps)
                    last_frame_time = time.time()

                    while True:
                        if self._should_stop():
                            break

                        ok, frame = self.cv_cap.read()
                        if not ok or frame is None:
                            continue

                        now = time.time()
                        if now - last_frame_time >= fps_interval:
                            # Convert BGR -> RGB for the controller/UI pipeline
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            if self.signals is not None:
                                self.signals.capture.emit(frame)
                            last_frame_time = now

                    if self.signals is not None:
                        self.signals.stopped.emit()
                else:
                    # Both providers failed
                    self.allow_finish = False

        except Exception as e:
            self.window.core.debug.log(e)
            if self.signals is not None:
                self.signals.error.emit(e)
        finally:
            # Cleanup resources
            try:
                if self.poll_timer is not None:
                    self.poll_timer.stop()
            except Exception:
                pass
            self.poll_timer = None

            if used_backend == 'qt':
                self._teardown_qt()
            else:
                self._teardown_qt()  # no-op if not initialized
                self._teardown_cv2()

            # Emit final state
            if self.signals is not None:
                if self.allow_finish:
                    self.signals.finished.emit()
                else:
                    self.signals.unfinished.emit()

            self.cleanup()

    def _poll_stop_qt(self):
        """Check stop flags while running Qt pipeline."""
        try:
            if self._should_stop():
                if self.camera is not None and self.camera.isActive():
                    self.camera.stop()
                if self.loop is not None and self.loop.isRunning():
                    self.loop.quit()
        except Exception as e:
            self.window.core.debug.log(e)
            if self.loop is not None and self.loop.isRunning():
                self.loop.quit()

    def _should_stop(self) -> bool:
        """
        Check external stop flags.

        :return: True if should stop
        """
        try:
            if getattr(self.window, 'is_closing', False):
                return True
            if self.window is not None and self.window.controller.camera.stop:
                return True
        except Exception:
            return True
        return False

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        try:
            if sig is not None:
                sig.deleteLater()
        except RuntimeError:
            pass