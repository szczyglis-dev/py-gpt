#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 21:00:00                  #
# ================================================== #

import copy
import os
from typing import List, Dict, Optional, Any

from PySide6 import QtCore
from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import Event
from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LLAMA_INDEX,
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_EXPERT,
)
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
        self.items_available_all = {}  # available models for import
        self.items_available = {}  # available models for import
        self.items_current = {}  # current models in use
        self.pending = {}  # waiting to be imported models
        self.removed = {}  # waiting to be removed models
        self.selected_available = None  # selected available model (single)
        self.selected_current = None  # selected current model (single)
        self.selected_available_ids: List[str] = []  # multi-selected available models
        self.selected_current_ids: List[str] = []  # multi-selected current models
        self.all = False  # show all models, not only available for import
        self.provider = "_"  # default provider

    def in_current(self, model: str) -> bool:
        """
        Check if model is in current list

        :param model: model ID
        :return: True if model is in current list, False otherwise
        """
        if self.provider not in self.items_current:
            self.items_current[self.provider] = {}
        if model in self.items_current[self.provider]:
            return True
        for key in list(self.items_current[self.provider].keys()):
            m = self.items_current[self.provider][key]
            if m.id == model:  # also check in IDs
                return True
        return False

    def change_available(self):
        """On change available model selection"""
        view = self.window.ui.nodes["models.importer.available"]
        sel_model = view.selectionModel()
        rows = sel_model.selectedRows() if sel_model else []
        # collect selected model keys by reading stored tooltip role (stable ID)
        selected_ids = []
        for ix in rows:
            key = ix.data(QtCore.Qt.ToolTipRole)
            if not key:
                key = self.get_by_idx(ix.row(), self.items_available)
            if key and key not in selected_ids:
                selected_ids.append(key)

        self.selected_available_ids = selected_ids
        if not selected_ids:
            self.selected_available = None
            self.window.ui.nodes["models.importer.add"].setEnabled(False)
            return

        # keep a single reference for backward compatibility (last selected)
        self.selected_available = selected_ids[-1]

        # enable add if any of selected can be added (not already in current)
        can_add = False
        for key in selected_ids:
            if key is None:
                continue
            if not self.in_current(key) and self.items_available.get(key) is not None:
                can_add = True
                break
        self.window.ui.nodes["models.importer.add"].setEnabled(can_add)

    def change_current(self):
        """On change current model selection"""
        if self.provider not in self.items_current:
            self.items_current[self.provider] = {}
        view = self.window.ui.nodes["models.importer.current"]
        sel_model = view.selectionModel()
        rows = sel_model.selectedRows() if sel_model else []
        # collect selected model keys by reading stored tooltip role (stable ID)
        selected_ids = []
        for ix in rows:
            key = ix.data(QtCore.Qt.ToolTipRole)
            if not key:
                key = self.get_by_idx(ix.row(), self.items_current[self.provider])
            if key and key not in selected_ids:
                selected_ids.append(key)

        self.selected_current_ids = selected_ids
        if not selected_ids:
            self.selected_current = None
            self.window.ui.nodes["models.importer.remove"].setEnabled(False)
            return

        # keep a single reference for backward compatibility (last selected)
        self.selected_current = selected_ids[-1]

        # enable remove if any of selected can be removed
        can_remove = False
        for key in selected_ids:
            if key is None:
                continue
            if (key in self.items_current[self.provider]) and self.in_available(key):
                can_remove = True
                break
        self.window.ui.nodes["models.importer.remove"].setEnabled(can_remove)

    def in_available(self, model: str) -> bool:
        """
        Check if model is in available list (all)

        :param model: model ID
        :return: True if model is in available list, False otherwise
        """
        if model in self.items_available_all:
            return True
        for key in list(self.items_available_all.keys()):
            m = self.items_available_all[key]
            if m.id == model:
                return True
        return False

    def _selected_keys_from_view(self, node_id: str, items: Dict) -> List[str]:
        """
        Resolve selected model keys from a given list view using stored tooltip role,
        falling back to index->dict mapping when needed.

        :param node_id: ui node id
        :param items: dict used to build the view's model
        :return: list of selected keys
        """
        keys: List[str] = []
        try:
            view = self.window.ui.nodes[node_id]
            sel_model = view.selectionModel()
            rows = sel_model.selectedRows() if sel_model else []
            for ix in rows:
                key = ix.data(QtCore.Qt.ToolTipRole)
                if not key:
                    key = self.get_by_idx(ix.row(), items)
                if key and key not in keys:
                    keys.append(key)
        except Exception:
            pass
        return keys

    def add(self):
        """Add model(s) to current list"""
        if self.provider not in self.items_current:
            self.items_current[self.provider] = {}

        # collect multi-selection; fallback to single selection
        keys = self._selected_keys_from_view(
            'models.importer.available',
            self.items_available,
        )
        if not keys and self.selected_available is not None:
            keys = [self.selected_available]

        if not keys:
            self.set_status(trans('models.importer.error.add.no_model'))
            return

        any_added = False
        for key in list(keys):
            if key is None:
                continue
            if self.in_current(key):
                continue
            model = self.items_available.get(key)
            if model is None:
                continue
            self.items_current[self.provider][key] = model
            if key not in self.pending:
                self.pending[key] = model
            if key in self.removed:
                del self.removed[key]
            if not self.all and key in self.items_available:
                del self.items_available[key]
            any_added = True

        if not any_added:
            self.set_status(trans('models.importer.error.add.not_exists'))
            return

        self.refresh()

    def remove(self):
        """Remove model(s) from current list"""
        if self.provider not in self.items_current:
            self.items_current[self.provider] = {}

        # collect multi-selection; fallback to single selection
        keys = self._selected_keys_from_view(
            'models.importer.current',
            self.items_current[self.provider],
        )
        if not keys and self.selected_current is not None:
            keys = [self.selected_current]

        if not keys:
            self.set_status(trans('models.importer.error.remove.no_model'))
            return

        any_removed = False
        for key in list(keys):
            if key is None:
                continue
            if not self.in_current(key):
                continue
            model = self.items_current[self.provider].get(key)
            if model is None:
                continue
            # return to available list
            self.items_available[key] = model
            if key not in self.removed:
                self.removed[key] = model
            if key in self.items_current[self.provider]:
                del self.items_current[self.provider][key]
            if key in self.pending:
                del self.pending[key]
            any_removed = True

        if not any_removed:
            self.set_status(trans('models.importer.error.remove.not_exists'))
            return

        self.refresh()

    def setup(self):
        """Set up importer"""
        idx = None
        option = self.get_providers_option()
        self.window.model_importer.setup(idx)  # widget dialog setup
        self.window.ui.config["models.importer"]["provider"].set_keys(option["keys"])
        self.window.ui.add_hook("update.models.importer.provider", self.hook_update)

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
            self.provider = "_"  # default provider
            self.pending = {}
            self.removed = {}
            self.items_current = {}
            self.items_available = {}
            self.items_available_all = {}
            option = self.get_providers_option()
            self.window.controller.config.apply_value(
                parent_id="models.importer",
                key="provider",
                option=option,
                value="_",
            )
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

    def init(
            self,
            reload: bool = False,
            on_change: bool = False
    ):
        """
        Initialize importer

        :param reload: force re-initialize
        :param on_change: on change provider
        """
        if (self.initialized
                and self.window.ui.nodes["models.importer.available.all"].isChecked()):
            self.all = True
        self.update_title()
        if not reload:
            self.items_available = self.get_available()
        if not on_change:
            self.items_current[self.provider] = self.get_current()
        else:
            # on change provider, only if not loaded
            if self.provider not in self.items_current:
                self.items_current[self.provider] = {}
                self.items_current[self.provider] = self.get_current()
        self.refresh(reload=reload)

    def update_title(self):
        """Update dialog title with current provider"""
        if self.provider == "ollama":
            current = "http://localhost:11434"
            if 'OLLAMA_API_BASE' in os.environ:
                current = os.environ['OLLAMA_API_BASE']
        elif self.provider == "_":
            current = trans("models.importer.current.default")
            self.set_status("")
        else:
            current = self.window.core.llm.get_provider_name(self.provider)
        self.window.ui.nodes["models.importer.url"].setText(current)

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

    def get_current(self) -> Dict:
        """
        Get current ollama models

        :return: PyGPT ollama models dictionary
        """
        if self.provider == "_":
            return {}
        items = copy.deepcopy(self.window.core.models.items)
        for key in list(items.keys()):
            if items[key].provider != self.provider:
                del items[key]
        return items

    def get_available(self) -> Dict:
        """
        Get available models for import

        :return: available models dictionary
        """
        models = {}
        if self.provider == "ollama":
            models = self.get_ollama_available()
        else:
            try:
                models = self.get_provider_available()
            except Exception as e:
                print(e)
                self.set_status(str(e))
        models = dict(sorted(models.items(), key=lambda item: item[1].id.lower()))
        return models

    def get_provider_available(self) -> Dict:
        """
        Get available provider models

        :return: Provider API models dictionary
        """
        models = {}
        if not self.provider or self.provider == "_":
            return models
        llm = self.window.core.llm.get(self.provider)
        if llm is None:
            return models
        models_list = llm.get_models(self.window)
        if not models_list or not isinstance(models_list, list):
            return models
        for model in models_list:
            if "id" not in model:
                continue
            id = model.get('id')
            name = model.get('id')
            if "name" in model:
                name = model.get('name')
            m, _ = self.window.core.models.create_empty(append=False)
            m.id = id
            m.name = name
            m.mode = [
                MODE_CHAT,
                MODE_LLAMA_INDEX,
                MODE_AGENT,
                MODE_AGENT_LLAMA,
                MODE_AGENT_OPENAI,
                MODE_EXPERT,
            ]
            m.provider = self.provider
            m.input = ["text"]
            m.output = ["text"]
            llama_id = id
            if self.provider == "google":
                llama_id = "models/" + id
            m.llama_index['args'] = [
                {
                    'name': 'model',
                    'value': llama_id,
                    'type': 'str'
                }
            ]
            m.imported = True
            m.ctx = 128000 # default context size
            key = m.id

            # prepare args and env config by provider
            if self.provider == "anthropic":
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'ANTHROPIC_API_KEY',
                        'value': '{api_key_anthropic}',
                        'type': 'str'
                    }
                ]
            elif self.provider == "deepseek_api":
                m.tool_calls = True
                m.llama_index['args'].append(
                    {
                        'name': 'api_key',
                        'value': '{api_key_deepseek}',
                        'type': 'str'
                    }
                )
                m.llama_index['env'] = [
                    {
                        'name': 'DEEPSEEK_API_KEY',
                        'value': '{api_key_deepseek}',
                        'type': 'str'
                    }
                ]
            elif self.provider == "google":
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'GOOGLE_API_KEY',
                        'value': '{api_key_google}',
                        'type': 'str'
                    }
                ]
            elif self.provider in ["openai", "azure_openai"]:
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'OPENAI_API_KEY',
                        'value': '{api_key}',
                        'type': 'str'
                    },
                    {
                        'name': 'OPENAI_API_BASE',
                        'value': '{api_endpoint}',
                        'type': 'str'
                    },
                    {
                        'name': 'AZURE_OPENAI_ENDPOINT',
                        'value': '{api_azure_endpoint}',
                        'type': 'str'
                    },
                    {
                        'name': 'OPENAI_API_VERSION',
                        'value': '{api_azure_version}',
                        'type': 'str'
                    }
                ]
            elif self.provider == "perplexity":
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'OPENAI_API_KEY',
                        'value': '{api_key_perplexity}',
                        'type': 'str'
                    },
                    {
                        'name': 'OPENAI_API_BASE',
                        'value': '{api_endpoint_perplexity}',
                        'type': 'str'
                    }
                ]
            elif self.provider == "mistral_ai":
                m.tool_calls = True
                m.llama_index['args'].append(
                    {
                        'name': 'api_key',
                        'value': '{api_key_mistral}',
                        'type': 'str'
                    }
                )
            elif self.provider == "local_ai":
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'OPENAI_API_KEY',
                        'value': '{api_key}',
                        'type': 'str'
                    },
                    {
                        'name': 'OPENAI_API_BASE',
                        'value': '{api_endpoint}',
                        'type': 'str'
                    }
                ]
            elif self.provider == "open_router":
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'OPENAI_API_KEY',
                        'value': '{api_key_open_router}',
                        'type': 'str'
                    },
                    {
                        'name': 'OPENAI_API_BASE',
                        'value': '{api_endpoint_open_router}',
                        'type': 'str'
                    }
                ]
            elif self.provider == "x_ai":
                m.tool_calls = True
                m.llama_index['env'] = [
                    {
                        'name': 'OPENAI_API_KEY',
                        'value': '{api_key_xai}',
                        'type': 'str'
                    },
                    {
                        'name': 'OPENAI_API_BASE',
                        'value': '{api_endpoint_xai}',
                        'type': 'str'
                    }
                ]
            models[key] = m
        provider_name = self.window.core.llm.get_provider_name(self.provider)
        self.set_status(trans('models.importer.loaded').replace("{provider}", provider_name))
        return models

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
                    name = model.get('name')
                    m, _ = self.window.core.models.create_empty(append=False)
                    m.id = name
                    m.name = name
                    m.mode = [
                        MODE_CHAT,
                        MODE_LLAMA_INDEX,
                        MODE_AGENT,
                        MODE_AGENT_LLAMA,
                        MODE_AGENT_OPENAI,
                        MODE_EXPERT,
                    ]
                    m.provider = 'ollama'
                    m.input = ["text"]
                    m.output = ["text"]
                    m.llama_index['args'] = [
                        {
                            'name': 'model',
                            'value': name,
                            'type': 'str'
                        }
                    ]
                    m.imported = True
                    m.ctx = 32000  # default
                    key = m.id
                    models[key] = m
                self.set_status(trans('models.importer.loaded').replace("{provider}", "Ollama"))
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
            else:
                # add provider suffix - to key
                new_key = f"{key}-{self.provider}"
                if new_key not in base_models:
                    base_models[new_key] = copy.deepcopy(self.pending[key])
                    base_models[new_key].imported = True
                    added = True
        for key in list(self.removed.keys()):
            if key in base_models:
                del base_models[key]
                added = True
        self.pending = {}
        self.removed = {}
        if added:
            self.window.core.models.sort_items()
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
        if self.provider == "_":
            self.set_status("")

        if reload:
            if self.provider == "_":
                self.set_status("")
            else:
                self.set_status(trans("models.importer.status.wait"))
            QApplication.processEvents()
            self.items_available = self.get_available()
            self.items_available_all = copy.deepcopy(self.items_available)

        # remove from available if already in current
        if not self.all:
            for key in list(self.items_available.keys()):
                if self.in_current(key):
                    del self.items_available[key]

        self.window.ui.nodes['models.importer.editor'].update_available(self.items_available)
        self.window.ui.nodes['models.importer.editor'].update_current(self.items_current[self.provider])

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

    def get_providers_option(self) -> Dict:
        """
        Get available LLM providers option

        :return: Dict with keys and values
        """
        excluded = [
            #"azure_openai",
            "huggingface_api",
            #"mistral_ai",
            "local_ai",
            "perplexity",
        ]
        choices = self.window.core.llm.get_choices()
        data = []
        data.append({"_": trans("models.importer.list.select")})
        for id in choices:
            if id in excluded:
                continue
            data.append({id: choices[id]})

        option = {
            "type": "combo",
            "label": "Provider",
            "keys": data,
        }
        return option

    def hook_update(
            self,
            key: str,
            value: Any,
            caller,
            *args,
            **kwargs
    ):
        """
        Hook: on settings update in real-time (prompt)

        :param key: setting key
        :param value: setting value
        :param caller: caller id
        :param args: additional arguments
        :param kwargs: additional keyword arguments
        """
        # show/hide extra options
        if key == "provider":
            self.provider = value
            self.init(reload=True, on_change=True)
            if value == "_":
                self.set_status("")