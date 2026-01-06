#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 18:00:00                  #
# ================================================== #

import copy
import json
from typing import Optional, Union, Any, List

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QStandardItem

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.utils import trans

from .batch import Batch


class RemoteStore:

    DEFAULT_PROVIDER = "openai"
    PROVIDERS = {
        "openai": "OpenAI",
        "google": "Google",
        # "anthropic": "Anthropic",  # TODO: enable when SDK fixed
        "xai": "xAI (Collections)",
    }

    def __init__(self, window=None):
        """
        Unified Remote Store controller

        :param window: Window instance
        """
        self.window = window

        # Unified UI state
        self.dialog = False
        self.config_initialized = False
        self.current: Optional[str] = None
        self.width = 900
        self.height = 560
        self.id = "remote_store"
        self.initialized = False

        # Active provider: 'google' | 'openai' | 'anthropic' | 'xai'
        self.provider_key: Optional[str] = None

        # Mapping row -> ids for current stores/files list
        self._stores_row_to_id: List[str] = []
        self._files_row_to_id: List[str] = []

        # Upload queue
        self.files_to_upload: List[str] = []

        # Unified options schema; UI hides provider-specific fields
        self.options = {
            "id": {
                "type": "text",
                "label": "remote_store.id",
                "description": "remote_store.id.description",
                "read_only": True,
                "value": "",
            },
            "name": {
                "type": "text",
                "label": "remote_store.name",
                "value": "",
            },
            "expire_days": {
                "type": "int",
                "label": "remote_store.expire_days",
                "value": 0,  # OpenAI only; hidden for Google/Anthropic/xAI
                "advanced": False,
            },
            "status": {
                "type": "textarea",
                "label": "remote_store.status",
                "read_only": True,
                "value": "",
            },
        }

        self.batch = Batch(self)

    # ======================== Provider helpers ========================

    def get_providers(self) -> dict:
        """Return available providers."""
        return self.PROVIDERS

    def get_provider_keys(self) -> List[str]:
        """Return available provider keys."""
        return list(self.PROVIDERS.keys())

    def _get_provider(self) -> str:
        """Return current provider key."""
        if self.provider_key in self.get_provider_keys():
            return self.provider_key
        key = self.window.core.config.get("remote_store.provider")
        if key not in self.get_provider_keys():
            key = self.DEFAULT_PROVIDER
            try:
                self.window.core.config.set("remote_store.provider", key)
            except Exception:
                pass
        self.provider_key = key
        return key

    def set_provider(self, key: str):
        """Set active provider and re-init UI."""
        if key not in self.get_provider_keys():
            return
        self.provider_key = key
        try:
            self.window.core.config.set("remote_store.provider", key)
        except Exception:
            pass
        # Force selecting the first visible store for the new provider and refresh files list
        self.init(select_first=True)

    def _core_for(self, provider: Optional[str] = None):
        key = provider or self._get_provider()
        if hasattr(self.window.core.remote_store, key):
            return getattr(self.window.core.remote_store, key)

    def _files_core_for(self, provider: Optional[str] = None):
        return self._core_for(provider).files

    def _api_store_for(self, provider: Optional[str] = None):
        key = provider or self._get_provider()
        if hasattr(self.window.core.api, key):
            return getattr(self.window.core.api, key).store

    # ======================== Provider hooks ========================

    def after_create(self, provider: str, store: RemoteStoreItem):
        """Hook: called after store creation (per provider)."""
        if provider == "openai":
            self.window.controller.assistant.editor.update_store_list()  # update stores list in assistant dialog

    def after_delete(self, provider: str, store_id: str):
        """Hook: called after store deletion (per provider)."""
        if provider == "openai":
            self.window.controller.assistant.editor.update_store_list()  # update stores list in assistant dialog

    def after_update(self, provider: str, store: RemoteStoreItem):
        """Hook: called after store update (per provider)."""
        if provider == "openai":
            self.window.controller.assistant.editor.update_store_list()

    def after_truncated_stores(self, provider: str):
        """Hook: called after truncating all stores (per provider)."""
        if provider == "openai":
            try:
                self.window.controller.assistant.batch.remove_all_stores_from_assistants()
                self.window.controller.assistant.editor.update_store_list()  # update stores list in assistant dialog
            except Exception:
                pass

    def after_imported_stores(self, provider: str):
        """Hook: called after importing stores (per provider)."""
        if provider == "openai":
            try:
                self.window.controller.assistant.files.update()
                self.window.controller.assistant.editor.update_store_list()  # update stores list in assistant dialog
            except Exception:
                pass

    # ======================== Options ========================

    def get_options(self) -> dict:
        return self.options

    def get_option(self, key: str) -> Optional[dict]:
        if key in self.options:
            return self.options[key]

    # ======================== Lifecycle ========================

    def setup(self):
        """Setup caches and build the unified dialog."""
        try:
            self.window.core.remote_store.openai.load_all()
            self.window.core.remote_store.google.load_all()
            self.window.core.remote_store.anthropic.load_all()
            self.window.core.remote_store.xai.load_all()
        except Exception as e:
            self.window.core.debug.log(e)

    def reload(self):
        """Reload provider data and refresh unified view."""
        try:
            self.window.core.remote_store.openai.load_all()
            self.window.core.remote_store.google.load_all()
            self.window.core.remote_store.anthropic.load_all()
            self.window.core.remote_store.xai.load_all()
        except Exception as e:
            self.window.core.debug.log(e)
        self.reset()

    def reset(self):
        """Reset current selection."""
        self.current = None
        if self.dialog:
            self.init()

    def toggle_editor(self, provider: Optional[str] = None):
        """Toggle unified dialog."""
        if provider is not None:
            self.set_provider(provider)
        if self.dialog:
            self.close()
        else:
            self.open()

    def open(self, force: bool = False):
        """Open dialog."""
        if not self.config_initialized:
            self.setup()
            self.config_initialized = True
        if not self.dialog or force:
            # Force selecting the first visible store on dialog open
            self.init(select_first=True)
            self.window.ui.dialogs.open(
                "remote_store",
                width=self.width,
                height=self.height,
            )
            self.dialog = True

    def close(self):
        """Close dialog."""
        if self.dialog:
            self.window.ui.dialogs.close("remote_store")
            self.dialog = False

    # ======================== Initialize / Refresh ========================

    def init(self, select_first: bool = False):
        """Initialize UI state for the active provider."""
        if not self.initialized:
            # Setup dialog UI
            self.window.remote_store.setup()

            # Ensure provider combobox is synced at first load
            try:
                self.window.remote_store.set_provider_in_ui(self._get_provider())
            except Exception:
                pass
            self.initialized = True

        self.reload_items()

        # Ensure a valid selection, optionally forcing the first visible store
        core = self._core_for()
        if select_first:
            # Reset current to enforce picking the first visible store below
            self.current = None
        if self.current is None or not core.has(self.current):
            self.current = self.get_first_visible()

        options = copy.deepcopy(self.get_options())
        if self.current is not None and core.has(self.current):
            store = core.items[self.current]
            data_dict = store.to_dict()
            for key in options:
                if key in data_dict:
                    value = data_dict[key]
                    if key == "status":
                        options[key]["value"] = json.dumps(value, indent=4)
                    else:
                        options[key]["value"] = value
            # Reflect selection in the left list
            self.set_tab_by_id(self.current)
            self.window.controller.config.load_options(self.id, options)
        else:
            self.current = None
            self.window.controller.config.load_options(self.id, options)

        # Provider-specific visibility
        try:
            self.window.remote_store.sync_provider_dependent_ui(self._get_provider())
        except Exception:
            pass

        # Always refresh files list on provider/selection changes (also clears when empty)
        self.update_files_list()
        try:
            self.window.remote_store.sync_hide_threads_checkbox(self._get_provider())
        except Exception:
            pass

        # Update dialog title
        try:
            self.window.remote_store.update_title(self._dialog_title_for_provider(self._get_provider()))
        except Exception:
            pass

    def refresh_status(self):
        """Reload current store status from API and refresh UI."""
        if self.current is None:
            return
        core = self._core_for()
        if not core.has(self.current):
            return

        self.window.update_status(trans('status.sending'))
        QApplication.processEvents()
        try:
            core.update_status(self.current)
            store = core.items[self.current]
            core.update(store)
            self.window.update_status(trans('status.finished'))
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.update_status(trans('status.error'))

        self.update_current()
        self.update()
        self.update_files_list()

    def refresh_store(self, store: RemoteStoreItem, update: bool = True, provider: Optional[str] = None):
        """Refresh a store by item."""
        if provider:
            if self._get_provider() != provider:
                return
        provider = self._get_provider()
        core = self._core_for(provider)
        core.update_status(store.id)
        core.update(store)
        if update and store.id == self.current:
            self.update_current()

    def refresh_by_idx(self, idx: Union[int, list]):
        """Refresh store(s) by list index or list of indexes."""
        store_ids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            store_id = self.get_by_tab_idx(i)
            if store_id is not None:
                store_ids.append(store_id)
        self.refresh_by_store_id(store_ids)

    def refresh_by_store_id(self, store_id: Union[str, list], provider: Optional[str] = None):
        """Refresh store(s) by ID."""
        if provider:
            if self._get_provider() != provider:
                return
        ids = store_id if isinstance(store_id, list) else [store_id]
        updated = False
        is_current = False
        core = self._core_for()
        for sid in ids:
            if sid is not None and core.has(sid):
                store = core.items[sid]
                if store is not None:
                    self.window.update_status(trans('status.sending'))
                    QApplication.processEvents()
                    self.refresh_store(store)
                    updated = True
                    if self.current == sid:
                        is_current = True
        if updated:
            self.window.update_status(trans('status.finished'))
            self.update()
            if is_current:
                self.update_files_list()

    def refresh_by_store_id_provider(self, provider: str, store_id: Optional[str]):
        """Refresh status for a specific provider+store (used by proxies after async)."""
        if store_id is None:
            return
        core = self._core_for(provider)
        if store_id not in core.items:
            return
        store = core.items[store_id]
        try:
            core.update_status(store_id)
            core.update(store)
        except Exception as e:
            self.window.core.debug.log(e)

        if provider == self._get_provider() and self.current == store_id:
            self.update_current()
            self.update()
            self.update_files_list()

    # ======================== UI update helpers ========================

    def update_current(self):
        """Update current store values in right panel."""
        if self.current is None:
            return
        core = self._core_for()
        if not core.has(self.current):
            return
        store = core.items[self.current]

        option = copy.deepcopy(self.get_option("status"))
        option["value"] = json.dumps(store.status, indent=4)
        self.window.controller.config.apply(self.id, "status", option)

        option = copy.deepcopy(self.get_option("name"))
        option["value"] = store.name
        self.window.controller.config.apply(self.id, "name", option)

        option = copy.deepcopy(self.get_option("id"))
        option["value"] = store.id
        self.window.controller.config.apply(self.id, "id", option)

        if self._get_provider() == "openai":
            try:
                option = copy.deepcopy(self.get_option("expire_days"))
                option["value"] = int(getattr(store, "expire_days", 0) or 0)
                self.window.controller.config.apply(self.id, "expire_days", option)
            except Exception:
                pass

    def update(self):
        """Refresh lists and auxiliary widgets."""
        self.reload_items()
        try:
            self.after_update(self._get_provider())
        except Exception:
            pass
        self.update_files_list()

    def reload_items(self):
        """Reload left stores list for current provider."""
        core = self._core_for()
        items = core.get_all()
        hide_threads = bool(self._get_hide_threads_config(self._get_provider()))
        suffix = trans("remote_store.files.suffix")

        pairs: List[tuple[str, str]] = []
        for sid, store in items.items():
            if core.is_hidden(sid) or (hide_threads and (store.name is None or store.name == "")):
                continue
            num_files = store.get_file_count()
            name = store.name or store.id
            extras = []
            if num_files > 0:
                extras.append(f"{num_files} {suffix}")
            if getattr(store, "usage_bytes", 0) > 0:
                try:
                    extras.append(self.window.core.filesystem.sizeof_fmt(store.usage_bytes))
                except Exception:
                    pass
            if extras:
                name = f"{name} ({' - '.join(extras)})"
            pairs.append((sid, name))

        self._stores_row_to_id = [sid for sid, _ in pairs]
        try:
            self.window.remote_store.update_list_pairs("remote_store.list", pairs)
        except Exception:
            pass

        self.restore_selection()

    def restore_selection(self):
        """Restore left selection to self.current."""
        if self.current is not None:
            idx = self.get_tab_by_id(self.current)
            if idx is not None:
                self.set_by_tab(idx)

    # ======================== Selection ========================

    def select(self, idx: int):
        """Select store by index in the left list."""
        self.save(persist=False)
        sid = self.get_by_tab_idx(idx)
        if sid is None:
            return
        self.current = sid
        self.init()
        self.update_files_list()

    def set_by_tab(self, idx: int):
        """Select row (left list) by index."""
        try:
            self.window.remote_store.set_current_row("remote_store.list", idx)
        except Exception:
            pass

    def set_tab_by_id(self, store_id: str):
        """Select row by store id."""
        idx = self.get_tab_idx(store_id)
        if idx is None:
            return
        self.set_by_tab(idx)

    def get_tab_idx(self, store_id: str) -> Optional[int]:
        """Return row index for a given store id."""
        try:
            return self._stores_row_to_id.index(store_id)
        except Exception:
            return None

    def get_tab_by_id(self, store_id: str) -> Optional[int]:
        return self.get_tab_idx(store_id)

    def get_by_tab_idx(self, idx: int) -> Optional[str]:
        """Return store id by row index."""
        if idx < 0 or idx >= len(self._stores_row_to_id):
            return None
        return self._stores_row_to_id[idx]

    def get_first_visible(self) -> Optional[str]:
        """Return first visible store id for current provider (respects current UI filters)."""
        # Prefer what is actually visible in the left list
        if self._stores_row_to_id:
            return self._stores_row_to_id[0]
        # Fallback to provider core when left list is not initialized
        core = self._core_for()
        for sid in core.get_ids():
            if not core.is_hidden(sid):
                return sid
        return None

    # ======================== CRUD: stores ========================

    def save_btn(self):
        """Save and refresh status."""
        self.window.update_status("Saving...")
        self.save()
        self.refresh_status()
        self.window.update_status("Saved.")

    def save(self, persist: bool = True):
        """Persist right panel data to store and remote if supported."""
        if self.current is not None and self._core_for().has(self.current):
            current = self._core_for().items[self.current].to_dict()
            options = copy.deepcopy(self.get_options())
            data_dict = current
            for key in options:
                if key == "status":
                    data_dict[key] = current.get("status", {})
                    continue
                value = self.window.controller.config.get_value(
                    parent_id="remote_store",
                    key=key,
                    option=options[key],
                )
                data_dict[key] = value
            self._core_for().items[self.current].from_dict(data_dict)

        if persist:
            self.window.update_status(trans('status.sending'))
            QApplication.processEvents()
            if self.current is not None:
                store = self._core_for().update(self._core_for().items[self.current])
                if store is None:
                    self.window.update_status(trans('status.error'))
                    self.window.ui.dialogs.alert("Failed to save store")
                    return
            self.update()
            self.window.update_status(trans("info.settings.saved"))
            self.restore_selection()
            self.update_files_list()

    def new(self, name: str = "", force: bool = False):
        """Create a new store for active provider."""
        if not force:
            self.window.ui.dialog['create'].id = 'remote_store.new'
            self.window.ui.dialog['create'].input.setText("New vector store")
            self.window.ui.dialog['create'].current = "New vector store"
            self.window.ui.dialog['create'].show()
            return

        self.window.ui.dialog['create'].close()
        self.window.update_status(trans('status.sending'))
        QApplication.processEvents()
        try:
            core = self._core_for()
            display_name = name or "New vector store"
            store = core.create(display_name)
            if store is None:
                raise RuntimeError("Failed to create new store")
            core.update(store)

            self.after_create(self._get_provider(), store)
            self.window.update_status(trans('status.finished'))

            self.current = store.id
            self.reload_items()
            self.set_tab_by_id(self.current)
            self.init()
            self.restore_selection()
            self.refresh_by_store_id(store.id)
            self.update_files_list()

        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.update_status(trans('status.error'))

    def delete_by_idx(self, idx: Union[int, list], force: bool = False):
        """Delete store(s) by index(es)."""
        store_ids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            store_id = self.get_by_tab_idx(i)
            if store_id is not None:
                store_ids.append(store_id)
        self.delete(store_ids, force)

    def delete(self, store_id: Optional[Union[str, list]] = None, force: bool = False):
        """Delete store(s) by id."""
        if store_id is None:
            self.window.ui.dialogs.alert("Please select store first.")
            return

        if not force:
            t = "remote_store.delete"
            self.window.ui.dialogs.confirm(
                type=t,
                id=store_id,
                msg=trans("dialog.remote_store.delete.confirm"),
            )
            return

        self.window.update_status(trans('status.sending'))
        updated = False
        QApplication.processEvents()
        core = self._core_for()
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            if self.current == sid:
                self.current = None
            try:
                if core.delete(sid):
                    try:
                        self.window.controller.assistant.batch.remove_store_from_assistants(sid)
                    except Exception:
                        pass
                    self.window.update_status(trans('status.deleted'))
                    core.save()
                    self.after_delete(self._get_provider(), sid)
                    updated = True
                else:
                    self.window.update_status(trans('status.error'))
            except Exception as e:
                self.window.update_status(trans('status.error'))
                self.window.ui.dialogs.alert(e)
        if updated:
            self.update()
            self.init()
            self.restore_selection()
            self.update_files_list()

    # ======================== Files (documents) ========================

    def update_files_list(self):
        """Populate files list (documents) for the current store from local DB."""
        model_id = 'remote_store.files.list'
        if model_id not in self.window.ui.models:
            return
        model = self.window.ui.models[model_id]
        try:
            model.removeRows(0, model.rowCount())
        except Exception:
            pass

        self._files_row_to_id = []

        if self.current is None:
            return

        files_db = self._files_core_for()
        if files_db is None:
            return

        try:
            store_files = files_db.get_by_store_or_thread(self.current, None) or {}
        except Exception as e:
            self.window.core.debug.log(e)
            store_files = {}

        i = 0
        for file_id, file_obj in store_files.items():
            if isinstance(file_obj, dict):
                data = file_obj
            else:
                data = {}
                for key in ('id', 'file_id', 'name', 'filename', 'bytes', 'size', 'usage_bytes', 'status'):
                    try:
                        if hasattr(file_obj, key):
                            data[key] = getattr(file_obj, key)
                    except Exception:
                        pass
                if not data and hasattr(file_obj, 'to_dict'):
                    try:
                        data = file_obj.to_dict()
                    except Exception:
                        data = {}

            name = data.get('name') or data.get('filename') or file_id
            size_val = None
            for k in ('bytes', 'size', 'usage_bytes'):
                if data.get(k) is not None:
                    size_val = data.get(k)
                    break

            size_txt = ""
            try:
                if size_val:
                    size_txt = self.window.core.filesystem.sizeof_fmt(int(size_val))
            except Exception:
                pass

            extra = []
            if size_txt:
                extra.append(size_txt)
            if data.get('status'):
                extra.append(str(data.get('status')))
            label = name
            if extra:
                label += " ({})".format(", ".join(extra))

            item = QStandardItem(label)
            item.setEditable(False)
            model.setItem(i, 0, item)
            self._files_row_to_id.append(data['file_id'] if 'file_id' in data else file_id)
            i += 1

    def delete_file_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Delete a single document from the current store.
        Uses inline confirmation if force is False.
        """
        if self.current is None:
            self.window.ui.dialogs.alert("Please select store first.")
            return

        model_id = 'remote_store.files.list'
        if model_id not in self.window.ui.models:
            return

        if not isinstance(idx, list):
            idx = [idx]
        idx_list = []
        for i in idx:
            if i < 0 or i >= len(self._files_row_to_id):
                continue
            idx_list.append(i)

        file_ids = [self._files_row_to_id[i] for i in idx_list if self._files_row_to_id[i]]
        if not file_ids:
            return

        if not force:
            m = QMessageBox(self.window)
            m.setIcon(QMessageBox.Warning)
            m.setWindowTitle(trans("remote_store.menu.file.delete"))
            m.setText(trans('confirm.remote_store.file.delete'))
            m.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            m.setDefaultButton(QMessageBox.No)
            if m.exec() != QMessageBox.Yes:
                return

        self._delete_file_by_idx_provider(idx, self._get_provider())

    def _delete_file_by_idx_provider(self, idx: Union[int, list], provider: str, file_id: Optional[str] = None):
        """Provider-explicit file delete (used by proxies/confirm)."""
        if self.current is None and provider == self._get_provider():
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return

        model_id = 'remote_store.files.list'
        if model_id not in self.window.ui.models and provider == self._get_provider():
            return

        idx_list = []
        if file_id is None:
            if not isinstance(idx, list):
                idx = [idx]
            for i in idx:
                if i < 0 or i >= len(self._files_row_to_id):
                    continue
                idx_list.append(i)

            if not idx_list:
                return

            file_ids = [self._files_row_to_id[i] for i in idx_list if self._files_row_to_id[i]]
            if not file_ids:
                return
        else:
            file_ids = [file_id]
            idx_list = [idx] if isinstance(idx, int) else idx

        # sort indexes descending to avoid shifting issues when removing multiple
        idx_list.sort(reverse=True)

        self.window.update_status(trans('status.sending'))
        QApplication.processEvents()
        try:
            api = self._api_store_for(provider)
            removed = False

            for file_id in file_ids:
                if hasattr(api, 'remove_store_file'):
                    try:
                        api.remove_store_file(self.current if provider == self._get_provider() else "", file_id)
                        removed = True
                    except Exception as e:
                        self.window.core.debug.log(e)

                if not removed and hasattr(api, 'remove_file'):
                    try:
                        api.remove_file(file_id)
                        removed = True
                    except Exception as e:
                        self.window.core.debug.log(e)

            if not removed:
                raise RuntimeError("Remove file API not available.")

            for file_id in file_ids:
                try:
                    self._files_core_for(provider).delete_by_file_id(file_id)
                except Exception as e:
                    self.window.core.debug.log(e)

            if provider == self._get_provider():
                try:
                    for i in idx_list:
                        self.window.ui.models[model_id].removeRow(i)
                        try:
                            del self._files_row_to_id[i]
                        except Exception:
                            pass
                except Exception:
                    pass

            QTimer.singleShot(1200, self.refresh_status)
            self.window.update_status(trans('status.deleted'))

        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert("Failed to delete file: {}".format(e))
            self.window.update_status(trans('status.error'))
            if provider == self._get_provider():
                self.update_files_list()

    # ======================== Hide threads ========================

    def set_hide_thread(self, state: bool):
        """Toggle hide thread stores for current provider."""
        self._set_hide_threads_config(self._get_provider(), state)
        self.update()

    def _get_hide_threads_config(self, provider: str) -> Any:
        key = "remote_store.hide_threads"
        return self.window.core.config.get(key)

    def _set_hide_threads_config(self, provider: str, state: bool):
        key = "remote_store.hide_threads"
        self.window.core.config.set(key, bool(state))

    # ======================== Title ========================

    def _dialog_title_for_provider(self, provider: str) -> str:
        return trans('dialog.remote_store')

    # ======================== Unified batch entry points (UI menu) ========================

    def import_stores(self, force: bool = False):
        if not force:
            t = 'remote_store.import'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans('confirm.remote_store.import'))
            return
        imp = self._importer_for(self._get_provider())
        self._core_for().truncate()
        imp.import_vector_stores()

    def refresh_stores(self, force: bool = False):
        if not force:
            t = 'remote_store.refresh'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans('confirm.remote_store.refresh'))
            return
        imp = self._importer_for(self._get_provider())
        imp.refresh_vector_stores()

    def truncate_stores(self, force: bool = False):
        if not force:
            t = 'remote_store.truncate'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans('confirm.remote_store.truncate'))
            return
        imp = self._importer_for(self._get_provider())
        self._core_for().truncate()
        imp.truncate_vector_stores()

    def import_files(self, force: bool = False):
        if not force:
            t = 'remote_store.files.import.all'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans('confirm.remote_store.import_files'))
            return
        imp = self._importer_for(self._get_provider())
        imp.import_files()

    def import_store_files(self, store_id: str, force: bool = False):
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        if not force:
            t = 'remote_store.files.import.store'
            self.window.ui.dialogs.confirm(type=t, id=store_id, msg=trans('confirm.remote_store.import_files.store'))
            return
        imp = self._importer_for(self._get_provider())
        self.window.update_status("Importing files...please wait...")
        imp.import_files(store_id)

    def truncate_files(self, force: bool = False):
        if not force:
            t = 'remote_store.files.truncate'
            key = 'confirm.remote_store.files.truncate'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans(key))
            return
        imp = self._importer_for(self._get_provider())
        imp.truncate_files()

    def truncate_store_files(self, store_id: Union[str, list], force: bool = False):
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        if not force:
            t = 'remote_store.files.truncate.store'
            key = 'confirm.remote_store.files.truncate.store'
            self.window.ui.dialogs.confirm(type=t, id=store_id, msg=trans(key))
            return
        imp = self._importer_for(self._get_provider())
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            imp.truncate_files(sid)

    def clear_files(self, force: bool = False):
        if not force:
            t = 'remote_store.files.clear.all'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans('confirm.assistant.files.clear'))
            return
        self.window.update_status("Clearing documents...please wait...")
        QApplication.processEvents()
        try:
            self._files_core_for().truncate_local()
        except Exception as e:
            self.window.core.debug.log(e)
        self.update()
        self.window.update_status("OK. All documents cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_store_files(self, store_id: Optional[Union[str, list]] = None, force: bool = False):
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        if not force:
            t = 'remote_store.files.clear.store'
            self.window.ui.dialogs.confirm(type=t, id=store_id, msg=trans('confirm.assistant.files.clear'))
            return
        self.window.update_status("Clearing store documents...please wait...")
        QApplication.processEvents()
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            try:
                self._files_core_for().truncate_local(sid)
            except Exception as e:
                self.window.core.debug.log(e)
        self.update()
        self.window.update_status("OK. Store documents cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_stores(self, force: bool = False):
        if not force:
            t = 'remote_store.clear'
            self.window.ui.dialogs.confirm(type=t, id='', msg=trans('confirm.remote_store.clear'))
            return
        self.window.update_status("Clearing stores...please wait...")
        QApplication.processEvents()
        try:
            self._core_for().truncate()
        except Exception as e:
            self.window.core.debug.log(e)
        self.update()
        self.current = None
        self.init()
        self.window.update_status("OK. All stores cleared.")

    # ======================== Utilities ========================

    def _importer_for(self, provider: str):
        if (hasattr(self.window.core.api, provider)
                and hasattr(getattr(self.window.core.api, provider), 'store')
                and hasattr(getattr(self.window.core.api, provider).store, 'importer')):
            return getattr(self.window.core.api, provider).store.importer