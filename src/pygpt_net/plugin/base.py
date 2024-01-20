#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.20 12:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class BasePlugin:
    def __init__(self, *args, **kwargs):
        self.window = kwargs.get('window', None)
        self.id = ""
        self.name = ""
        self.type = []  # Types:
        # audio.input, audio.output, image.input, image.output, schedule, text.input, text.output, vision
        self.description = ""
        self.urls = {}
        self.options = {}
        self.initial_options = {}
        self.parent = None
        self.enabled = False
        self.use_locale = False
        self.is_async = False
        self.order = 0

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def add_option(self, name: str, type: str, **kwargs):
        """
        Add plugin configuration option

        :param name: Option name (ID, key)
        :param type: Option type (text, textarea, bool, int, float, dict, combo)
        :param kwargs: Additional keyword arguments for option properties
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

    def has_option(self, name: str) -> bool:
        """
        Check if option exists

        :param name: option name
        :return: True if exists
        :rtype: bool
        """
        return name in self.options

    def get_option(self, name: str) -> dict:
        """
        Return option

        :param name: option name
        :return: option
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
        Send error message to logger

        :param err: error message
        """
        self.window.core.debug.log(err)
        self.window.controller.debug.log(str(err), True)
        self.window.ui.dialogs.alert("{}: {}".format(self.name, err))

    def debug(self, data: any):
        """
        Send debug message to logger window

        :param data: data to send
        """
        self.window.controller.debug.log(data, True)

    def log(self, msg: str):
        """
        Log message to logger and console

        :param msg: message to log
        """
        self.debug(msg)
        self.window.ui.status(msg)
        print(msg)

    @Slot(object, object)
    def handle_finished(self, response: dict, ctx: CtxItem = None):
        """
        Handle finished response signal

        :param response: response
        :param ctx: context (CtxItem)
        """
        # dispatcher handle late response
        if ctx is not None:
            ctx.results.append(response)
            ctx.reply = True
            self.window.core.dispatcher.reply(ctx)

    @Slot(object)
    def handle_status(self, data: str):
        """
        Handle thread status msg signal

        :param data: status message
        """
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
        self.log(msg)


class BaseSignals(QObject):
    finished = Signal(object, object)  # response, ctx
    debug = Signal(object)
    destroyed = Signal()
    error = Signal(object)
    log = Signal(object)
    started = Signal()
    status = Signal(object)
    stopped = Signal()


class BaseWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(BaseWorker, self).__init__()
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
        if self.signals is not None and hasattr(self.signals, "log"):
            self.signals.log.emit(msg)

    def response(self, response: dict):
        """
        Emit finished signal

        :param response: response
        """
        if self.signals is not None and hasattr(self.signals, "finished"):
            self.signals.finished.emit(response, self.ctx)

    def started(self):
        """Emit started signal"""
        if self.signals is not None and hasattr(self.signals, "started"):
            self.signals.started.emit()

    def status(self, msg: str):
        """
        Emit status signal

        :param msg: status message
        """
        if self.signals is not None and hasattr(self.signals, "status"):
            self.signals.status.emit(msg)

    def stopped(self):
        """Emit stopped signal"""
        if self.signals is not None and hasattr(self.signals, "stopped"):
            self.signals.stopped.emit()
            