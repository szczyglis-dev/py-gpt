#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from typing import Optional, Any, Dict, List

from PySide6.QtCore import QObject, QRunnable
from typing_extensions import deprecated

from .plugin import BasePlugin
from .signals import BaseSignals


class BaseWorker(QObject, QRunnable):
    def __init__(self, plugin: Optional[BasePlugin] = None, *args, **kwargs):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.plugin = plugin
        self.window = None
        self.signals = BaseSignals()
        self.args = args
        self.kwargs = kwargs
        self.cmds = None
        self.ctx = None

    def debug(self, msg: str):
        """
        Emit debug signal

        :param msg: debug message
        """
        if self.signals is not None and hasattr(self.signals, "debug"):
            self.signals.debug.emit(msg)

    def destroyed(self):
        """Emit destroyed signal"""
        if self.signals is not None and hasattr(self.signals, "destroyed"):
            self.signals.destroyed.emit()

    def error(self, err: Any):
        """
        Emit error signal

        :param err: error message
        """
        if self.signals is not None and hasattr(self.signals, "error"):
            self.signals.error.emit(err)

    def log(self, msg: str):
        """
        Emit log signal

        :param msg: log message
        """
        if self.is_threaded():
            return
        if self.signals is not None and hasattr(self.signals, "log"):
            self.signals.log.emit(msg)

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
        # if tool call from agent_llama mode, then send direct reply to plugin -> dispatcher -> reply
        if self.ctx is not None and self.ctx.agent_call and self.plugin is not None:
            self.plugin.handle_finished(response, self.ctx, extra_data)
            return

        if self.signals is not None and hasattr(self.signals, "finished"):
            self.signals.finished.emit(response, self.ctx, extra_data)

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
        # if tool call from agent_llama mode, then send direct reply to plugin -> dispatcher -> reply
        if self.ctx.agent_call and self.plugin is not None:
            self.plugin.handle_finished_more(responses, self.ctx, extra_data)
            return

        if self.signals is not None and hasattr(self.signals, "finished_more"):
            self.signals.finished_more.emit(responses, self.ctx, extra_data)

    def started(self):
        """Emit started signal"""
        if self.signals is not None and hasattr(self.signals, "started"):
            self.signals.started.emit()

    def status(self, msg: str):
        """
        Emit status signal

        :param msg: status message
        """
        if self.is_threaded():
            return
        if self.signals is not None and hasattr(self.signals, "status"):
            self.signals.status.emit(msg)

    def stopped(self):
        """Emit stopped signal"""
        if self.signals is not None and hasattr(self.signals, "stopped"):
            self.signals.stopped.emit()

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
        return {"cmd": item["cmd"]}

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
        """Run asynchronous"""
        if self.window:
            self.window.threadpool.start(self)
        else:
            self.run()
