#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

import copy
import os
from typing import List, Dict, Optional

from pygpt_net.core.events import Event
from pygpt_net.utils import trans


class Importer:
    def __init__(self, window=None):
        """
        Models importer controller

        :param window: Window instance
        """
        self.window = window
        self.dialog = False
        self.initialized = False
        self.width = 800
        self.height = 500
        self.items_available = {}  # available models for import
        self.items_current = {}  # current models in use
        self.pending = {}  # waiting to be imported models
        self.removed = {}  # waiting to be removed models
        self.selected_available = None  # selected available model
        self.selected_current = None  # selected current model
        self.all = False  # show all models, not only available for import

    def in_current(self, model: str) -> bool:
        """
        Check if model is in current list

        :param model: model ID
        :return: True if model is in current list, False otherwise
        """
        if model in self.items_current:
            return True
        for key in list(self.items_current.keys()):
            m = self.items_current[key]
            if m.id == model:  # also check in IDs
                return True
        return False

    def change_available(self):
        """On change available model selection"""
        val = self.window.ui.nodes["models.importer.available"].selectionModel().currentIndex()
        idx = val.row()
        if idx < 0:
            self.selected_available = None
            self.window.ui.nodes["models.importer.add"].setEnabled(False)
        else:
            self.selected_available = self.get_by_idx(idx, self.items_available)
            if self.items_available.get(self.selected_available) is None:
                self.selected_available = None
                self.window.ui.nodes["models.importer.add"].setEnabled(False)
            else:
                # if not in current then enable add button
                if not self.in_current(self.selected_available):
                    self.window.ui.nodes["models.importer.add"].setEnabled(True)
                else:
                    self.window.ui.nodes["models.importer.add"].setEnabled(False)

    def change_current(self):
        """On change current model selection"""
        val = self.window.ui.nodes["models.importer.current"].selectionModel().currentIndex()
        idx = val.row()
        if idx < 0:
            self.selected_current = None
            self.window.ui.nodes["models.importer.remove"].setEnabled(False)
        else:
            self.selected_current = self.get_by_idx(idx, self.items_current)
            if self.items_current.get(self.selected_current) is None:
                self.selected_current = None
                self.window.ui.nodes["models.importer.remove"].setEnabled(False)
            else:
                if self.selected_current in self.items_current and self.items_current[self.selected_current].imported:
                    self.window.ui.nodes["models.importer.remove"].setEnabled(True)
                else:
                    self.window.ui.nodes["models.importer.remove"].setEnabled(False)

    def add(self):
        """Add model to current list"""
        if self.selected_available is None:
            self.set_status(trans('models.importer.error.add.no_model'))
            return
        if self.in_current(self.selected_available):
            self.set_status(trans('models.importer.error.add.not_exists'))
            return
        model = self.items_available[self.selected_available]
        self.items_current[self.selected_available] = model
        if self.selected_available not in self.pending:
            self.pending[self.selected_available] = model
        if self.selected_available in self.removed:
            del self.removed[self.selected_available]
        if not self.all:
            del self.items_available[self.selected_available]
        self.refresh()

    def remove(self):
        """Remove model from current list"""
        if self.selected_current is None:
            self.set_status(trans('models.importer.error.remove.no_model'))
            return
        if not self.in_current(self.selected_current):
            self.set_status(trans('models.importer.error.remove.not_exists'))
            return
        model = self.items_current[self.selected_current]
        self.items_available[self.selected_current] = model
        if self.selected_current not in self.removed:
            self.removed[self.selected_current] = model
        del self.items_current[self.selected_current]
        if self.selected_current in self.pending:
            del self.pending[self.selected_current]
        self.refresh()

    def setup(self):
        """Set up importer"""
        idx = None
        self.window.model_importer.setup(idx)  # widget dialog setup

    def toggle_editor(self):
        """Toggle models importer dialog"""
        if self.dialog:
            self.close()
        else:
            self.open()

    def open(self, force: bool = False):
        """
        Open models editor dialog

        :param force: force open dialog
        """
        if not self.initialized:
            self.setup()
            self.initialized = True
        if not self.dialog or force:
            self.pending = {}
            self.removed = {}
            self.init()
            self.window.ui.dialogs.open(
                "models.importer",
                width=self.width,
                height=self.height,
            )
            self.dialog = True

    def close(self):
        """Close models importer dialog"""
        if self.dialog:
            self.window.ui.dialogs.close('models.importer')
            self.dialog = False

    def cancel(self):
        """Cancel models importer dialog"""
        self.close()

    def init(self):
        """Initialize importer"""
        if self.initialized and self.window.ui.nodes["models.importer.available.all"].isChecked():
            self.all = True

        base_url = "http://localhost:11434"
        if 'OLLAMA_API_BASE' in os.environ:
            base_url = os.environ['OLLAMA_API_BASE']
        self.window.ui.nodes["models.importer.url"].setText(base_url)
        self.items_available = self.get_ollama_available()
        self.items_current = self.get_ollama_current()
        self.refresh()

    def toggle_all(self, all: bool):
        """
        Toggle all models visibility

        :param all: show all models, not only available for import
        """
        self.all = all
        self.refresh(reload=True)

    def set_status(self, status: str):
        """
        Set status message

        :param status: status message
        """
        if self.initialized:
            self.window.ui.nodes["models.importer.status"].setText(status)

    def get_ollama_current(self) -> Dict:
        """
        Get current ollama models

        :return: PyGPT ollama models dictionary
        """
        items = copy.deepcopy(self.window.core.models.items)
        for key in list(items.keys()):
            if (items[key].llama_index is None
                    or items[key].provider != 'ollama'):
                del items[key]
        return items

    def get_ollama_available(self) -> Dict:
        """
        Get available ollama models

        :return: Ollama API models dictionary
        """
        models = {}
        status = self.window.core.models.ollama.get_status()
        if not status['status']:
            self.set_status(trans('models.importer.error.no_connection'))
            return models
        else:
            ollama_models = status.get('models', [])
            if not ollama_models:
                self.set_status(trans('models.importer.error.no_models'))
                return models
            else:
                for model in ollama_models:
                    name = model.get('name').replace(":latest", "")
                    m = self.window.core.models.create_empty(append=False)
                    m.id = name
                    m.name = name
                    m.mode = [
                        "chat",
                        "llama_index",
                        "agent",
                        "agent_llama",
                        "expert",
                    ]
                    m.provider = 'ollama'
                    m.input = ["text"]
                    m.output = ["text"]
                    # m.llama_index['provider'] = 'ollama'
                    # m.llama_index['mode'] = ['chat']
                    m.llama_index['args'] = [
                        {
                            'name': 'model',
                            'value': name,
                            'type': 'str'
                        }
                    ]
                    """
                    m.langchain['provider'] = 'ollama'
                    m.langchain['mode'] = ['chat']
                    m.langchain['args'] = [
                        {
                            'name': 'model',
                            'value': name,
                            'type': 'str'
                        }
                    ]
                    """
                    m.imported = True
                    m.ctx = 32000  # default
                    key = m.id
                    # if key in self.items_current:
                        # key += "_imported"
                    models[key] = m
                self.set_status(trans('models.importer.loaded'))
        return models

    def from_pending(self):
        """Move pending models to base list"""
        added = False
        base_models = self.window.core.models.items
        for key in list(self.pending.keys()):
            if key not in base_models:
                base_models[key] = copy.deepcopy(self.pending[key])
                base_models[key].imported = True
                added = True
        for key in list(self.removed.keys()):
            if key in base_models:
                del base_models[key]
                added = True
        self.pending = {}
        self.removed = {}
        if added:
            self.window.core.models.save()
            self.set_status(trans('models.importer.status.imported'))

    def save(self, persist: bool = True):
        """
        Save models

        :param persist: persist to file and close dialog
        """
        self.from_pending()
        self.window.controller.model.init_list()
        self.window.controller.model.update()
        self.close()

        # dispatch on update event
        event = Event(Event.MODELS_CHANGED)
        self.window.dispatch(event, all=True)

    def refresh(self, reload: bool = False):
        """
        Reload items

        :param reload: reload available models
        """
        if reload:
            self.items_available = self.get_ollama_available()

        # remove from available if already in current
        if not self.all:
            for key in list(self.items_available.keys()):
                if self.in_current(key):
                    del self.items_available[key]

        self.window.ui.nodes['models.importer.editor'].update_available(self.items_available)
        self.window.ui.nodes['models.importer.editor'].update_current(self.items_current)

    def get_by_idx(self, idx: int, items: Dict) -> Optional[str]:
        """
        Get model key by list index

        :param idx: list index
        :param items: items dictionary
        :return: model key
        """
        model_idx = 0
        for id in self.get_ids(items):
            if model_idx == idx:
                return id
            model_idx += 1
        return None

    def get_ids(self, items: Dict) -> List[str]:
        """
        Return models ids

        :return: model ids list
        """
        return list(items.keys())