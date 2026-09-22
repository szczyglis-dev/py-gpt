#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 02:20:00                  #
# ================================================== #

import locale
import os.path
import re
import threading

from pygpt_net.core.qt import safe_emit
from pygpt_net.item.ctx import CtxItem


class Runner:
    def __init__(self, plugin=None):
        """
        Cmd Runner

        :param plugin: plugin
        """
        self.plugin = plugin
        self._signals_local = threading.local()
        self.signals = None

    @property
    def signals(self):
        """Return signals attached to the current worker thread."""
        return getattr(self._signals_local, "value", None)

    @signals.setter
    def signals(self, signals):
        self._signals_local.value = signals

    def attach_signals(self, signals):
        """Attach signals to the current worker thread."""
        self.signals = signals

    def detach_signals(self, signals=None):
        """Detach signals from the current worker thread if they still match."""
        current = self.signals
        if signals is None or current is signals:
            self.signals = None

    def _emit_signal(self, name: str, *args) -> bool:
        """Safely emit through the current worker's Qt signal object."""
        signals = self.signals
        if signals is None:
            return False
        emitted = safe_emit(signals, name, *args)
        if not emitted and self.signals is signals:
            self.detach_signals(signals)
        return emitted

    def send_interpreter_input(self, data: str):
        """
        Send input to subprocess

        :param data: input text
        """
        type = "stdin"
        if self.signals is not None:
            self.send_interpreter_output_begin(type)
            self._emit_signal("output", data, type)
            self.send_interpreter_output_end(type)

    def send_interpreter_output(self, data: str, type: str):
        """
        Send output to interpreter

        :param data: output text
        :param type: output type (stdout/stderr)
        """
        self._emit_signal("output", data, type)

    def send_interpreter_output_begin(self, type: str):
        """
        Send output begin to interpreter

        :param type: output type (stdout/stderr)
        """
        self._emit_signal("output_begin", type)

    def send_interpreter_output_end(self, type: str):
        """
        Send output end to interpreter

        :param type: output type (stdout/stderr)
        """
        self._emit_signal("output_end", type)

    def send_html_output(self, data: str, ctx=None):
        """Send HTML output to canvas with its host-side asset base directory."""
        base_dir = self.plugin.window.core.filesystem.get_data_dir(ctx=ctx)
        self._emit_signal("html_output", {
            "html": data,
            "base_dir": base_dir,
        })

    @staticmethod
    def decode_subprocess_output(data) -> str:
        """Decode subprocess output without assuming UTF-8 on Windows.

        Windows console programs commonly emit the active OEM code page when
        stdout/stderr are redirected (for example ``dir``/``tree``), while some
        utilities emit UTF-16.  Always prefer Unicode encodings when they are
        detectable, then fall back to the Windows OEM/system code pages.
        """
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if not isinstance(data, (bytes, bytearray)):
            return str(data)

        raw = bytes(data)
        if not raw:
            return ""

        # Explicit BOMs are authoritative.  ``utf-16`` consumes either endian
        # BOM and avoids leaving U+FEFF in the returned text.
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            try:
                return raw.decode("utf-16")
            except UnicodeDecodeError:
                pass
        if raw.startswith(b"\xef\xbb\xbf"):
            try:
                return raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                pass

        encodings = ["utf-8"]

        if os.name == "nt":
            # cmd.exe and many classic Windows utilities write using the OEM
            # console code page (e.g. cp852 on a Polish Windows installation).
            try:
                import ctypes
                oem_cp = int(ctypes.windll.kernel32.GetOEMCP())
                if oem_cp > 0:
                    encodings.append(f"cp{oem_cp}")
            except Exception:
                pass

        try:
            preferred = locale.getpreferredencoding(False)
            if preferred:
                encodings.append(preferred)
        except Exception:
            pass

        if os.name == "nt":
            encodings.append("mbcs")

        # UTF-16 output without a BOM is uncommon but does occur in some
        # Windows command-line utilities.  Try it only when NUL density makes
        # UTF-16 plausible, so normal single-byte output is not misdetected.
        if raw.count(b"\x00") >= max(2, len(raw) // 5):
            encodings.extend(("utf-16-le", "utf-16-be"))

        seen = set()
        for encoding in encodings:
            key = str(encoding).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                return raw.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue

        # Output shown to the user/model must never crash the tool solely due
        # to an unknown process encoding.
        return raw.decode("utf-8", errors="replace")

    def handle_result(self, stdout, stderr, log_category: str = "code"):
        """
        Handle result from subprocess

        :param stdout: stdout
        :param stderr: stderr
        :return: result
        """
        result = None
        if stdout:
            result = self.decode_subprocess_output(stdout)
            self.send_interpreter_output(result, "stdout")
            self.log("STDOUT: {}".format(result), category=log_category)
        if stderr:
            result = self.decode_subprocess_output(stderr)
            self.send_interpreter_output(result, "stderr")
            self.log("STDERR: {}".format(result), category=log_category)
        if result is None:
            result = "No result (STDOUT/STDERR empty)"
            self.log(result, category=log_category)
        return result

    def handle_result_sandbox(self, response, log_category: str = "code") -> str:
        """
        Handle result from sandbox backend

        :param response: response
        :return: result
        """
        result = None
        if response:
            result = self.decode_subprocess_output(response)
        self.send_interpreter_output(result, "stdout")
        self.log(
            "Result: {}".format(result),
            sandbox=True,
            category=log_category,
        )
        return result

    def handle_result_ipython(self, ctx: CtxItem, response) -> str:
        """
        Handle result from ipython container, check for files and images

        :param ctx: CtxItem
        :param response: response
        :return: result
        """
        paths = self.plugin.window.core.filesystem.parser.extract_data_files(ctx, response)
        if len(paths) == 0:
            self.plugin.window.core.filesystem.parser.extract_data_files(ctx, ctx.input)
        return response

    def is_sandbox(self) -> bool:
        """Return True when the current execution backend is sandboxed."""
        return self.plugin.get_execution_backend().sandboxed

    def ipython_exec(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        backend = self.plugin.get_execution_backend()
        sandbox = backend.sandboxed
        preparing = backend.consume_preparing_response(request)
        if preparing is not None:
            return preparing
        data = item["params"]['code']

        # Model/tool executions should recover a genuinely dead kernel once on
        # their own. The kernel backends suppress duplicate restart bursts.
        auto_init = True
        if "auto_init" in item["params"]:
            auto_init = item["params"]['auto_init']

        # check if command is to restart the kernel
        if data.strip().startswith("/restart"):
            return self.ipython_kernel_restart(ctx, item, request, all)

        if not all:
            path = self.plugin.window.tools.get("interpreter").file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            msg = "Saving Python file: {}".format(path)
            self.log(msg, sandbox=sandbox)
            host_path = self.prepare_path(path, on_host=True, ctx=ctx)
            self.plugin.window.core.security.ensure_write(host_path, sandbox=sandbox, ctx=ctx)
            with open(host_path, 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.plugin.window.tools.get("interpreter").file_input

        host_path = self.prepare_path(path, on_host=True, ctx=ctx)
        self.plugin.window.core.security.ensure_read(host_path, sandbox=sandbox, ctx=ctx)
        with open(host_path, 'r', encoding="utf-8") as file:
            data = file.read()

        self.append_input(data, ctx=ctx)
        self.send_interpreter_input(data)  # send input to interpreter tool

        # run code in IPython interpreter
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=sandbox)
        self.log("Connecting to IPython interpreter...", sandbox=sandbox)
        try:
            self.log("Please wait...", sandbox=sandbox)
            self.send_interpreter_output_begin("stdout")
            result = backend.execute_ipython(
                data,
                ctx=ctx,
                auto_init=auto_init,  # auto initialize after error
            )
            result = self.handle_result_ipython(ctx, result)
            self.log("Python Code Executed.", sandbox=sandbox)
        except Exception as e:
            self.error(e)
            result = str(e)
        self.send_interpreter_output_end("stdout")
        return {
            "request": request,
            "result": str(result),
            "context": "IPYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result, ctx=ctx),
        }

    def ipython_kernel_restart(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        backend = self.plugin.get_execution_backend()
        sandbox = backend.sandboxed
        preparing = backend.consume_preparing_response(request)
        if preparing is not None:
            return preparing
        self.append_input("", ctx=ctx)
        self.send_interpreter_input("")  # send input to interpreter tool

        # restart IPython interpreter
        self.log("Connecting to IPython interpreter...", sandbox=sandbox)
        try:
            self.log("Restarting IPython kernel...", sandbox=sandbox)
            response = backend.restart_ipython(ctx=ctx)
        except Exception as e:
            self.error(e)
            response = False
        if response:
            result = (
                "Kernel is ready. The restart request completed or a duplicate "
                "restart was skipped because the kernel had just been restarted. "
                "Do not restart it again unless a later execution reports a real kernel failure."
            )
        else:
            result = (
                "Kernel restart failed or another restart is already in progress. "
                "Do not retry restart in a loop."
            )
        self.log(result, sandbox=sandbox)
        return {
            "request": request,
            "result": str(result),
            "context": "IPYTHON OUTPUT:\n--------------------------------\n" + self.parse_result(result, ctx=ctx),
        }

    def parse_result(self, result, ctx=None):
        """
        Parse result

        :param result: result
        :return: parsed result
        """
        if result is None:
            return ""
        img_ext = ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]
        if result.strip().split(".")[-1].lower() in img_ext:
            path = self.prepare_path(result.strip().replace("file://", ""), on_host=True, ctx=ctx)
            if os.path.isfile(path):
                return "![Image](file://{})".format(path)
        return str(result)

    def append_input(self, data: str, ctx=None):
        """
        Append input to interpreter input file

        :param data: input data
        """
        if not self.plugin.get_option_value("attach_output"):
            return

        content = ""
        path = self.prepare_path(self.plugin.window.tools.get("interpreter").file_input, on_host=True, ctx=ctx)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        with open(path, "a", encoding="utf-8") as f:
            nl = ""
            if content != "":
                nl = "\n"
            if data != "":
                f.write(nl + data)
            else:
                f.write("")

    def prepare_path(self, path: str, on_host: bool = True, ctx=None) -> str:
        """Translate a path using the active execution backend."""
        return self.plugin.get_execution_backend().prepare_path(
            path,
            on_host=on_host,
            ctx=ctx,
        )

    def error(self, err: any):
        """
        Log error message

        :param err: exception or error message
        """
        self._emit_signal("error", err)

    def status(self, msg: str):
        """
        Send status message

        :param msg: status message
        """
        self._emit_signal("status", msg)

    def debug(self, msg: any):
        """
        Log debug message

        :param msg: message to log
        """
        self._emit_signal("debug", msg)

    def log(self, msg, sandbox: bool = False, category: str = "code"):
        """Log a message using the code or system-exec Python channel."""
        prefix = ""
        if sandbox:
            prefix = self.plugin.get_execution_backend().log_prefix
        full_msg = (prefix + " " if prefix else "") + str(msg)

        if category == "exec":
            self._emit_signal("log", {
                "__pygpt_python_log__": True,
                "prefix": "Python -> exec",
                "message": full_msg,
            })
        else:
            self._emit_signal("log", full_msg)
