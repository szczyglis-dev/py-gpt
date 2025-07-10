#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 23:00:00                  #
# ================================================== #

import copy
from typing import Optional, Any, Dict, List

from PySide6.QtCore import QObject, Slot

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent
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

    def has_cmd(
            self,
            cmd: str
    ) -> bool:
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

    def cmd_allowed(
            self,
            cmd: str
    ) -> bool:
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

    def get_cmd(
            self,
            cmd: str
    ) -> Dict[str, Any]:
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
        if self.has_option(name):
            return self.options[name]

    def get_option_value(
            self,
            name: str
    ) -> Any:
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
        domain = 'plugin.{}'.format(self.id)
        return trans(text, False, domain)

    def error(self, err: Any):
        """
        Send error message to logger and alert dialog

        :param err: error message
        """
        self.window.core.debug.log(err)
        msg = self.window.core.debug.parse_alert(err)
        self.window.ui.dialogs.alert("{}: {}".format(self.name, msg))

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
        if self.window.core.config.has("log.plugins") \
                and self.window.core.config.get("log.plugins"):
            return True
        return False

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
        msg = "[{}] {}".format(self.prefix, msg)
        self.debug(msg, not self.is_log())
        if self.is_threaded():
            return
        self.window.update_status(msg.replace("\n", " "))
        if self.is_log():
            print(msg)

    def cmd_prepare(self, ctx: CtxItem, cmds: list):
        """
        On command run

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        # set state: busy
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
        # send response (reply)
        if ctx is not None:
            self.prepare_reply_ctx(response, ctx)
            
            context = BridgeContext()
            context.ctx = ctx
            extra = {}
            if extra_data:
                extra = extra_data
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
        # send multiple responses (reply)
        for response in responses:
            if ctx is not None:
                self.prepare_reply_ctx(response, ctx)

        context = BridgeContext()
        context.ctx = ctx
        extra = {}
        if extra_data:
            extra = extra_data
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
        ignore_extra = ["request", "context"]
        allow_output = ["request", "result", "context"]
        clean_response = {}
        for key in response:
            if key in allow_output or key.startswith("agent_"):
                clean_response[key] = response[key]

        ctx.results.append(clean_response)
        ctx.reply = True

        extras = {}
        for key in response:
            if key not in ignore_extra:
                extras[key] = response[key]

        # add extra data to context, into `tool_output` list
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        if "tool_output" not in ctx.extra:
            ctx.extra["tool_output"] = []
        ctx.extra["tool_output"].append(extras)  # allow more extra data

        if "context" in response:
            if self.window.core.config.get("ctx.use_extra"):
                if ctx.extra_ctx is None:
                    ctx.extra_ctx = ""
                if ctx.extra_ctx != "":
                    ctx.extra_ctx += "\n\n"
                ctx.extra_ctx += response["context"]  # allow more context data
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