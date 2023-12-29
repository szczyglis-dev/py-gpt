#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 03:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, QRunnable

from pygpt_net.utils import trans


class BasePlugin:
    def __init__(self):
        self.id = ""
        self.name = ""
        self.type = []  # audio.input, audio.output
        self.description = ""
        self.urls = {}
        self.options = {}
        self.initial_options = {}
        self.window = None
        self.parent = None
        self.enabled = False
        self.use_locale = False
        self.is_async = False
        self.order = 0

    def setup(self):
        """
        Return available config options

        :return: config options
        :rtype: dict
        """
        return self.options

    def add_option(self,
                   name,  # option name (ID, key)
                   type,  # option type (text, textarea, bool, int, float, dict)
                   value=None,  # option value
                   label="",  # option label
                   description="",  # option description
                   tooltip=None,  # option tooltip
                   min=None,  # option min value
                   max=None,  # option max value
                   multiplier=1,  # option float value multiplier (for sliders)
                   step=1,  # option step value (for sliders)
                   slider=False,  # option slider (True/False)
                   keys=None,  # option keys (for dict type)
                   advanced=False,  # option is advanced (True/False)
                   secret=False,  # option is secret (True/False)
                   persist=False,  # option is persistent on reset to defaults (True/False)
                   urls=None):  # option URLs (API keys, docs, etc.)
        """
        Add plugin configuration option

        :param name: Option name (ID, key)
        :param type: Option type (text, textarea, bool, int, float, dict)
        :param value: Option value
        :param label: Option label
        :param description: Option description
        :param tooltip: Option tooltip
        :param min: Option min value
        :param max: Option max value
        :param multiplier: Option float value multiplier
        :param step: Option step value (for slider)
        :param slider: Option slider (True/False)
        :param keys: Option keys (for dict type)
        :param advanced: Option advanced (True/False)
        :param secret: Option secret (True/False)
        :param persist: Option persist (True/False)
        :param urls: Option URLs
        """
        if tooltip is None:
            tooltip = description

        option = {
            "type": type,
            "value": value,
            "label": label,
            "description": description,
            "tooltip": tooltip,
            "min": min,
            "max": max,
            "multiplier": multiplier,
            "step": step,
            "slider": slider,
            "keys": keys,
            "advanced": advanced,
            "secret": secret,
            "persist": persist,
            "urls": urls,
        }
        self.options[name] = option

    def has_option(self, name):
        """
        Check if option exists

        :param name: option name
        :return: true if exists
        :rtype: bool
        """
        return name in self.options

    def get_option(self, name):
        """
        Return option

        :param name: option name
        :return: option
        :rtype: dict
        """
        if self.has_option(name):
            return self.options[name]

    def get_option_value(self, name):
        """
        Return option value

        :param name: option name
        :return: option value
        :rtype: any
        """
        if self.has_option(name):
            return self.options[name]["value"]

    def attach(self, window):
        """
        Attach window to plugin

        :param window: Window instance
        """
        self.window = window

    def handle(self, event, *args, **kwargs):
        """
        Handle event

        :param event: event name
        :param args: arguments
        :param kwargs: keyword arguments
        """
        return

    def trans(self, text=None):
        """
        Translate text using plugin domain
        
        :param text: text to translate
        :return: translated text
        :rtype: str
        """
        if text is None:
            return ""
        domain = 'plugin.{}'.format(self.id)
        return trans(text, False, domain)

    def debug(self, data):
        """
        Send thread-safe debug message to logger window

        :param data: data to send
        """
        self.window.controller.debug.log(data, True)


class BaseSignals(QObject):
    finished = Signal(object, object)  # ctx, response
    log = Signal(object)
    debug = Signal(object)
    status = Signal(object)
    error = Signal(object)
    destroyed = Signal()
    started = Signal()
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

    def response(self, response):
        self.signals.finished.emit(self.ctx, response)

    def error(self, err):
        self.signals.error.emit(err)

    def status(self, msg):
        self.signals.status.emit(msg)

    def debug(self, msg):
        self.signals.debug.emit(msg)

    def log(self, msg):
        self.signals.log.emit(msg)

    def started(self):
        self.signals.started.emit()

    def stopped(self):
        self.signals.stopped.emit()

    def destroyed(self):
        self.signals.destroyed.emit()
