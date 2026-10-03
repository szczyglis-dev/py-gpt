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
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class _PreviewHandler(SimpleHTTPRequestHandler):
    """Loopback preview handler which never follows symlinks outside its configured root."""

    RUNTIME_PATH = "/__pygpt_runtime__.html"

    def __init__(self, *args, runtime_html_getter=None, **kwargs):
        self.runtime_html_getter = runtime_html_getter
        super().__init__(*args, **kwargs)

    def _runtime_html(self):
        if self.path.split("?", 1)[0] != self.RUNTIME_PATH or not callable(self.runtime_html_getter):
            return None
        value = self.runtime_html_getter()
        return "" if value is None else str(value)

    def do_GET(self):
        runtime_html = self._runtime_html()
        if runtime_html is None:
            return super().do_GET()
        data = runtime_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        runtime_html = self._runtime_html()
        if runtime_html is None:
            return super().do_HEAD()
        data = runtime_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def translate_path(self, path):
        translated = super().translate_path(path)
        root = os.path.realpath(self.directory or os.getcwd())
        target = os.path.realpath(translated)
        try:
            inside = os.path.commonpath([root, target]) == root
        except ValueError:
            inside = False
        if not inside:
            return os.path.join(root, ".__pygpt_forbidden__")
        return target

    def log_message(self, fmt, *args):
        return


class PreviewServer:
    """Serve local assets and the active HTML document over loopback."""

    def __init__(self, runtime):
        self.runtime = runtime

    def start(self, root, port=0):
        runtime = self.runtime
        root = os.path.realpath(os.path.abspath(os.path.expanduser(str(root))))
        if not os.path.isdir(root):
            raise NotADirectoryError(root)
        port = int(port or 0)
        if runtime.server is not None and runtime.server_root == root:
            current_port = int(runtime.server.server_address[1])
            if port in (0, current_port):
                return runtime.server_url
        self.stop()
        handler = partial(
            _PreviewHandler,
            directory=root,
            runtime_html_getter=lambda: runtime.runtime_html,
        )
        runtime.server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        runtime.server.daemon_threads = True
        actual_port = int(runtime.server.server_address[1])
        runtime.server_root = root
        runtime.server_url = f"http://127.0.0.1:{actual_port}/"
        runtime.server_thread = threading.Thread(target=runtime.server.serve_forever, daemon=True, name="PyGPT-WebPreview")
        runtime.server_thread.start()
        return runtime.server_url

    def stop(self):
        runtime = self.runtime
        server = runtime.server
        runtime.server = None
        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass
        runtime.server_thread = None
        runtime.server_root = None
        runtime.server_url = None

    def state(self):
        runtime = self.runtime
        return {"running": runtime.server is not None, "root": runtime.server_root, "url": runtime.server_url}
