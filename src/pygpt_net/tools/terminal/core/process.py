#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Platform PTY transport, independent of widgets and terminal rendering."""
import os
import codecs
import select
import shutil
import signal
import sys
import threading
from PySide6.QtCore import QObject, Signal


class TerminalProcess(QObject):
    output = Signal(str)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.reader = None
        self.closed = False

    def start(self, cwd, rows=24, columns=80, command=None):
        env = dict(os.environ, TERM='xterm', COLORTERM='truecolor')
        if sys.platform == 'win32':
            from winpty import PtyProcess
            command = command or [shutil.which('pwsh') or os.environ.get('COMSPEC', 'cmd.exe')]
        else:
            from ptyprocess import PtyProcessUnicode as PtyProcess
            command = command or [os.environ.get('SHELL') or '/bin/sh', '-i']
        self.process = PtyProcess.spawn(command, cwd=cwd, env=env, dimensions=(rows, columns))
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()

    def read(self):
        decoder = codecs.getincrementaldecoder('utf-8')('replace')
        try:
            while not self.closed:
                if sys.platform == 'win32':
                    text = self.process.read(65536)
                else:
                    if not select.select([self.process.fd], [], [], 0.1)[0]:
                        continue
                    raw = os.read(self.process.fd, 65536)
                    if not raw:
                        break
                    text = decoder.decode(raw)
                    if not text:
                        continue
                if not text:
                    break
                if not self.closed:
                    self.output.emit(text)
        except (EOFError, OSError):
            pass
        finally:
            if not self.closed:
                self.finished.emit()

    def write(self, text):
        if self.process is not None and not self.closed and self.process.isalive():
            self.process.write(text)

    def resize(self, rows, columns):
        if self.process is not None and not self.closed and self.process.isalive():
            self.process.setwinsize(rows, columns)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process is not None:
            # Stop the child first: closing a buffered PTY while another
            # thread is blocked in read() deadlocks on its file lock.
            if sys.platform != 'win32':
                # Foreground jobs can own a different process group than the shell.
                try:
                    foreground = os.tcgetpgrp(self.process.fd)
                    if foreground != os.getpgrp():
                        os.killpg(foreground, signal.SIGHUP)
                except (OSError, ProcessLookupError):
                    pass
            self.process.terminate(force=True)
        if self.reader is not None:
            self.reader.join(timeout=1)
        if self.process is not None:
            self.process.close(force=True)
