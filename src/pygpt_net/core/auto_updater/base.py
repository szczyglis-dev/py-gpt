#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 20:00:00                  #
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
            log_cb: Optional[Callable[[str], None]] = None,
            debug_enabled_cb: Optional[Callable[[], bool]] = None,
    ):
        self.window = window
        self.cancel_event = cancel_event
        self._progress_cb = progress_cb
        self._confirm_cb = confirm_cb
        self._log_cb = log_cb
        self._debug_enabled_cb = debug_enabled_cb

    @property
    def debug_enabled(self) -> bool:
        try:
            return bool(self._debug_enabled_cb and self._debug_enabled_cb())
        except Exception:
            return False

    def log(self, message: str):
        try:
            if self._log_cb is not None:
                self._log_cb(str(message))
        except Exception:
            pass

    def check_cancelled(self):
        if self.cancel_event.is_set():
            self.log("Cancellation flag detected; aborting current update step.")
            raise UpdateCancelled("Update cancelled")

    def confirm(self, title: str, message: str) -> bool:
        self.check_cancelled()
        self.log(f"Confirmation requested: title={title!r}, message={message!r}")
        result = bool(self._confirm_cb(title, message))
        self.log(f"Confirmation result: {'YES' if result else 'NO'}")
        return result

    def progress(
            self,
            status: str,
            percent: Optional[int] = None,
            received: int = 0,
            total: int = 0,
            speed: float = 0.0,
            eta: Optional[float] = None,
    ):
        data = {
            "status": status,
            "percent": percent,
            "received": int(received or 0),
            "total": int(total or 0),
            "speed": float(speed or 0.0),
            "eta": eta,
        }
        self.log(
            "Progress: "
            f"status={status!r}, percent={percent!r}, "
            f"received={data['received']}, total={data['total']}, "
            f"speed={data['speed']:.2f} B/s, eta={eta!r}"
        )
        self._progress_cb(data)

    def run_process(
            self,
            command: List[str],
            cwd: Optional[str] = None,
            status: str = "",
            env: Optional[dict] = None,
    ) -> subprocess.CompletedProcess:
        """Run a cancellable subprocess and return captured output."""
        self.check_cancelled()
        command_text = subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command)
        self.log(f"Starting process: command={command_text!r}, cwd={cwd!r}")
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
            self.log(f"Process started: pid={proc.pid}")
            while proc.poll() is None:
                if self.cancel_event.wait(0.15):
                    self.log(f"Cancellation requested; terminating process pid={proc.pid}.")
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                        self.log(f"Process pid={proc.pid} terminated cleanly.")
                    except Exception as exc:
                        self.log(f"Terminate failed for pid={proc.pid}: {exc}; trying kill().")
                        try:
                            proc.kill()
                            self.log(f"Process pid={proc.pid} killed.")
                        except Exception as kill_exc:
                            self.log(f"Unable to kill process pid={proc.pid}: {kill_exc}")
                    raise UpdateCancelled("Update cancelled")

            output.flush()
            output.seek(0)
            detail = output.read().decode("utf-8", errors="replace").strip()

        self.log(f"Process finished: pid={proc.pid}, returncode={proc.returncode}")
        if detail:
            self.log(f"Process output:\n{detail}")
        else:
            self.log("Process output: <empty>")

        result = subprocess.CompletedProcess(command, proc.returncode, detail, "")
        if result.returncode != 0:
            error_detail = detail
            if len(error_detail) > 3000:
                error_detail = error_detail[-3000:]
            raise UpdateError(
                f"Command failed ({result.returncode}): {' '.join(command)}"
                + (f"\n\n{error_detail}" if error_detail else "")
            )
        return result


class BaseUpdateFlow:
    id = "base"

    def __init__(self, window, payload: UpdatePayload, context: UpdateContext):
        self.window = window
        self.payload = payload
        self.context = context

    def log(self, message: str):
        self.context.log(f"[{self.id}] {message}")

    def run(self) -> UpdateResult:
        raise NotImplementedError
