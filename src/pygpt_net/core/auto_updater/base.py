#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import os
import subprocess
import threading
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class UpdateError(RuntimeError):
    """Raised when an automatic update step fails."""


class UpdateCancelled(UpdateError):
    """Raised when the user cancels the active automatic update."""


@dataclass
class UpdatePayload:
    version: str
    build: str = ""
    changelog: str = ""
    download_windows: str = ""
    download_linux: str = ""
    download_appimage: str = ""


@dataclass
class UpdateResult:
    success: bool = True
    message: str = ""
    quit_app: bool = False
    data: Dict[str, Any] = field(default_factory=dict)


class UpdateContext:
    """Thread-safe bridge used by update flows."""

    def __init__(
            self,
            window,
            cancel_event: threading.Event,
            progress_cb: Callable[[dict], None],
            confirm_cb: Callable[[str, str], bool],
    ):
        self.window = window
        self.cancel_event = cancel_event
        self._progress_cb = progress_cb
        self._confirm_cb = confirm_cb

    def check_cancelled(self):
        if self.cancel_event.is_set():
            raise UpdateCancelled("Update cancelled")

    def confirm(self, title: str, message: str) -> bool:
        self.check_cancelled()
        return bool(self._confirm_cb(title, message))

    def progress(
            self,
            status: str,
            percent: Optional[int] = None,
            received: int = 0,
            total: int = 0,
            speed: float = 0.0,
            eta: Optional[float] = None,
    ):
        self._progress_cb({
            "status": status,
            "percent": percent,
            "received": int(received or 0),
            "total": int(total or 0),
            "speed": float(speed or 0.0),
            "eta": eta,
        })

    def run_process(
            self,
            command: List[str],
            cwd: Optional[str] = None,
            status: str = "",
            env: Optional[dict] = None,
    ) -> subprocess.CompletedProcess:
        """Run a cancellable subprocess and return captured output."""
        self.check_cancelled()
        if status:
            self.progress(status, percent=None)

        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if hasattr(subprocess, "STARTUPINFO"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)

        with tempfile.TemporaryFile(mode="w+b") as output:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            while proc.poll() is None:
                if self.cancel_event.wait(0.15):
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    raise UpdateCancelled("Update cancelled")

            output.flush()
            output.seek(0)
            detail = output.read().decode("utf-8", errors="replace").strip()

        result = subprocess.CompletedProcess(command, proc.returncode, detail, "")
        if result.returncode != 0:
            if len(detail) > 3000:
                detail = detail[-3000:]
            raise UpdateError(
                f"Command failed ({result.returncode}): {' '.join(command)}"
                + (f"\n\n{detail}" if detail else "")
            )
        return result


class BaseUpdateFlow:
    id = "base"

    def __init__(self, window, payload: UpdatePayload, context: UpdateContext):
        self.window = window
        self.payload = payload
        self.context = context

    def run(self) -> UpdateResult:
        raise NotImplementedError
