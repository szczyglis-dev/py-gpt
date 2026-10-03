#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.30 23:30:00                  #
# ================================================== #

from PySide6.QtCore import (
    Qt,
    QRectF,
    QPropertyAnimation,
    Property,
    QSequentialAnimationGroup,
    QAbstractAnimation,
    QEasingCurve,
    QPauseAnimation,
    QEvent,
    QElapsedTimer,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy

try:
    from pygpt_net.core.types.theme import THEME_TYPE_LIGHT
except Exception:
    THEME_TYPE_LIGHT = "light"


class _BaseLevelBar(QWidget):
    """Simple audio level bar with optional right-to-left fill."""

    def __init__(self, parent=None, reverse: bool = False):
        super().__init__(parent)
        self._level = 0.0
        self._reverse = reverse
        self._bar_color = None
        self._background_color = None
        self.setFixedSize(200, 5)

    def setLevel(self, level):
        """Set volume level (0-100)."""
        level = min(max(float(level), 0.0), 100.0)
        if self._level == level:
            return
        self._level = level
        self.update()

    def setBarColor(self, color):
        self._bar_color = self._coerce_color(color)
        self.update()

    def setBackgroundColor(self, color):
        self._background_color = self._coerce_color(color)
        self.update()

    @staticmethod
    def _coerce_color(color):
        if isinstance(color, QColor):
            return QColor(color)
        value = QColor(color)
        return value if value.isValid() else None

    def _fallback_background(self) -> QColor:
        return self.palette().color(QPalette.Mid)

    def _fallback_fill(self) -> QColor:
        return self.palette().color(QPalette.ButtonText)

    def _bar_background(self) -> QColor:
        color = self._background_color or self._fallback_background()
        if not color.isValid():
            color = QColor("#444444")
        return color

    def _bar_fill(self) -> QColor:
        color = self._bar_color or self._fallback_fill()
        if not color.isValid():
            color = QColor("#ffffff")
        return color

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.transparent)

        bg_rect = QRectF(self.rect())
        radius = min(bg_rect.height() / 2.0, 3.0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bar_background())
        painter.drawRoundedRect(bg_rect, radius, radius)

        if self._level <= 0:
            return

        width = (self._level / 100.0) * bg_rect.width()
        if self._reverse:
            fill_rect = QRectF(bg_rect.right() - width, bg_rect.top(), width, bg_rect.height())
        else:
            fill_rect = QRectF(bg_rect.left(), bg_rect.top(), width, bg_rect.height())
        painter.setBrush(self._bar_fill())
        painter.drawRoundedRect(fill_rect, radius, radius)


class InputBar(_BaseLevelBar):
    def __init__(self, parent=None):
        super().__init__(parent, reverse=False)

    def paintEvent(self, event):
        # Keep legacy centered visualization for the old advanced record button.
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        level_width = (self._level / 100.0) * self.width()
        center_x = self.width() / 2.0
        rect_x = center_x - (level_width / 2.0)
        painter.setBrush(self.palette().color(QPalette.ButtonText))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(rect_x, 0.0, level_width, float(self.height())))


class OutputBar(_BaseLevelBar):
    def __init__(self, parent=None):
        super().__init__(parent, reverse=False)

    def paintEvent(self, event):
        # Preserve existing output bar appearance/behavior.
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        level_width = (self._level / 100.0) * self.width()
        center_x = self.width() / 2.0
        rect_x = center_x - (level_width / 2.0)
        painter.setBrush(self.palette().color(QPalette.ButtonText))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(rect_x, 0.0, level_width, float(self.height())))


class InputRecordLevelBar(_BaseLevelBar):
    """Input level bar with a continuous right-to-left activity sweep."""

    def __init__(self, parent=None):
        super().__init__(parent, reverse=True)
        self._activity_phase = 0.0
        self.setFixedSize(120, 6)

        self._activity_anim = QPropertyAnimation(self, b"activityPhase", self)
        self._activity_anim.setDuration(1150)
        self._activity_anim.setStartValue(0.0)
        self._activity_anim.setEndValue(1.0)
        self._activity_anim.setLoopCount(-1)
        self._activity_anim.setEasingCurve(QEasingCurve.Linear)

    def _get_activity_phase(self) -> float:
        return self._activity_phase

    def _set_activity_phase(self, value: float):
        self._activity_phase = min(max(float(value), 0.0), 1.0)
        self.update()

    activityPhase = Property(float, _get_activity_phase, _set_activity_phase)

    def start_activity(self):
        if self._activity_anim.state() != QAbstractAnimation.Running:
            self._activity_anim.start()

    def stop_activity(self):
        self._activity_anim.stop()
        self._set_activity_phase(0.0)

    def _activity_color(self) -> QColor:
        background = self._bar_background()
        if background.lightness() > 150:
            color = background.darker(112)
        else:
            color = background.lighter(132)
        color.setAlpha(190)
        return color

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.transparent)

        bg_rect = QRectF(self.rect())
        radius = min(bg_rect.height() / 2.0, 3.0)
        path = QPainterPath()
        path.addRoundedRect(bg_rect, radius, radius)

        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bar_background())
        painter.drawPath(path)

        # Indeterminate activity segment. It deliberately travels in the
        # opposite direction to the splash progress indicator: right -> left.
        chunk_width = max(24.0, bg_rect.width() * 0.30)
        travel = bg_rect.width() + chunk_width
        chunk_x = bg_rect.right() - (self._activity_phase * travel)
        chunk_rect = QRectF(chunk_x, bg_rect.top(), chunk_width, bg_rect.height())
        painter.save()
        painter.setClipPath(path)
        painter.setBrush(self._activity_color())
        painter.drawRect(chunk_rect)
        painter.restore()

        # Keep the real microphone level independent from the background
        # animation. The current UI fills the level from right to left.
        if self._level <= 0:
            return
        width = (self._level / 100.0) * bg_rect.width()
        fill_rect = QRectF(bg_rect.right() - width, bg_rect.top(), width, bg_rect.height())
        painter.save()
        painter.setClipPath(path)
        painter.setBrush(self._bar_fill())
        painter.drawRect(fill_rect)
        painter.restore()


class RecordingDot(QWidget):
    """Animated recording indicator with a subtle pulse."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._record_color = None
        self._state_scale = 1.0
        self._pulse_scale = 1.0
        self._active = False
        self._pending = False
        self._base_diameter = 10.0
        self.setFixedSize(18, 18)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._pulse_anim = QSequentialAnimationGroup(self)
        grow = QPropertyAnimation(self, b"pulseScale", self)
        grow.setDuration(350)
        grow.setStartValue(1.0)
        grow.setEndValue(1.08)
        grow.setEasingCurve(QEasingCurve.InOutSine)
        shrink = QPropertyAnimation(self, b"pulseScale", self)
        shrink.setDuration(450)
        shrink.setStartValue(1.08)
        shrink.setEndValue(1.0)
        shrink.setEasingCurve(QEasingCurve.InOutSine)
        pause = QPauseAnimation(650, self)
        self._pulse_anim.addAnimation(grow)
        self._pulse_anim.addAnimation(shrink)
        self._pulse_anim.addAnimation(pause)
        self._pulse_anim.setLoopCount(-1)

        self._state_anim = QPropertyAnimation(self, b"stateScale", self)
        self._state_anim.setDuration(180)
        self._state_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _coerce_color(self, color):
        if isinstance(color, QColor):
            return QColor(color)
        value = QColor(color)
        return value if value.isValid() else None

    def setRecordColor(self, color):
        self._record_color = self._coerce_color(color)
        self.update()

    def recordColor(self) -> QColor:
        return self._record_color or QColor("#ff3b30")

    def _get_state_scale(self) -> float:
        return self._state_scale

    def _set_state_scale(self, value: float):
        self._state_scale = max(0.1, float(value))
        self.update()

    def _get_pulse_scale(self) -> float:
        return self._pulse_scale

    def _set_pulse_scale(self, value: float):
        self._pulse_scale = max(0.1, float(value))
        self.update()

    stateScale = Property(float, _get_state_scale, _set_state_scale)
    pulseScale = Property(float, _get_pulse_scale, _set_pulse_scale)

    def set_pending(self):
        self._pending = True
        self._active = False
        self._state_anim.stop()
        self._pulse_anim.stop()
        self._set_pulse_scale(1.0)
        self._set_state_scale(0.62)
        self.update()

    def set_active(self):
        self._pending = False
        self._active = True
        self._state_anim.stop()
        self._state_anim.setStartValue(self._state_scale)
        self._state_anim.setEndValue(1.0)
        self._state_anim.start()
        if self._pulse_anim.state() != QAbstractAnimation.Running:
            self._pulse_anim.start()
        self.update()

    def reset(self):
        self._active = False
        self._pending = False
        self._state_anim.stop()
        self._pulse_anim.stop()
        self._set_pulse_scale(1.0)
        self._set_state_scale(1.0)
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.transparent)

        color = self.recordColor()
        radius = (self._base_diameter * self._state_scale * self._pulse_scale) / 2.0
        rect = QRectF(
            (self.width() / 2.0) - radius,
            (self.height() / 2.0) - radius,
            radius * 2.0,
            radius * 2.0,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(rect)


class InputRecordWidget(QWidget):
    """Dedicated top-row input recording meter for the shared composer."""

    def __init__(self, window=None, parent=None):
        if parent is None:
            parent = window
        super().__init__(parent)
        self.window = window
        self._bar_background_color = None
        self._bar_color = None
        self._record_color = None
        self._state = "idle"
        self._microphone_enabled = True

        self.setObjectName("audioInputRecordWidget")
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)

        self.elapsed = QLabel("00:00", self)
        self.elapsed.setStyleSheet("background: transparent; border: none;")
        self.elapsed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.elapsed.setFixedWidth(62)
        self.elapsed.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._elapsed_clock = QElapsedTimer()
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(250)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        self.bar = InputRecordLevelBar(self)
        self.dot = RecordingDot(self)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 0, 4, 0)
        self.layout.setSpacing(6)
        self.layout.addWidget(self.elapsed, alignment=Qt.AlignVCenter)
        self.layout.addWidget(self.bar, alignment=Qt.AlignVCenter)
        self.layout.addWidget(self.dot, alignment=Qt.AlignVCenter)
        self.layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._apply_colors()
        self.hide_widget()

    def _theme_type(self) -> str:
        try:
            theme = self.window.core.config.get("theme")
            return self.window.controller.theme.common.get_theme_type(theme)
        except Exception:
            palette_color = self.palette().color(QPalette.Window)
            return THEME_TYPE_LIGHT if palette_color.lightness() > 140 else "dark"

    def _default_bar_background(self) -> QColor:
        if self._theme_type() == THEME_TYPE_LIGHT:
            return QColor("#d6dbe0")
        return QColor("#31353a")

    def _default_bar_color(self) -> QColor:
        if self._theme_type() == THEME_TYPE_LIGHT:
            return QColor("#26292d")
        return QColor("#ffffff")

    def _default_record_color(self) -> QColor:
        if self._theme_type() == THEME_TYPE_LIGHT:
            return QColor("#d84a3d")
        return QColor("#ff3b30")

    def _coerce_color(self, color):
        if isinstance(color, QColor):
            return QColor(color)
        value = QColor(color)
        return value if value.isValid() else None

    def _apply_colors(self):
        bg = self.barBackgroundColor
        bar = self.barColor
        rec = self.recordColor
        self.bar.setBackgroundColor(bg)
        self.bar.setBarColor(bar)
        self.dot.setRecordColor(rec)

    def _get_bar_background_color(self):
        return self._bar_background_color or self._default_bar_background()

    def _set_bar_background_color(self, color):
        value = self._coerce_color(color)
        if value is None:
            return
        self._bar_background_color = value
        self._apply_colors()

    def _get_bar_color(self):
        return self._bar_color or self._default_bar_color()

    def _set_bar_color(self, color):
        value = self._coerce_color(color)
        if value is None:
            return
        self._bar_color = value
        self._apply_colors()

    def _get_record_color(self):
        return self._record_color or self._default_record_color()

    def _set_record_color(self, color):
        value = self._coerce_color(color)
        if value is None:
            return
        self._record_color = value
        self._apply_colors()

    barBackgroundColor = Property(QColor, _get_bar_background_color, _set_bar_background_color)
    barColor = Property(QColor, _get_bar_color, _set_bar_color)
    recordColor = Property(QColor, _get_record_color, _set_record_color)

    def is_pending(self) -> bool:
        return self._state == "pending"

    def is_recording(self) -> bool:
        return self._state == "recording"

    def set_microphone_enabled(self, enabled: bool):
        """Compatibility hook retained after replacing the mic icon with time."""
        self._microphone_enabled = bool(enabled)

    def is_microphone_enabled(self) -> bool:
        """Return the legacy microphone-visibility preference."""
        return self._microphone_enabled

    @staticmethod
    def _format_elapsed(seconds: int) -> str:
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes:02d}:{seconds:02d}"

        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _reset_elapsed(self):
        self._elapsed_timer.stop()
        self._elapsed_clock.invalidate()
        self.elapsed.setText("00:00")

    def _start_elapsed(self):
        self._elapsed_clock.start()
        self.elapsed.setText("00:00")
        self._elapsed_timer.start()

    def _update_elapsed(self):
        if self._state != "recording" or not self._elapsed_clock.isValid():
            return
        self.elapsed.setText(self._format_elapsed(self._elapsed_clock.elapsed() // 1000))

    def show_pending(self):
        self._state = "pending"
        self._reset_elapsed()
        self.bar.stop_activity()
        self.bar.setLevel(0)
        self.elapsed.setVisible(False)
        self.bar.setVisible(False)
        self.dot.setVisible(True)
        self.dot.set_pending()
        self.show()

    def show_recording(self):
        already_recording = self._state == "recording"
        self._state = "recording"
        if not already_recording:
            self._start_elapsed()
        self.elapsed.setVisible(True)
        self.bar.setVisible(True)
        self.dot.setVisible(True)
        self.bar.start_activity()
        self.dot.set_active()
        self.show()

    def hide_widget(self):
        self._state = "idle"
        self._reset_elapsed()
        self.bar.stop_activity()
        self.bar.setLevel(0)
        self.dot.reset()
        self.hide()

    def abort(self):
        self.hide_widget()

    def reset(self):
        self.hide_widget()

    def setLevel(self, level):
        self.bar.setLevel(level)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange):
            self._apply_colors()
