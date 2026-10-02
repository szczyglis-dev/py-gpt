"""Application-wide computer-control indicator, independent of chat rendering."""
from PySide6.QtCore import QEvent, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QLabel

from pygpt_net.utils import trans
from .computer_use_frame import ComputerUseFrame


class ComputerUseBadge(QLabel):
    active_changed = Signal(bool)
    stop_requested = Signal()

    def __init__(self, window):
        super().__init__(window.menuBar())
        self.window = window
        self.setObjectName('computerUseBadge')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.desktop_frame = ComputerUseFrame(self)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(800)
        self._hide_timer.timeout.connect(self._retire)
        self.active_changed.connect(self.set_active)
        self.stop_requested.connect(self.stop)
        self.hide()
        window.menuBar().installEventFilter(self)

    @Slot(bool)
    def set_active(self, active):
        # Every dispatch path (native providers, plugins and agent workers) shares
        # this guard. Queued activation after ESC must never resurrect the frame.
        if self.window.core.config.get('computer_use.sandbox', False) or (
                active and self.window.controller.kernel.stopped()):
            self.stop()
            return
        if not active:
            # Renderer cleanup/idle events also occur between tool continuations.
            # A following computer action cancels this pending retirement.
            if not self._hide_timer.isActive():
                self._hide_timer.start()
            return
        self._hide_timer.stop()
        if active:
            self.setText(trans('tool.status.computer_use'))
            light = self.window.controller.theme.common.is_light_theme_id(
                self.window.core.config.get('theme', 'dark'))
            color = '#248544' if light else '#55ff70'
            background = 'rgba(36,133,68,24)' if light else 'rgba(85,255,112,24)'
            self.setStyleSheet(
                f'QLabel#computerUseBadge {{ color: {color}; background: {background}; '
                'font-weight: bold; border-radius: 6px; padding: 3px 8px; margin: 0px; }')
            self.adjustSize()
            self.reposition()
        self.setVisible(bool(active))
        self.desktop_frame.show()

    @Slot()
    def stop(self):
        self._hide_timer.stop()
        self._retire()

    def _retire(self):
        self.hide()
        self.desktop_frame.hide()

    def reposition(self):
        bar = self.window.menuBar()
        chrome = getattr(self.window, 'window_chrome', None)
        profile = getattr(chrome, 'profile_label', None)
        if profile is not None:
            x = profile.geometry().right() + 10
        else:
            x = max((bar.actionGeometry(a).right() for a in bar.actions() if a.isVisible()), default=0) + 10
        self.move(x, max(0, (bar.height() - self.height()) // 2))
        self.raise_()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.LayoutRequest, QEvent.ActionChanged):
            QTimer.singleShot(0, self.reposition)
        return False
