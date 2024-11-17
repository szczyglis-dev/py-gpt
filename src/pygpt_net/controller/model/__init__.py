#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.model import ModelItem
from pygpt_net.core.access.events import AppEvent
from .editor import Editor


class Model:
    def __init__(self, window=None):
        """
        Model controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)

    def select(self, model: str):
        """
        Select model

        :param model: model ID
        """
        # check if model change is not locked
        if self.change_locked():
            return

        mode = self.window.core.config.get('mode')
        self.window.core.config.set('model', model)
        if 'current_model' not in self.window.core.config.data:
            self.window.core.config.data['current_model'] = {}
        self.window.core.config.data['current_model'][mode] = model

        event = Event(Event.MODEL_SELECT, {
            'value': model,
        })
        self.window.core.dispatcher.dispatch(event)

        # update all layout
        self.window.controller.ui.update()
        self.window.core.dispatcher.dispatch(AppEvent(AppEvent.MODEL_SELECTED))  # app event

    def next(self):
        """Select next model"""
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        next = self.window.core.models.get_next(model, mode)
        self.select(next)

    def prev(self):
        """Select previous model"""
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        prev = self.window.core.models.get_prev(model, mode)
        self.select(prev)

    def set(self, mode: str, model: str):
        """
        Set model by mode and model name

        :param mode: mode name
        :param model: model name
        """
        self.window.core.config.set('model', model)
        if 'current_model' not in self.window.core.config.data:
            self.window.core.config.data['current_model'] = {}
        self.window.core.config.data['current_model'][mode] = model

    def set_by_idx(self, mode: str, idx: int):
        """
        Set model by mode and model idx

        :param mode: mode name
        :param idx: model index
        """
        model = self.window.core.models.get_by_idx(idx, mode)
        self.window.core.config.set('model', model)
        if 'current_model' not in self.window.core.config.data:
            self.window.core.config.data['current_model'] = {}
        self.window.core.config.data['current_model'][mode] = model

        event = Event(Event.MODEL_SELECT, {
            'value': model,
        })
        self.window.core.dispatcher.dispatch(event)

    def select_on_list(self, model):
        self.window.ui.nodes["prompt.model"].set_value(model)

    def select_current(self):
        """Select current model on list"""
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        items = self.window.core.models.get_by_mode(mode)
        if model in items:
            self.select_on_list(model)

    def select_default(self):
        """Set default model"""
        model = self.window.core.config.get('model')
        if model is None or model == "":
            mode = self.window.core.config.get('mode')

            # set previous selected model
            current_models = self.window.core.config.get('current_model')
            if mode in current_models and \
                    current_models[mode] is not None and \
                    current_models[mode] != "" and \
                    current_models[mode] in self.window.core.models.get_by_mode(mode):
                self.window.core.config.set('model', current_models[mode])
            else:
                # or set default model
                self.window.core.config.set('model', self.window.core.models.get_default(mode))

    def switch_inline(self, mode: str, model: ModelItem = None) -> ModelItem:
        """
        Switch inline model instance (force change model if needed)

        :param mode: mode (vision, chat, etc.)
        :param model: model instance
        :return: model instance
        """
        event = Event(Event.MODEL_BEFORE, {
            'mode': mode,
            'model': model,  # model instance
        })
        self.window.core.dispatcher.dispatch(event)
        tmp_model = event.data['model']
        if tmp_model is not None:
            model = tmp_model
        return model

    def init_list(self):
        """Init models list"""
        mode = self.window.core.config.get('mode')
        items = {}
        data = self.window.core.models.get_by_mode(mode)
        for k in data:
            items[k] = data[k].name
        self.window.ui.nodes["prompt.model"].set_keys(items)

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
