#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

import json

from PySide6.QtWidgets import QApplication

from pygpt_net.item.ctx import CtxItem


class BaseEvent:
    def __init__(
            self,
            name: str = None,
            data: dict = None,
            ctx: CtxItem = None
    ):
        """
        Base Event object class

        :param name: event name
        :param data: event data
        :param ctx: context instance
        """
        self.name = name
        self.data = data
        self.ctx = ctx  # CtxItem
        self.stop = False  # True to stop propagation
        self.internal = False


class Event(BaseEvent):

    # Events
    AI_NAME = "ai.name"
    AUDIO_INPUT_RECORD_START = "audio.input.record.start"  # start audio input recording
    AUDIO_INPUT_RECORD_STOP = "audio.input.record.stop"  # stop audio input recording
    AUDIO_INPUT_RECORD_TOGGLE = "audio.input.record.toggle"  # toggle audio input recording
    AUDIO_INPUT_TRANSCRIBE = "audio.input.transcribe"  # transcribe audio file
    AUDIO_INPUT_STOP = "audio.input.stop"
    AUDIO_INPUT_TOGGLE = "audio.input.toggle"
    AUDIO_OUTPUT_STOP = "audio.output.stop"
    AUDIO_OUTPUT_TOGGLE = "audio.output.toggle"
    AUDIO_READ_TEXT = "audio.read_text"
    CMD_EXECUTE = "cmd.execute"
    CMD_INLINE = "cmd.inline"
    CMD_SYNTAX = "cmd.syntax"
    CMD_SYNTAX_INLINE = "cmd.syntax.inline"
    CTX_AFTER = "ctx.after"
    CTX_BEFORE = "ctx.before"
    CTX_BEGIN = "ctx.begin"
    CTX_END = "ctx.end"
    CTX_SELECT = "ctx.select"
    DISABLE = "disable"
    ENABLE = "enable"
    FORCE_STOP = "force.stop"
    INPUT_BEFORE = "input.before"
    MODE_BEFORE = "mode.before"
    MODE_SELECT = "mode.select"
    MODEL_BEFORE = "model.before"
    MODEL_SELECT = "model.select"
    PLUGIN_SETTINGS_CHANGED = "plugin.settings.changed"
    PLUGIN_OPTION_GET = "plugin.option.get"
    POST_PROMPT = "post.prompt"
    PRE_PROMPT = "pre.prompt"
    SYSTEM_PROMPT = "system.prompt"
    UI_ATTACHMENTS = "ui.attachments"
    UI_VISION = "ui.vision"
    USER_NAME = "user.name"
    USER_SEND = "user.send"

    def __init__(
            self,
            name: str = None,
            data: dict = None,
            ctx: CtxItem = None
    ):
        """
        Event object class

        :param name: event name
        :param data: event data
        :param ctx: context instance
        """
        super(Event, self).__init__(name, data, ctx)
        self.name = name
        self.data = data
        self.ctx = ctx  # CtxItem
        self.stop = False  # True to stop propagation
        self.internal = False
        # internal event, not called from user
        # internal event is handled synchronously, ctx item has internal flag

    def to_dict(self) -> dict:
        """Dump event to dict"""
        return {
            'name': self.name,
            'data': self.data,
            'ctx': self.ctx.to_dict() if self.ctx else None,
            'stop': self.stop,
            'internal': self.internal,
        }

    def dump(self) -> str:
        """
        Dump event to json string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        return self.dump()


class Dispatcher:
    def __init__(self, window=None):
        """
        Event dispatcher

        :param window: Window instance
        """
        self.window = window
        self.nolog_events = ["system.prompt"]
        self.reply_stack = []
        self.reply_ctx = None

    def is_log(self, event: BaseEvent) -> bool:
        """
        Check if event can be logged

        :param event: event object
        :return: true if can be logged
        """
        if event.name in self.nolog_events:
            return False
        if not self.is_log_display():
            return False
        data = event.data
        if data is not None and "silent" in data and data["silent"]:
            return False
        return True

    def is_log_display(self) -> bool:
        """
        Check if event can be logged

        :return: true if can be logged
        """
        is_log = False
        if self.window.core.config.has("log.events") \
                and self.window.core.config.get("log.events"):
            is_log = True
        return is_log

    def async_allowed(self, ctx: CtxItem) -> bool:
        """
        Check if async execution are allowed

        :param ctx: context item
        :return: True if async commands are allowed
        """
        disallowed_modes = ["assistant", "agent", "expert"]
        if ctx.internal:
            return False
        if self.window.core.config.get("mode") in disallowed_modes:
            return False
        if self.window.controller.agent.enabled() or self.window.controller.agent.experts.enabled():
            return False
        if len(ctx.cmds) > 1:  # if multiple commands then run synchronously
            return False
        return True

    def dispatch(
            self,
            event: BaseEvent,
            all: bool = False
    ) -> (list, BaseEvent):
        """
        Dispatch event to plugins

        :param event: event to dispatch
        :param all: true if dispatch to all plugins (enabled or not)
        :return: list of affected plugins ids and event object
        """
        if self.is_log(event):
            self.window.core.debug.info("Dispatch event begin: " + event.name)
            if self.window.core.debug.enabled():
                self.window.core.debug.debug("EVENT BEFORE: " + str(event))

        # dispatch event to accessibility controller
        self.window.controller.access.handle(event)

        # dispatch event to plugins
        affected = []
        for id in self.window.core.plugins.plugins:
            if self.window.controller.plugins.is_enabled(id) or all:
                if event.stop:
                    break
                if self.window.core.debug.enabled() and self.is_log(event):
                    self.window.core.debug.debug("Apply [{}] to plugin: ".format(event.name) + id)
                self.apply(id, event)
                affected.append(id)

        if self.is_log(event):
            self.window.core.debug.info("Dispatch event end: " + event.name)
            if self.window.core.debug.enabled():
                self.window.core.debug.debug("EVENT AFTER: " + str(event))

        return affected, event

    def apply(
            self,
            id: str,
            event: BaseEvent
    ):
        """
        Handle event in plugin with provided id

        :param id: plugin id
        :param event: event object
        """
        if id in self.window.core.plugins.plugins:
            try:
                self.window.core.plugins.plugins[id].handle(event)
            except AttributeError:
                pass

    def reply(self, ctx: CtxItem, flush: bool = False):
        """
        Send reply from plugins to model

        :param ctx: context object
        :param flush: True to flush reply stack
        """
        if ctx is not None:
            self.window.core.debug.info("Reply...")
            if self.window.core.debug.enabled() and self.is_log_display():
                self.window.core.debug.debug("CTX REPLY: " + str(ctx))
            if ctx.reply:
                self.add_reply(ctx)
            if flush or self.window.core.dispatcher.async_allowed(ctx):
                self.flush_reply_stack()

    def add_reply(self, ctx: CtxItem):
        """
        Add reply to stack

        :param ctx: context object
        """
        self.window.core.debug.info("Reply stack (add)...")
        self.reply_stack.append(ctx.results)
        ctx.results = []  # clear results
        self.reply_ctx = ctx

    def flush_reply_stack(self):
        """Flush reply stack"""
        if self.reply_ctx is None or len(self.reply_stack) == 0:
            return
        self.window.core.debug.info("Reply stack (flush)...")
        results = []
        for responses in self.reply_stack:
            for result in responses:
                results.append(result)

        self.window.ui.status("")  # clear status
        if self.reply_ctx.internal:
            if self.window.controller.agent.enabled():
                self.window.controller.agent.add_run()
                self.window.controller.agent.update()
                QApplication.processEvents()

        # prepare data to send as reply
        data = json.dumps(results)
        if len(self.reply_stack) < 2 and self.reply_ctx.extra_ctx and self.window.core.config.get("ctx.use_extra"):
            data = self.reply_ctx.extra_ctx  # if extra content is set, use it as data to send

        prev_ctx = self.window.core.ctx.as_previous(self.reply_ctx)  # copy result to previous ctx and clear current ctx
        self.window.core.ctx.update_item(self.reply_ctx)  # update context in db
        self.window.ui.status('...')

        parent_id = None
        if self.reply_ctx.sub_call:
            parent_id = self.reply_ctx.meta_id  # slave meta id
        self.window.controller.chat.input.send(
            text=data,
            force=True,
            reply=True,
            internal=self.reply_ctx.internal,
            prev_ctx=prev_ctx,
            parent_id=parent_id,
        )
        self.clear_reply_stack()

    def clear_reply_stack(self):
        """Clear reply stack"""
        self.window.core.debug.info("Reply stack (clear)...")
        self.reply_ctx = None
        self.reply_stack = []
