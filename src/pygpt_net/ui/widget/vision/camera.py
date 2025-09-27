#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 18:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup, QAbstractAnimation
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QGraphicsOpacityEffect

from pygpt_net.utils import trans


class VideoContainer(QWidget):
    def __init__(self, window=None):
        """
        Video container with scroll

        :param window: Window instance
        """
        super(VideoContainer, self).__init__()
        self.window = window
        self.setStyleSheet("background-color: #000000;")
        self.layout = QVBoxLayout()
        self.video = VideoLabel(window=self.window)
        self.video.setStyleSheet("background-color: #000000; border: 1px solid #000")
        self.layout.addWidget(self.video)
        self.setLayout(self.layout)


class VideoLabel(QLabel):
    def __init__(self, text=None, window=None):
        """
        Video output label

        :param text: text
        :param window: main window
        """
        super(VideoLabel, self).__init__(text)
        self.window = window

        # Tooltip shown on hover
        self.setToolTip(trans("vision.capture.label"))

        # Freeze-frame overlay (post-capture pause)
        self._freeze_duration_ms = 1000  # default: 1 second
        self._freeze = QLabel(self)
        self._freeze.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._freeze.setStyleSheet("background-color: transparent;")
        self._freeze.setScaledContents(True)
        self._freeze.hide()

        self._freeze_effect = QGraphicsOpacityEffect(self._freeze)
        self._freeze.setGraphicsEffect(self._freeze_effect)
        self._freeze_effect.setOpacity(1.0)

        self._freeze_timer = QTimer(self)
        self._freeze_timer.setSingleShot(True)
        self._freeze_timer.timeout.connect(self._on_freeze_timeout)

        self._freeze_fade_out = QPropertyAnimation(self._freeze_effect, b"opacity", self)
        self._freeze_fade_out.setDuration(140)
        self._freeze_fade_out.setStartValue(1.0)
        self._freeze_fade_out.setEndValue(0.0)
        self._freeze_fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._freeze_fade_out.finished.connect(self._on_freeze_finished)

        # Flash overlay for click feedback (screenshot effect)
        self._flash = QWidget(self)
        self._flash.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._flash.setStyleSheet("background-color: #ffffff;")
        self._flash.hide()

        # Opacity effect + animation group for smooth flash in/out
        self._flash_effect = QGraphicsOpacityEffect(self._flash)
        self._flash.setGraphicsEffect(self._flash_effect)
        self._flash_effect.setOpacity(0.0)

        self._anim_in = QPropertyAnimation(self._flash_effect, b"opacity", self)
        self._anim_in.setDuration(90)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(0.85)
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_out = QPropertyAnimation(self._flash_effect, b"opacity", self)
        self._anim_out.setDuration(160)
        self._anim_out.setStartValue(0.85)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)

        self._flash_anim = QSequentialAnimationGroup(self)
        self._flash_anim.addAnimation(self._anim_in)
        self._flash_anim.addAnimation(self._anim_out)
        self._flash_anim.finished.connect(self._on_flash_finished)

    # -------- Freeze-frame helpers --------
    def _start_freeze(self, duration_ms=None):
        """Show a 1:1 snapshot overlay for a short 'freeze-frame' effect."""
        duration = self._freeze_duration_ms if duration_ms is None else duration_ms

        # Snapshot the currently displayed content before showing overlays
        shot = self.grab()

        # Prepare overlay
        self._freeze_timer.stop()
        if self._freeze_fade_out.state() != QAbstractAnimation.Stopped:
            self._freeze_fade_out.stop()
        self._freeze_effect.setOpacity(1.0)

        self._freeze.setGeometry(self.rect())
        self._freeze.setPixmap(shot)
        self._freeze.raise_()
        self._freeze.show()

        # Schedule fade-out/hide
        self._freeze_timer.start(duration)

    def _on_freeze_timeout(self):
        """Start fade-out of the freeze overlay."""
        if self._freeze.isVisible():
            self._freeze_fade_out.start()

    def _on_freeze_finished(self):
        """Cleanup after the freeze overlay is faded out."""
        self._freeze.hide()
        # Clear pixmap instead of passing None which is invalid for setPixmap
        self._freeze.clear()
        self._freeze_effect.setOpacity(1.0)

    # -------- Flash helpers --------
    def _start_flash(self):
        """Start the visual flash effect to indicate a capture."""
        self._flash.setGeometry(self.rect())
        self._flash.raise_()
        self._flash.show()
        self._flash_effect.setOpacity(0.0)
        # Restart animation if it is running
        if self._flash_anim.state() != QAbstractAnimation.Stopped:
            self._flash_anim.stop()
        self._flash_anim.start()

    def _on_flash_finished(self):
        """Hide overlay when the animation is done."""
        self._flash.hide()

    def resizeEvent(self, event):
        """Keep overlays in sync with the label size."""
        self._freeze.setGeometry(self.rect())
        self._flash.setGeometry(self.rect())
        super(VideoLabel, self).resizeEvent(event)

    def enterEvent(self, event):
        """Show link-like cursor on hover."""
        self.setCursor(Qt.PointingHandCursor)
        super(VideoLabel, self).enterEvent(event)

    def leaveEvent(self, event):
        """Restore cursor when leaving the widget."""
        self.unsetCursor()
        super(VideoLabel, self).leaveEvent(event)

    def mousePressEvent(self, event):
        """
        Mouse click

        :param event: mouse event
        """
        if event.button() == Qt.LeftButton:
            # Freeze current frame for a brief moment
            self._start_freeze()

            # Trigger immediate visual feedback
            self._start_flash()

            # Defer capture to the next event loop tick to keep UI responsive
            if self.window is not None and hasattr(self.window, "controller"):
                QTimer.singleShot(0, lambda: self.window.controller.camera.manual_capture())

        super(VideoLabel, self).mousePressEvent(event)