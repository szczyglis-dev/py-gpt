#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 00:00:00                  #
# ================================================== #

import json

from typing import Optional, Any, Dict, List

from PySide6.QtCore import QRunnable
from typing_extensions import deprecated

from pygpt_net.core.agents_v2.tool_bridge import mark_pending

from .plugin import BasePlugin
from .signals import BaseSignals


class BaseWorker(QRunnable):
    def __init__(
            self,
            plugin: Optional[BasePlugin] = None,
            *args,
            **kwargs
    ):
        super().__init__()
        self.plugin = plugin
        self.window = None
        self.signals = BaseSignals()
        self.args = args
        self.kwargs = kwargs
        self.cmds = None
        self.ctx = None

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass

    def _emit(self, name: str, *args) -> bool:
        """Safely emit a signal if it still exists.

        Guards against the race where ``cleanup()`` has already requested the
        signals object be deleted (or a queued emission is in flight) while a
        worker thread is still attempting to emit.
        """
        sig = self.signals
        if sig is None:
            return False
        try:
            signal = getattr(sig, name, None)
            if signal is None or not callable(getattr(signal, "emit", None)):
                return False
            signal.emit(*args)
            return True
        except RuntimeError:
            # C++ object already deleted under us
            return False
        except Exception:
            return False

    def debug(self, msg: str):
        """
        Emit debug signal

        :param msg: debug message
        """
        self._emit("debug", msg)

    def destroyed(self):
        """Emit destroyed signal"""
        self._emit("destroyed")

    def error(self, err: Any):
        """
        Emit error signal

        :param err: error message
        """
        self._emit("error", err)

    def log(self, msg: str):
        """
        Emit log signal

        :param msg: log message
        """
        if self.is_threaded():
            return
        self._emit("log", msg)

    @deprecated("From 2.1.29: BaseWorker.response() is deprecated, use BaseWorker.reply() instead")
    def response(
            self,
            response: Dict[str, Any],
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Emit finished signal (deprecated)

        :param response: response (dict)
        :param extra_data: extra data
        """
        # show warning
        self.debug("BaseWorker.response is deprecated from 2.1.29, use BaseWorker.reply instead")
        self.reply(response, extra_data)

    def reply(
            self,
            response: Dict[str, Any],
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Emit finished signal (on reply from command output)

        :param response: response (dict)
        :param extra_data: extra data
        """
        # Legacy agents historically called the plugin handler directly. Agents
        # v2 must not do that from a QRunnable thread: emit the Qt signal instead
        # so QObject slots and REPLY_ADD are delivered on the receiver thread.
        if self.ctx is not None and self.ctx.agent_call and self.plugin is not None:
            extra = self.ctx.extra if isinstance(self.ctx.extra, dict) else {}
            if not extra.get("agents_v2_async_tool"):
                self.plugin.handle_finished(response, self.ctx, extra_data)
                return

        self._emit("finished", response, self.ctx, extra_data)

    def reply_more(
            self,
            responses: List[Dict[str, Any]],
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Emit finished_more signal (on reply from command output, multiple responses)

        :param responses: list of responses dicts  TODO: add ResponseContext
        :param extra_data: extra data
        """
        # See reply(): Agents v2 routes completion through Qt's queued signal
        # path so plugin result handling never runs directly on a worker thread.
        if self.ctx is not None and self.ctx.agent_call and self.plugin is not None:
            extra = self.ctx.extra if isinstance(self.ctx.extra, dict) else {}
            if not extra.get("agents_v2_async_tool"):
                self.plugin.handle_finished_more(responses, self.ctx, extra_data)
                return

        self._emit("finished_more", responses, self.ctx, extra_data)

    def started(self):
        """Emit started signal"""
        self._emit("started")

    def status(self, msg: str):
        """
        Emit status signal

        :param msg: status message
        """
        if self.is_threaded():
            return
        self._emit("status", msg)

    def stopped(self):
        """Emit stopped signal"""
        self._emit("stopped")

    def is_threaded(self) -> bool:
        """
        Check if plugin is threaded

        :return: True if threaded
        """
        if self.plugin is not None:
            return self.plugin.is_threaded()
        return False

    def from_defaults(self, parent: BasePlugin):
        """
        Initialize defaults from parent plugin

        :param parent: parent plugin
        """
        self.plugin = parent
        self.window = parent.window

        # connect base signals
        self.signals.finished.connect(parent.handle_finished)
        self.signals.finished_more.connect(parent.handle_finished_more)
        self.signals.log.connect(parent.handle_log)
        self.signals.debug.connect(parent.handle_debug)
        self.signals.status.connect(parent.handle_status)
        self.signals.error.connect(parent.handle_error)

    def from_request(
            self,
            item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        append_params = ("path", "query")
        data = {"cmd": item["cmd"]}
        if "params" in item and isinstance(item["params"], dict):
            for k in append_params:
                if k in item["params"]:
                    value = item["params"][k]
                    try:
                        # Keep JSON-native types intact in the request echoed
                        # with the tool result. In particular, list-valued
                        # paths must remain JSON arrays instead of becoming a
                        # Python repr string such as "['file.txt']".
                        data[k] = json.loads(json.dumps(value, ensure_ascii=False))
                    except (TypeError, ValueError, OverflowError):
                        # Keep the old safety net for non-JSON internal values.
                        data[k] = str(value)
        return data

    def make_response(
            self,
            item: Dict[str, Any],
            result: Any,
            extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare response item

        :param item: item with parameters
        :param result: result
        :param extra: extra data
        :return: response item
        """
        request = self.from_request(item)
        response = {
            "request": request,
            "result": result,
        }
        if extra:
            response.update(extra)
        return response

    def security_read(self, path: str, sandbox: bool = False) -> str:
        """Validate host-side plugin file read access."""
        if self.plugin is None or self.plugin.window is None:
            return path
        return self.plugin.window.core.security.ensure_read(path, sandbox=sandbox)

    def security_write(self, path: str, sandbox: bool = False) -> str:
        """Validate host-side plugin file write access."""
        if self.plugin is None or self.plugin.window is None:
            return path
        return self.plugin.window.core.security.ensure_write(path, sandbox=sandbox)

    def security_command(self, command: str, sandbox: bool = False):
        """Validate host-side plugin system command access."""
        if self.plugin is None or self.plugin.window is None:
            return []
        return self.plugin.window.core.security.ensure_command(command, sandbox=sandbox)

    def throw_error(self, e: Exception) -> str:
        """
        Handle error

        :param e: exception
        """
        msg = "Error: {}".format(e)
        self.error(e)
        self.log(msg)
        return msg

    def has_param(
            self,
            item: Dict[str, Any],
            param: str
    ) -> bool:
        """
        Check if item has parameter

        :param item: item with parameters
        :param param: parameter name
        :return: True if item has parameter
        """
        if item is None:
            return False
        return "params" in item and param in item["params"]

    def get_param(
            self,
            item: Dict[str, Any],
            param: str,
            default: Any = None
    ) -> Any:
        """
        Get parameter value from item

        :param item: item with parameters
        :param param: parameter name
        :param default: default value
        :return: parameter value
        """
        if self.has_param(item, param):
            return item["params"][param]
        return default

    def is_stopped(self) -> bool:
        """
        Check if worker is stopped

        :return: True if stopped
        """
        if self.plugin is not None:
            return self.plugin.window.controller.kernel.stopped()
        return False

    def run_sync(self):
        """Run synchronous"""
        self.run()

    def run_async(self):
        """Run asynchronous."""
        # Agents v2 waits for the plugin reply instead of for dispatch() to
        # return. Mark the context so the Qt-side bridge knows an asynchronous
        # worker has actually been scheduled and must not complete the tool call
        # prematurely.
        try:
            if self.ctx is not None and isinstance(self.ctx.extra, dict) \
                    and self.ctx.extra.get("agents_v2_async_tool"):
                mark_pending(self.ctx, True)
        except Exception:
            pass
        if self.window:
            self.window.threadpool.start(self)
        else:
            self.run()

