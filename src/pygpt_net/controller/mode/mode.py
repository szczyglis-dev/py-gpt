#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 07:00:00                  #
# ================================================== #

from pygpt_net.core.events import Event, AppEvent
from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_CHAT, MODE_AUDIO,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Mode:
    def __init__(self, window=None):
        """
        Mode controller

        :param window: Window instance
        """
        self.window = window
        self.locked = False

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        """
        Normalize mode name (handle deprecated modes)

        :param mode: mode name
        :return: normalized mode name
        """
        if mode == "langchain":
            print("Langchain mode is deprecated from v2.5.20 and no longer supported. "
                  "Please use LlamaIndex or Chat mode instead.")
            return MODE_CHAT
        elif mode == "vision":
            print("Vision mode is deprecated from v2.6.30 and no longer supported. "
                  "Please use Chat mode with multimodal models instead.")
            return MODE_CHAT
        return mode

    def select(self, mode: str):
        """
        Select mode by id

        :param mode: mode to select
        """
        mode = self._normalize_mode(mode)
        if self.change_locked() or mode is None:
            return  # abort if mode is locked

        self.set(mode)
        event = Event(Event.MODE_SELECT, {
            'value': mode,
        })
        w = self.window
        w.dispatch(event)
        c = w.controller
        c.attachment.update()
        c.chat.attachment.update()
        c.chat.audio.update()
        w.dispatch(AppEvent(AppEvent.MODE_SELECTED))  # app event

    def set(self, mode: str):
        """
        Set mode

        :param mode: mode name
        """
        mode = self._normalize_mode(mode)

        self.locked = True
        w = self.window
        c = w.controller
        core = w.core
        cfg = core.config
        try:
            if mode == MODE_ASSISTANT:
                c.presets.select_default()
                core_ctx = core.ctx
                current = core_ctx.get_current()
                assistant_id = core_ctx.get_assistant()
                if current is not None and assistant_id is not None:
                    c.assistant.select_by_id(assistant_id)
                else:
                    c.assistant.select_current()

            elif mode == MODE_AUDIO:
                c.audio.set_muted(False) # un-mute and show audio output icon by default

            cfg.set('mode', mode)

            # reset model and preset at start
            cfg.set('model', "")
            cfg.set('preset', "")

            # update
            c.attachment.update()
            c.ctx.update_ctx()

            # update toolbox, mode, presets, model, assistant and rest of the UI
            c.ui.update()

            # update model list
            c.model.init_list()
            c.model.select_current()

            # set status: ready
            if not c.reloading:
                w.update_status(trans('status.started'))

            # if assistant mode then update ctx label
            if mode == "assistant":
                c.ctx.common.update_label_by_current()
        finally:
            self.locked = False

    def select_on_list(self, mode: str):
        """
        Select mode on the list

        :param mode: mode name
        """
        mode = self._normalize_mode(mode)
        self.window.ui.nodes["prompt.mode"].set_value(mode)

    def init_list(self):
        """Init modes list"""
        data = self.window.core.modes.get_all()
        items = {k: trans(v.label) for k, v in data.items()}
        self.window.ui.nodes["prompt.mode"].set_keys(items)

    def select_current(self):
        """Select current mode on the list"""
        mode = self.window.core.config.get('mode')
        if mode:
            self.select_on_list(mode)

    def select_default(self):
        """Set default mode"""
        cfg = self.window.core.config
        mode = cfg.get('mode')
        if mode is None or mode == "":
            cfg.set('mode', self.window.core.modes.get_default())

    def default_all(self):
        """Set default mode, model and preset"""
        c = self.window.controller
        self.select_default()
        c.model.select_default()
        c.presets.select_default()
        c.assistant.select_default()

    def update_temperature(self, temperature: float = None):
        """
        Update current temperature field

        :param temperature: current temperature
        :type temperature: float or None
        """
        if temperature is None:
            cfg = self.window.core.config
            preset_id = cfg.get('preset')
            if preset_id is None or preset_id == "":
                temperature = 1.0  # default temperature
            else:
                items = self.window.core.presets.items
                if preset_id in items:
                    temperature = float(items[preset_id].temperature or 1.0)
        '''
        self.window.controller.config.slider.on_update("global", "current_temperature", option, temperature,
                                                       hooks=False)  # disable hooks to prevent circular update
        '''

    def hook_global_temperature(
            self,
            key: str,
            value,
            caller,
            *args,
            **kwargs
    ):
        """Hook: on update current temperature global field"""
        if caller != "slider":
            return  # accept call only from slider (has already validated min/max)

        temperature = value / 100
        cfg = self.window.core.config
        cfg.set("temperature", temperature)
        preset_id = cfg.get('preset')
        if preset_id is not None and preset_id != "":
            items = self.window.core.presets.items
            if preset_id in items:
                preset = items[preset_id]
                preset.temperature = temperature
                self.window.core.presets.save(preset_id)

    def switch_inline(
            self,
            mode: str,
            ctx: CtxItem,
            prompt: str
    ) -> str:
        """
        Switch inline mode

        :param mode: current mode
        :param ctx: ctx item
        :param prompt: prompt text
        :return: changed mode
        """
        event = Event(Event.MODE_BEFORE, {
            'value': mode,
            'prompt': prompt,
        })
        event.ctx = ctx
        self.window.dispatch(event)
        return event.data['value']

    def update_mode(self):
        """Update mode"""
        self.select_default()  # set default mode
        self.select_current()  # select current mode on the list

    def reset_current(self):
        """Reset current setup"""
        cfg = self.window.core.config
        cfg.set('prompt', None)
        cfg.set('ai_name', None)
        cfg.set('user_name', None)

    def next(self):
        """Select next mode"""
        mode = self.window.core.config.get('mode')
        nxt = self.window.core.modes.get_next(mode)
        self.select(nxt)

    def prev(self):
        """Select previous mode"""
        mode = self.window.core.config.get('mode')
        prv = self.window.core.modes.get_prev(mode)
        self.select(prv)

    def change_locked(self) -> bool:
        """
        Check if mode change is locked

        :return: True if locked
        """
        return bool(self.window.controller.chat.input.generating)