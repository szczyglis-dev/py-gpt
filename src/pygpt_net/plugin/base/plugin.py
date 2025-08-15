#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

import copy
from typing import Optional, Any, Dict, List

from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtGui import QDesktopServices

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class BasePlugin(QObject):
    DEFAULT_OPTION = {
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
    _ALLOW_OUTPUT_KEYS = ("request", "result", "context")
    _IGNORE_EXTRA_KEYS = ("request", "context")

    def __init__(self, *args, **kwargs):
        super(BasePlugin, self).__init__()
        self.window = kwargs.get('window', None)
        self.id = ""
        self.name = ""
        self.type = []
        self.description = ""
        self.prefix = "Plugin"
        self.urls = {}
        self.options = {}
        self.initial_options = {}
        self.allowed_cmds = []
        self.tabs = {}
        self.parent = None
        self.enabled = False
        self.use_locale = False
        self.order = 0

    def setup(self) -> Dict[str, Any]:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def add_option(
            self,
            name: str,
            type: str,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Add plugin configuration option

        :param name: option name (ID, key)
        :param type: option type (text, textarea, bool, int, float, dict, combo)
        :param kwargs: additional keyword arguments for option properties
        :return: added option config dict
        """
        option = BasePlugin.DEFAULT_OPTION.copy()
        option.update(kwargs)
        option['tooltip'] = option['tooltip'] or option['description']
        option["id"] = name
        option["type"] = type
        self.options[name] = option
        return option

    def add_cmd(
            self,
            cmd: str,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Add plugin command

        :param cmd: command name
        :param kwargs: additional keyword arguments for command properties
        :return: added option config dict
        """
        cmd_syntax = {
            "instruction": "",
            "params": {},
            "enabled": True,
        }
        if "instruction" in kwargs and isinstance(kwargs.get("instruction"), str):
            cmd_syntax["instruction"] = kwargs.get("instruction")
            kwargs.pop("instruction")
        if "params" in kwargs and isinstance(kwargs.get("params"), (dict, list)):
            cmd_syntax["params"] = kwargs.get("params")
            kwargs.pop("params")
        if "enabled" in kwargs and isinstance(kwargs.get("enabled"), bool):
            cmd_syntax["enabled"] = kwargs.get("enabled")
            kwargs.pop("enabled")

        name = f"cmd.{cmd}"
        kwargs["cmd"] = cmd
        kwargs["value"] = cmd_syntax

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

    def has_cmd(
            self,
            cmd: str
    ) -> bool:
        """
        Check if command exists

        :param cmd: command name
        :return: True if exists
        """
        return bool(self.options.get(f"cmd.{cmd}", {}).get("value", {}).get("enabled", False))

    def cmd_allowed(
            self,
            cmd: str
    ) -> bool:
        """
        Check if command allowed

        :param cmd: command name
        :return: True if allowed
        """
        return cmd in self.allowed_cmds

    def cmd_exe(self) -> bool:
        """
        Check if command enabled

        :return: True if enabled
        """
        return self.window.core.config.get("cmd")

    def get_cmd(
            self,
            cmd: str
    ) -> Dict[str, Any]:
        """
        Return command

        :param cmd: command name
        :return: command dict
        """
        key = f"cmd.{cmd}"
        opt = self.options.get(key)
        if opt:
            data = copy.deepcopy(opt["value"])
            data = {"cmd": cmd, **data}
            return data
        return None

    def has_option(
            self,
            name: str
    ) -> bool:
        """
        Check if option exists

        :param name: option name
        :return: True if exists
        """
        return name in self.options

    def get_option(
            self,
            name: str
    ) -> Dict[str, Any]:
        """
        Return option

        :param name: option name
        :return: option dict
        """
        return self.options.get(name)

    def get_option_value(
            self,
            name: str
    ) -> Any:
        """
        Return option value

        :param name: option name
        :return: option value
        """
        opt = self.options.get(name)
        if not opt:
            return None
        value = opt["value"]
        t = opt["type"]
        if t == "bool":
            return bool(value)
        elif t == "int":
            return int(value)
        elif t == "float":
            return float(value)
        return value

    def set_option_value(
            self,
            name: str,
            value: Any
    ):
        """
        Set option value

        :param name: option name
        :param value: option value
        """
        opt = self.options.get(name)
        if not opt:
            return
        t = opt["type"]
        if t == "bool":
            value = bool(value)
        elif t == "int":
            value = int(value)
        elif t == "float":
            value = float(value)
        opt["value"] = value
        self.refresh_option(name)

    def attach(self, window):
        """
        Attach window to plugin

        :param window: Window instance
        """
        self.window = window

    def refresh_option(self, option_id: str):
        """
        Refresh plugin option

        :param option_id: option id
        """
        if option_id in self.options:
            self.window.controller.plugins.settings.refresh_option(self.id, option_id)

    def handle(
            self,
            event: Event,
            *args,
            **kwargs
    ):
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

    def trans(
            self,
            text: Optional[str] = None
    ) -> str:
        """
        Translate text using plugin domain

        :param text: text to translate
        :return: translated text
        """
        if text is None:
            return ""
        domain = f'plugin.{self.id}'
        return trans(text, False, domain)

    def error(self, err: Any):
        """
        Send error message to logger and alert dialog

        :param err: error message
        """
        self.window.core.debug.log(err)
        msg = self.window.core.debug.parse_alert(err)
        self.window.ui.dialogs.alert(f"{self.name}: {msg}")

    def debug(self, data: Any, console: bool = True):
        """
        Send debug message to logger window

        :param data: data to send
        :param console: print in console
        """
        self.window.core.debug.info(data, console)

    def reply(
            self,
            response: dict,
            ctx: Optional[CtxItem] = None,
            extra_data: Optional[dict] = None
    ):
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
        cfg = self.window.core.config
        return bool(cfg.has("log.plugins") and cfg.get("log.plugins"))

    def is_async(self, ctx: CtxItem) -> bool:
        """
        Check if async execution is allowed

        :param ctx: context (CtxItem)
        :return: True if async execution is allowed
        """
        if ctx.async_disabled:
            return False
        return self.window.controller.kernel.async_allowed(ctx)

    def log(self, msg: str):
        """
        Log message to logger and console

        :param msg: message to log
        """
        msg = f"[{self.prefix}] {msg}"
        log_enabled = self.is_log()
        self.debug(msg, not log_enabled)
        if self.is_threaded():
            return
        self.window.update_status(msg.replace("\n", " "))
        if log_enabled:
            print(msg)

    def cmd_prepare(self, ctx: CtxItem, cmds: list):
        """
        On command run

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "img",
        }))

    @Slot(object, object, dict)
    def handle_finished(
            self,
            response: Dict[str, Any],
            ctx: Optional[CtxItem] = None,
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Handle finished response signal

        :param response: response
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        if ctx is not None:
            self.prepare_reply_ctx(response, ctx)
            context = BridgeContext()
            context.ctx = ctx
            extra = extra_data if extra_data else {}
            extra["response_type"] = "single"
            event = KernelEvent(KernelEvent.REPLY_ADD, {
                'context': context,
                'extra': extra,
            })
            self.window.dispatch(event)

    @Slot(object, object, dict)
    def handle_finished_more(
            self,
            responses: List[Dict[str, Any]],
            ctx: Optional[CtxItem] = None,
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Handle finished response signal

        :param responses: responses
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        for response in responses:
            if ctx is not None:
                self.prepare_reply_ctx(response, ctx)

        context = BridgeContext()
        context.ctx = ctx
        extra = extra_data if extra_data else {}
        extra["response_type"] = "multiple"
        event = KernelEvent(KernelEvent.REPLY_ADD, {
            'context': context,
            'extra': extra,
        })
        self.window.dispatch(event)

    def prepare_reply_ctx(
            self,
            response: Dict[str, Any],
            ctx: Optional[CtxItem] = None
    ) -> Dict[str, Any]:
        """
        Prepare reply context

        :param response: response
        :param ctx: context (CtxItem)
        :return: response dict
        """
        clean_response = {k: v for k, v in response.items() if k in self._ALLOW_OUTPUT_KEYS or k.startswith("agent_")}
        ctx.results.append(clean_response)
        ctx.reply = True

        extras = {k: v for k, v in response.items() if k not in self._IGNORE_EXTRA_KEYS}

        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        if "tool_output" not in ctx.extra:
            ctx.extra["tool_output"] = []
        ctx.extra["tool_output"].append(extras)

        if "context" in response:
            cfg = self.window.core.config
            if cfg.get("ctx.use_extra"):
                if ctx.extra_ctx is None:
                    ctx.extra_ctx = ""
                if ctx.extra_ctx != "":
                    ctx.extra_ctx += "\n\n"
                ctx.extra_ctx += str(response["context"])
                response["result"] = "OK"
            else:
                del response["context"]

        return response

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: status message
        """
        if self.is_threaded():
            return
        self.window.update_status(str(data))

    @Slot(object)
    def handle_error(self, err: Any):
        """
        Handle thread error signal

        :param err: error message
        """
        self.error(err)

    @Slot(object)
    def handle_debug(self, msg: Any):
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
        return self.window.controller.kernel.is_threaded()

    def open_url(self, url: str):
        """
        Open URL in the default web browser

        :param url: URL to open
        """
        if url:
            QDesktopServices.openUrl(QUrl(url))