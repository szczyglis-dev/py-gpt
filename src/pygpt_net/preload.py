#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 14:00:00                  #
# ================================================== #

# -------------------------------------------------- #
# Lightweight splash window (separate process)
# -------------------------------------------------- #
def _splash_main(conn, title="PyGPT", message="Loading…"):
    """
    Minimal splash process using PySide6. Runs its own event loop and
    listens for commands on a Pipe: {"type": "msg", "text": "..."} or {"type": "quit"}.
    """
    try:
        # Import locally to keep the main process import path untouched
        from PySide6 import QtCore, QtWidgets
    except Exception:
        return

    try:
        # Enable HiDPI (safe defaults)
        try:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass

        app = QtWidgets.QApplication(["pygpt_splash"])

        # Root window styled as splash
        root = QtWidgets.QWidget(
            None,
            QtCore.Qt.SplashScreen
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        root.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        root.setObjectName("SplashRoot")

        panel = QtWidgets.QFrame(root)
        panel.setObjectName("SplashPanel")
        panel.setStyleSheet("""
        #SplashPanel {
            background-color: rgba(30, 30, 30, 230);
            border-radius: 12px;
        }
        QLabel { color: #ffffff; }
        """)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        lbl_title = QtWidgets.QLabel(title, panel)
        lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 600;")

        lbl_msg = QtWidgets.QLabel(message, panel)
        lbl_msg.setAlignment(QtCore.Qt.AlignCenter)
        lbl_msg.setStyleSheet("font-size: 12px;")

        bar = QtWidgets.QProgressBar(panel)
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet("QProgressBar { border: 0px; border-radius: 4px; } "
                          "QProgressBar::chunk { background-color: #3f3f3f; }")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_msg)
        layout.addWidget(bar)

        panel.setFixedSize(360, 120)
        panel.move(0, 0)
        root.resize(panel.size())

        # Center on primary screen
        screen = app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            root.move(geo.center() - root.rect().center())

        # Ensure initial transparency for fade-in
        try:
            root.setWindowOpacity(0.0)
        except Exception:
            pass

        root.show()

        # Fade-in on start (non-blocking, resilient to platform limitations)
        try:
            def _start_fade_in():
                try:
                    anim = QtCore.QPropertyAnimation(root, b"windowOpacity")
                    anim.setDuration(300)
                    anim.setStartValue(0.0)
                    anim.setEndValue(1.0)
                    root._fade_in_anim = anim  # keep reference to avoid GC
                    anim.start()
                except Exception:
                    try:
                        root.setWindowOpacity(1.0)
                    except Exception:
                        pass

            QtCore.QTimer.singleShot(0, _start_fade_in)
        except Exception:
            try:
                root.setWindowOpacity(1.0)
            except Exception:
                pass

        # Poll the pipe for messages and close requests
        timer = QtCore.QTimer()
        timer.setInterval(80)

        def poll():
            try:
                if conn.poll():
                    msg = conn.recv()
                    if isinstance(msg, dict):
                        t = msg.get("type")
                        if t == "quit":
                            # Stop fade-in if it is running to avoid conflicting animations
                            try:
                                if hasattr(root, "_fade_in_anim") and root._fade_in_anim is not None:
                                    root._fade_in_anim.stop()
                            except Exception:
                                pass
                            # Fade-out and quit
                            try:
                                anim = QtCore.QPropertyAnimation(root, b"windowOpacity")
                                anim.setDuration(180)
                                anim.setStartValue(root.windowOpacity())
                                anim.setEndValue(0.0)
                                anim.finished.connect(app.quit)
                                # Keep reference to avoid GC
                                root._fade_anim = anim
                                anim.start()
                            except Exception:
                                app.quit()
                        elif t == "msg":
                            text = msg.get("text", "")
                            if text:
                                lbl_msg.setText(text)
                    elif isinstance(msg, str):
                        if msg.lower() == "quit":
                            app.quit()
            except (EOFError, OSError):
                # Parent died or pipe closed: exit
                app.quit()

        timer.timeout.connect(poll)
        timer.start()

        # Failsafe timeout (can be overridden via env)
        import os as _os
        timeout_ms = int(_os.environ.get("PYGPT_SPLASH_TIMEOUT", "120000"))
        killer = QtCore.QTimer()
        killer.setSingleShot(True)
        killer.timeout.connect(app.quit)
        killer.start(timeout_ms)

        app.exec()
    except Exception:
        # No crash propagation to main app
        pass


class _Preloader:
    """
    Controller for the splash subprocess.
    """

    def __init__(self, proc, conn):
        self._proc = proc
        self._conn = conn

    def set_message(self, text):
        try:
            if self._conn:
                self._conn.send({"type": "msg", "text": str(text)})
        except Exception:
            pass

    def close(self, wait=True, timeout=2.0):
        try:
            if self._conn:
                try:
                    self._conn.send({"type": "quit"})
                except Exception:
                    pass
        finally:
            if wait and self._proc is not None:
                self._proc.join(timeout=timeout)
            if self._proc is not None and self._proc.is_alive():
                try:
                    self._proc.terminate()
                except Exception:
                    pass
            self._conn = None
            self._proc = None


def _start_preloader(title="PyGPT", message="Loading…"):
    """
    Start splash in a separate process to avoid interfering with the main Qt app.
    Returns a _Preloader controller or None if failed.
    """
    try:
        from multiprocessing import Process, Pipe
        parent_conn, child_conn = Pipe(duplex=True)
        proc = Process(target=_splash_main, args=(child_conn, title, message), daemon=True)
        proc.start()
        return _Preloader(proc, parent_conn)
    except Exception:
        return None