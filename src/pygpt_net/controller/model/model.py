#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

from typing import Optional

from pygpt_net.core.events import Event, AppEvent
from pygpt_net.item.model import ModelItem

from .editor import Editor
from .importer import Importer


class Model:
    def __init__(self, window=None):
        """
        Model controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)
        self.importer = Importer(window)

    def _ensure_current_model_map(self):
        return self.window.core.config.data.setdefault('current_model', {})

    def select(self, model: str):
        """
        Select model

        :param model: model ID
        """
        if self.change_locked():
            return

        w = self.window
        cfg = w.core.config
        mode = cfg.get('mode')
        cfg.set('model', model)
        self._ensure_current_model_map()[mode] = model

        w.dispatch(Event(Event.MODEL_SELECT, {'value': model}))
        w.controller.ui.update()
        w.dispatch(AppEvent(AppEvent.MODEL_SELECTED))

        preset = cfg.get('preset')
        if preset and preset != "*":
            preset_data = w.core.presets.get_by_id(mode, preset)
            if preset_data:
                preset_data.model = model
                w.core.presets.save(preset)

        ctx = w.core.ctx
        ctx.model = model
        ctx.last_model = model
        ctx.update_model_in_current(model)

    def next(self):
        """Select next model"""
        w = self.window
        mode = w.core.config.get('mode')
        model = w.core.config.get('model')
        next_model = w.core.models.get_next(model, mode)
        self.select(next_model)

    def prev(self):
        """Select previous model"""
        w = self.window
        mode = w.core.config.get('mode')
        model = w.core.config.get('model')
        prev_model = w.core.models.get_prev(model, mode)
        self.select(prev_model)

    def set(self, mode: str, model: str):
        """
        Set model by mode and model name

        :param mode: mode name
        :param model: model name
        """
        w = self.window
        w.core.config.set('model', model)
        self._ensure_current_model_map()[mode] = model

    def set_by_idx(self, mode: str, idx: int):
        """
        Set model by mode and model idx

        :param mode: mode name
        :param idx: model index
        """
        w = self.window
        model = w.core.models.get_by_idx(idx, mode)
        w.core.config.set('model', model)
        self._ensure_current_model_map()[mode] = model
        w.dispatch(Event(Event.MODEL_SELECT, {'value': model}))

    def select_on_list(self, model: str):
        """
        Select model on list

        :param model: model ID
        """
        self.window.ui.nodes["prompt.model"].set_value(model)

    def select_current(self):
        """Select current model on list"""
        w = self.window
        mode = w.core.config.get('mode')
        model = w.core.config.get('model')
        items = w.core.models.get_by_mode(mode)
        if model in items:
            self.select_on_list(model)

    def select_default(self):
        """Set default model"""
        w = self.window
        model = w.core.config.get('model')
        if model is None or model == "":
            mode = w.core.config.get('mode')
            current_models = w.core.config.get('current_model') or {}
            mode_items = w.core.models.get_by_mode(mode)
            if (
                mode in current_models
                and current_models[mode]
                and current_models[mode] in mode_items
            ):
                w.core.config.set('model', current_models[mode])
            else:
                w.core.config.set('model', w.core.models.get_default(mode))

    def switch_inline(
            self,
            mode: str,
            model: Optional[ModelItem] = None
    ) -> ModelItem:
        """
        Switch inline model instance (force change model if needed)

        :param mode: mode (vision, chat, etc.)
        :param model: model instance
        :return: model instance
        """
        event = Event(Event.MODEL_BEFORE, {
            'mode': mode,
            'model': model,
        })
        self.window.dispatch(event)
        tmp_model = event.data['model']
        if tmp_model is not None:
            model = tmp_model
        return model

    def init_list(self):
        """Init models list"""
        w = self.window
        mode = w.core.config.get('mode')
        data = w.core.models.get_by_mode(mode)

        items_by_provider = {}
        for k, item in data.items():
            p = item.provider
            d = items_by_provider.get(p)
            if d is None:
                d = {}
                items_by_provider[p] = d
            d[k] = item.name

        providers = w.core.llm.get_choices()
        sorted_items = {}
        for provider, label in providers.items():
            provider_items = items_by_provider.get(provider)
            if provider_items:
                sorted_items[f"separator::{provider}"] = label
                sorted_items.update(provider_items)

        w.ui.nodes["prompt.model"].set_keys(sorted_items)

    def reload(self):
        """Reload models"""
        self.init_list()
        self.update()

    def update(self):
        """Update models"""
        self.select_default()
        self.select_current()

    def change_locked(self) -> bool:
        """
        Check if model change is locked

        :return: True if locked
        """
        return self.window.controller.chat.input.generating