#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.16 05:00:00                  #
# ================================================== #

import copy

from PySide6.QtCore import QObject, Signal, QRunnable, Slot, QTimer
from typing_extensions import deprecated

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class BasePlugin(QObject):
    def __init__(self, *args, **kwargs):
        super(BasePlugin, self).__init__()
        self.window = kwargs.get('window', None)
        self.id = ""
        self.name = ""
        self.type = []  # Types:
        # audio.input, audio.output, image.input, image.output, schedule, text.input, text.output, vision
        self.description = ""
        self.urls = {}
        self.options = {}
        self.initial_options = {}
        self.allowed_cmds = []
        self.tabs = {}
        self.parent = None
        self.enabled = False
        self.use_locale = False
        self.order = 0

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def add_option(self, name: str, type: str, **kwargs) -> dict:
        """
        Add plugin configuration option

        :param name: option name (ID, key)
        :param type: option type (text, textarea, bool, int, float, dict, combo)
        :param kwargs: additional keyword arguments for option properties
        :return: added option config dict
        """
        defaults = {
            "value": None,
            "label": "",
            "description": "",
            "tooltip": None,
            "min": None,
            "max": None,
            "multiplier": 1,
            "step": 1,
            "slider": False,
            "keys": None,
            "advanced": False,
            "secret": False,
            "persist": False,
            "urls": None,
            "use": None,
        }
        option = {**defaults, **kwargs}
        option['tooltip'] = option['tooltip'] or option['description']
        option["id"] = name
        option["type"] = type
        self.options[name] = option
        return option

    def add_cmd(self, cmd: str, **kwargs) -> dict:
        """
        Add plugin command

        :param cmd: command name
        :param kwargs: additional keyword arguments for command properties
        :return: added option config dict
        """
        cmd_syntax = {
            "instruction": "",  # instruction for model
            "params": {},  # parameters
            "enabled": True,  # enabled
        }
        if "instruction" in kwargs and isinstance(kwargs.get("instruction"), str):
            cmd_syntax["instruction"] = kwargs.get("instruction")
            kwargs.pop("instruction")
        if "params" in kwargs and isinstance(kwargs.get("params"), list):
            cmd_syntax["params"] = kwargs.get("params")
            kwargs.pop("params")
        if "enabled" in kwargs and isinstance(kwargs.get("enabled"), bool):
            cmd_syntax["enabled"] = kwargs.get("enabled")
            kwargs.pop("enabled")

        name = "cmd." + cmd
        kwargs["cmd"] = cmd
        kwargs["value"] = cmd_syntax

        # static keys
        kwargs["params_keys"] = {
            "name": "text",
            "type": {
                "type": "combo",
                "use": "var_types",
                "keys": {},
            },
            "description": "text",
            "required": "bool",
        }

        return self.add_option(name, "cmd", **kwargs)

    def has_cmd(self, cmd: str) -> bool:
        """
        Check if command exists

        :param cmd: command name
        :return: True if exists
        """
        key = "cmd." + cmd
        if key in self.options:
            if "value" in self.options[key] and "enabled" in self.options[key]["value"]:
                return self.options[key]["value"]["enabled"]
        return False

    def cmd_allowed(self, cmd: str) -> bool:
        """
        Check if command allowed

        :param cmd: command name
        :return: True if allowed
        """
        if cmd in self.allowed_cmds:
            return True
        return False

    def cmd_exe(self) -> bool:
        """
        Check if command enabled

        :return: True if enabled
        """
        return self.window.core.config.get("cmd")

    def get_cmd(self, cmd: str) -> dict:
        """
        Return command

        :param cmd: command name
        :return: command dict
        """
        key = "cmd." + cmd
        if key in self.options:
            data = copy.deepcopy(self.options[key]["value"]) # make copy to prevent changes in original data
            data = {"cmd": cmd, **data}
            return data

    def has_option(self, name: str) -> bool:
        """
        Check if option exists

        :param name: option name
        :return: True if exists
        """
        return name in self.options

    def get_option(self, name: str) -> dict:
        """
        Return option

        :param name: option name
        :return: option dict
        """
        if self.has_option(name):
            return self.options[name]

    def get_option_value(self, name: str) -> any:
        """
        Return option value

        :param name: option name
        :return: option value
        """
        if self.has_option(name):
            return self.options[name]["value"]

    def attach(self, window):
        """
        Attach window to plugin

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle event

        :param event: event name
        :param args: arguments
        :param kwargs: keyword arguments
        """
        return

    def on_update(self, *args, **kwargs):
        """
        Called on update

        :param args: arguments
        :param kwargs: keyword arguments
        """
        return

    def on_post_update(self, *args, **kwargs):
        """
        Called on post-update

        :param args: arguments
        :param kwargs: keyword arguments
        """
        return

    def trans(self, text: str = None) -> str:
        """
        Translate text using plugin domain

        :param text: text to translate
        :return: translated text
        """
        if text is None:
            return ""
        domain = 'plugin.{}'.format(self.id)
        return trans(text, False, domain)

    def error(self, err: any):
        """
        Send error message to logger and alert dialog

        :param err: error message
        """
        self.window.core.debug.log(err)
        msg = self.window.core.debug.parse_alert(err)
        self.window.ui.dialogs.alert("{}: {}".format(self.name, msg))

    def debug(self, data: any):
        """
        Send debug message to logger window

        :param data: data to send
        """
        self.window.core.debug.info(data)

    def reply(self, response: dict, ctx: CtxItem = None, extra_data: dict = None):
        """
        Send reply from plugin (command response)

        :param response: response
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        self.handle_finished(response, ctx, extra_data)

    def is_native_cmd(self) -> bool:
        """
        Check if native API command execution is enabled

        :return: True if native execution is enabled
        """
        return self.window.core.command.is_native_enabled()

    def is_log(self) -> bool:
        """
        Check if logging to console is enabled

        :return: True if log is enabled
        """
        if self.window.core.config.has("log.plugins") \
                and self.window.core.config.get("log.plugins"):
            return True
        return False

    def log(self, msg: str):
        """
        Log message to logger and console

        :param msg: message to log
        """
        self.debug(msg)
        if self.is_threaded():
            return
        self.window.ui.status(msg)
        if self.is_log():
            print(msg)

    @Slot(object, object, dict)
    def handle_finished(self, response: dict, ctx: CtxItem = None, extra_data: dict = None):
        """
        Handle finished response signal

        :param response: response
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        # handle post-finishing operations
        if isinstance(extra_data, dict):
            if (ctx is None or not ctx.agent_call) or not self.is_threaded():
                if "post_update" in extra_data and isinstance(extra_data["post_update"], list):
                    if "file_explorer" in extra_data["post_update"]:
                        # update file explorer view
                        self.window.controller.files.update_explorer()

        # dispatch response (reply)
        if ctx is not None:
            ctx.results.append(response)
            ctx.reply = True
            if "context" in response:
                if self.window.core.config.get("ctx.use_extra"):
                    ctx.extra_ctx = response["context"]
                    response["result"] = "OK"
                else:
                    del response["context"]

            self.window.core.dispatcher.reply(ctx)

    @Slot(object, object, dict)
    def handle_finished_more(self, responses: list, ctx: CtxItem = None, extra_data: dict = None):
        """
        Handle finished response signal

        :param responses: responses
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        # handle post-finishing operations
        if isinstance(extra_data, dict):
            if (ctx is None or not ctx.agent_call) or not self.is_threaded():
                if "post_update" in extra_data and isinstance(extra_data["post_update"], list):
                    if "file_explorer" in extra_data["post_update"]:
                        # update file explorer view
                        self.window.controller.files.update_explorer()

        # dispatch responses (reply)
        for response in responses:
            if ctx is not None:
                ctx.results.append(response)
                ctx.reply = True
                if "context" in response:
                    if self.window.core.config.get("ctx.use_extra"):
                        ctx.extra_ctx = response["context"]
                        response["result"] = "OK"
                    else:
                        del response["context"]


            self.window.core.dispatcher.reply(ctx)

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: status message
        """
        if self.is_threaded():
            return
        self.window.ui.status(str(data))

    @Slot(object)
    def handle_error(self, err: any):
        """
        Handle thread error signal

        :param err: error message
        """
        self.error(err)

    @Slot(object)
    def handle_debug(self, msg: any):
        """
        Handle debug message signal

        :param msg: debug message
        """
        self.debug(msg)

    @Slot(object)
    def handle_log(self, msg: str):
        """
        Handle log message signal

        :param msg: log message
        """
        if self.is_threaded():
            return
        self.log(msg)

    def is_threaded(self) -> bool:
        """
        Check if plugin is threaded

        :return: True if threaded
        """
        if self.window.core.config.get("mode") == "agent_llama":
            return True
        return False


class BaseSignals(QObject):
    finished = Signal(object, object, dict)  # response dict, ctx, extra_data
    finished_more = Signal(list, object, dict)  # responses list, ctx, extra_data
    debug = Signal(object)
    destroyed = Signal()
    error = Signal(object)
    log = Signal(object)
    started = Signal()
    status = Signal(object)
    stopped = Signal()


class BaseWorker(QObject, QRunnable):
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.signals = BaseSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
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

    def error(self, err: any):
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
    def response(self, response: dict, extra_data: dict = None):
        """
        Emit finished signal (deprecated)

        :param response: response (dict)
        :param extra_data: extra data
        """
        # show warning
        self.debug("BaseWorker.response is deprecated from 2.1.29, use BaseWorker.reply instead")
        self.reply(response, extra_data)

    def reply(self, response: dict, extra_data: dict = None):
        """
        Emit finished signal (on reply from command output)

        :param response: response (dict)
        :param extra_data: extra data
        """
        # if tool call from agent_llama mode, then send direct reply to plugin -> dispatcher -> reply
        if self.ctx.agent_call and self.plugin is not None:
            self.plugin.handle_finished(response, self.ctx, extra_data)
            return

        if self.signals is not None and hasattr(self.signals, "finished"):
            self.signals.finished.emit(response, self.ctx, extra_data)

    def reply_more(self, responses: list, extra_data: dict = None):
        """
        Emit finished_more signal (on reply from command output, multiple responses)

        :param responses: responses
        :param extra_data: extra data
        """
        # if tool call from agent_llama mode, then send direct reply to plugin -> dispatcher -> reply
        if self.ctx.agent_call and self.plugin is not None:
            self.plugin.handle_finished(responses, self.ctx, extra_data)
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
            