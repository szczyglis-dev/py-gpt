#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 17:30:00                  #
# ================================================== #

import os
import threading
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname
from pathlib import Path

from PySide6.QtCore import Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
)
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

    def _is_agents_mode(self) -> bool:
        """Return True when the application is currently in an agent mode."""
        try:
            mode = self.plugin.window.core.config.get("mode")
            return mode in (MODE_AGENT, MODE_AGENT_LLAMA, MODE_AGENT_OPENAI, MODE_AGENT_V2)
        except Exception:
            return False

    def _is_files_io_enabled(self) -> bool:
        """Return the live Files I/O plugin state without assuming UI availability."""
        try:
            controller = self.plugin.window.controller.plugins
            return bool(controller.is_enabled("cmd_files"))
        except Exception:
            return False

    def _prepare_painter_runtime_artifact(self, result: dict) -> dict:
        """Normalize a Painter snapshot through the shared runtime tmp mapping."""
        path = str(result.get("path") or "").strip()
        if not path:
            raise RuntimeError("Painter image capture returned no file")

        name = str(result.get("name") or os.path.basename(path))
        artifact = self.plugin.window.core.filesystem.materialize_runtime_artifact(
            path,
            ctx=self.ctx,
            name=name,
        )
        if not artifact:
            raise RuntimeError("Painter image could not be prepared in runtime temporary storage")
        return artifact

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
                    if cmd == "get_user_painter_image" and isinstance(result, dict):
                        artifact = self._prepare_painter_runtime_artifact(result)
                        model_path = str(artifact.get("path") or artifact.get("host_path") or "")
                        host_path = str(artifact.get("host_path") or model_path)
                        name = str(artifact.get("name") or os.path.basename(host_path))

                        # Agents own their file/tool loop, so never inject an
                        # automatic image continuation there.  Likewise, when
                        # Files I/O is enabled in a normal mode, return the tmp
                        # path and let the model explicitly call
                        # attach_runtime_file, exactly like any other local file.
                        if self._is_agents_mode() or self._is_files_io_enabled():
                            response = self.make_response(
                                item,
                                {"path": model_path},
                                extra={"plugin": self.plugin.id, "cmd": cmd},
                            )
                        else:
                            # Files I/O is unavailable, so fall back to the same
                            # runtime-only transport contract used by
                            # cmd_files.attach_runtime_file.  This keeps normal
                            # Chat usable without introducing a second image
                            # attachment protocol.
                            attached = f"Attached for native analysis in the next model request: {name}"
                            response = self.make_response(
                                item,
                                attached,
                                extra={
                                    "plugin": self.plugin.id,
                                    "cmd": cmd,
                                    "agent_runtime_attachments": [
                                        {"path": host_path, "name": name},
                                    ],
                                },
                            )
                    else:
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
