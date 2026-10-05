"""Wake Qt immediately on a system shutdown signal."""

import signal
import socket

from PySide6.QtCore import QObject, QSocketNotifier


class ShutdownSignals(QObject):
    """Bridge OS signals to the normal application shutdown on the GUI thread."""

    def __init__(self, app):
        super().__init__(app)
        self._requested = False
        self._closed = False
        self._handlers = {}
        self._reader, self._writer = socket.socketpair()
        self._reader.setblocking(False)
        self._writer.setblocking(False)
        self._previous_fd = signal.set_wakeup_fd(self._writer.fileno(), warn_on_full_buffer=False)
        for name in ('SIGTERM', 'SIGINT', 'SIGHUP', 'SIGBREAK'):
            signum = getattr(signal, name, None)
            if signum is not None:
                self._handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, self._handle_signal)
        self._notifier = QSocketNotifier(self._reader.fileno(), QSocketNotifier.Read, self)
        self._notifier.activated.connect(self._drain)
        self._app = app
        app.aboutToQuit.connect(self.close)

    @staticmethod
    def _handle_signal(signum, frame):
        # CPython writes the signal number to the wakeup socket. Never run Qt
        # or resource cleanup inside a Python signal handler.
        pass

    def _drain(self, *args):
        received = False
        while True:
            try:
                data = self._reader.recv(4096)
            except BlockingIOError:
                break
            if not data:
                break
            received = received or any(signum in self._handlers for signum in data)
        if received and not self._requested:
            self._requested = True
            # quit() bypasses minimize-to-tray and uses MainWindow.shutdown()
            # through aboutToQuit, including saving state and stopping plugins.
            self._app.quit()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._notifier.setEnabled(False)
        signal.set_wakeup_fd(self._previous_fd)
        for signum, handler in self._handlers.items():
            signal.signal(signum, handler)
        self._reader.close()
        self._writer.close()
