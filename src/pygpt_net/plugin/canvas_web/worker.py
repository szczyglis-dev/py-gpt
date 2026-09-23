#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 18:40:00                  #
# ================================================== #

import os
import threading
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname
from pathlib import Path

from PySide6.QtCore import Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    call = Signal(str, dict, object, object)


class Worker(BaseWorker):
    WAIT_TIMEOUT = 90.0

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.signals = WorkerSignals()

    def from_defaults(self, parent):
        super().from_defaults(parent)
        self.signals.call.connect(parent.on_browser_call)

    def _secure_local_reference(self, value: str, workdir: str, *, force_relative: bool = False):
        """Validate local file/directory references without treating normal web URLs as host paths."""
        raw = str(value or "").strip()
        if not raw:
            return raw
        parsed = urlparse(raw)
        if parsed.scheme == "file":
            local = url2pathname(unquote(parsed.path))
            if parsed.netloc and parsed.netloc not in ("", "localhost"):
                local = f"//{parsed.netloc}{local}"
            checked = self.security_read(local)
            return Path(checked).resolve().as_uri()
        if parsed.scheme:
            return raw

        expanded = os.path.expanduser(raw)
        candidate = expanded if os.path.isabs(expanded) else os.path.join(workdir or os.getcwd(), expanded)
        candidate = os.path.abspath(candidate)
        is_local_hint = (
            force_relative
            or os.path.isabs(expanded)
            or raw.startswith((".", "~"))
            or os.path.exists(candidate)
        )
        if is_local_hint:
            return self.security_read(candidate)
        return raw

    def _call(self, cmd: str, params: dict):
        params = dict(params or {})
        workdir = self.get_workdir()
        params.setdefault("__workdir", workdir)
        if cmd == "canvas_screenshot" and params.get("path"):
            output = os.path.expanduser(str(params["path"]))
            if not os.path.isabs(output):
                output = os.path.join(workdir or os.getcwd(), output)
            params["path"] = self.security_write(os.path.abspath(output))
        if cmd == "web_server_start" and params.get("path"):
            params["path"] = self._secure_local_reference(params["path"], workdir, force_relative=True)
        if cmd == "canvas_upload" and params.get("path"):
            params["path"] = self._secure_local_reference(params["path"], workdir, force_relative=True)
        if cmd == "canvas_open" and params.get("url"):
            params["url"] = self._secure_local_reference(params["url"], workdir)
        if cmd == "canvas_set_html" and params.get("base_url"):
            params["base_url"] = self._secure_local_reference(params["base_url"], workdir)
        ret = {}
        done = threading.Event()
        if not safe_emit(self.signals, "call", cmd, params, ret, done):
            raise RuntimeError("Canvas/web browser runtime is not available")
        if not done.wait(self.WAIT_TIMEOUT):
            raise TimeoutError(f"Canvas/web browser operation timed out: {cmd}")
        if ret.get("error"):
            raise RuntimeError(str(ret["error"]))
        return ret.get("result")

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds or []:
                if self.is_stopped():
                    break
                cmd = item.get("cmd")
                if cmd not in self.plugin.allowed_cmds:
                    continue
                if not (self.plugin.has_cmd(cmd) or item.get("force")):
                    continue
                try:
                    result = self._call(cmd, item.get("params") or {})
                    response = self.make_response(item, result, extra={"plugin": self.plugin.id, "cmd": cmd})
                    responses.append(response)
                    if cmd == "canvas_screenshot" and isinstance(result, dict):
                        self.plugin.attach_screenshot_to_ctx(self.ctx, result.get("path"))
                except Exception as exc:
                    # Runtime browser/DOM errors are normal tool outcomes (a stale
                    # selector, missing element, navigation race, etc.). The main
                    # thread already logs them and places the message in the bottom
                    # status bar; return the error to the model without an alert.
                    responses.append(self.make_response(
                        item,
                        f"Error: {exc}",
                        extra={"plugin": self.plugin.id, "cmd": cmd},
                    ))
            if responses:
                self.reply_more(responses)
        except Exception as exc:
            # Keep unexpected worker failures non-modal for this browser plugin.
            self.debug(f"{self.plugin.name}: {exc}")
        finally:
            self.cleanup()
