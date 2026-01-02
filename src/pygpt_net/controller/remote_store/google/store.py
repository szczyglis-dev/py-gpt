#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

import copy
import json
from typing import Optional, Union

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QStandardItem
from PySide6.QtCore import Qt, QTimer

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.utils import trans

from .batch import Batch


class GoogleRemoteStore:
    def __init__(self, window=None):
        """
        Google File Search store editor controller

        :param window: Window instance
        """
        self.window = window
        self.batch = Batch(window)
        self.dialog = False
        self.config_initialized = False
        self.current = None
        self.width = 800
        self.height = 500
        self.id = "remote_store.google"
        self.options = {
            "id": {
                "type": "text",
                "label": "remote_store.id",
                "read_only": True,
                "value": "",
            },
            "name": {
                "type": "text",
                "label": "remote_store.name",
                "value": "",
            },
            "status": {
                "type": "textarea",
                "label": "remote_store.status",
                "read_only": True,
                "value": "",
            },
        }
        self._files_row_to_id = []

    def get_options(self) -> dict:
        return self.options

    def get_option(self, key: str) -> Optional[dict]:
        if key in self.options:
            return self.options[key]

    def setup(self):
        """Set up store editor"""
        idx = None
        self.window.remote_store_google.setup(idx)

    def toggle_editor(self):
        """Toggle editor dialog"""
        if self.dialog:
            self.close()
        else:
            self.open()

    def reset(self):
        """Reset store editor"""
        self.current = None
        if self.dialog:
            self.init()

    def open(self, force: bool = False):
        """
        Open store editor dialog

        :param force: force open dialog
        """
        if not self.config_initialized:
            self.setup()
            self.config_initialized = True
        if not self.dialog or force:
            self.current = self.window.controller.assistant.editor.get_selected_store_id()
            self.init()
            self.window.ui.dialogs.open(
                "remote_store.google",
                width=self.width,
                height=self.height,
            )
            self.dialog = True

    def close(self):
        """Close editor dialog"""
        if self.dialog:
            self.window.ui.dialogs.close('remote_store.google')
            self.dialog = False

    def init(self):
        """Initialize editor options"""
        self.reload_items()

        if self.current is None:
            self.current = self.get_first_visible()

        options = copy.deepcopy(self.get_options())
        if self.current is not None and self.window.core.remote_store.google.has(self.current):
            store = self.window.core.remote_store.google.items[self.current]
            data_dict = store.to_dict()
            for key in options:
                if key in data_dict:
                    value = data_dict[key]
                    options[key]["value"] = value
                    if key == "status":
                        options[key]["value"] = json.dumps(value, indent=4)

            self.set_tab_by_id(self.current)
            self.window.controller.config.load_options(self.id, options)
        else:
            self.current = None
            self.window.controller.config.load_options(self.id, options)

        self.update_files_list()

    def refresh_status(self):
        """Reload store status"""
        if self.current is not None:
            if self.window.core.remote_store.google.has(self.current):
                self.window.update_status(trans('status.sending'))
                QApplication.processEvents()
                store = self.window.core.remote_store.google.items[self.current]
                self.refresh_store(store)
                self.window.update_status(trans('status.finished'))
                self.update()
                self.update_files_list()

    def refresh_store(self, store: RemoteStoreItem, update: bool = True):
        """
        Refresh store by item

        :param store: store object
        :param update: apply updates to current
        """
        self.window.core.remote_store.google.update_status(store.id)
        self.window.core.remote_store.google.update(store)
        if update and store.id == self.current:
            self.update_current()

    def refresh_by_idx(self, idx: Union[int, list]):
        """
        Refresh store by list index or list of indexes

        :param idx: index or list
        """
        store_ids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            store_id = self.get_by_tab_idx(i)
            if store_id is not None:
                store_ids.append(store_id)
        self.refresh_by_store_id(store_ids)

    def refresh_by_store_id(self, store_id: Union[str, list]):
        """
        Refresh store by ID(s)

        :param store_id: store name or list
        """
        ids = store_id if isinstance(store_id, list) else [store_id]
        updated = False
        is_current = False
        for sid in ids:
            if sid is not None and sid in self.window.core.remote_store.google.items:
                store = self.window.core.remote_store.google.items[sid]
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

    def update_current(self):
        """Update current store values in the UI"""
        if self.current is not None and self.window.core.remote_store.google.has(self.current):
            store = self.window.core.remote_store.google.items[self.current]
            option = copy.deepcopy(self.get_option("status"))
            option["value"] = json.dumps(store.status, indent=4)
            self.window.controller.config.apply(self.id, "status", option)

            option = copy.deepcopy(self.get_option("name"))
            option["value"] = store.name
            self.window.controller.config.apply(self.id, "name", option)

    def save_btn(self):
        """Save editor and refresh"""
        self.window.update_status("Saving...")
        self.save()
        self.refresh_status()
        self.window.update_status("Saved.")

    def save(self, persist: bool = True):
        """
        Save editor data to local store and (if possible) remote

        :param persist: persist to file and close dialog
        """
        if self.current is not None:
            current = self.window.core.remote_store.google.items[self.current].to_dict()
            options = copy.deepcopy(self.get_options())
            data_dict = {}
            for key in options:
                if key == "status":
                    data_dict[key] = current[key]
                    continue
                value = self.window.controller.config.get_value(
                    parent_id="remote_store.google",
                    key=key,
                    option=options[key],
                )
                data_dict[key] = value
            self.window.core.remote_store.google.items[self.current].from_dict(data_dict)

        if persist:
            self.window.update_status(trans('status.sending'))
            QApplication.processEvents()
            if self.current is not None:
                # No remote patch endpoint; we save locally and fetch remote for status
                store = self.window.core.remote_store.google.update(
                    self.window.core.remote_store.google.items[self.current]
                )
                if store is None:
                    self.window.update_status(trans('status.error'))
                    self.window.ui.dialogs.alert("Failed to save File Search store")
                    return

            self.update()
            self.window.update_status(trans("info.settings.saved"))
            self.restore_selection()
            self.update_files_list()

    def reload_items(self):
        """Reload list items"""
        items = self.window.core.remote_store.google.items
        self.window.remote_store_google.update_list("remote_store.google.list", items)
        self.restore_selection()

    def restore_selection(self):
        """Restore selection"""
        if self.current is not None:
            idx = self.get_tab_by_id(self.current)
            if idx is not None:
                self.set_by_tab(idx)

    def select(self, idx: int):
        """Select store by index"""
        self.save(persist=False)
        self.current = self.get_by_tab_idx(idx)
        self.init()
        self.update_files_list()

    def new(self, name = "", force: bool = False):
        """
        Create new File Search store

        :param name: store name
        :param force: force create without confirmation
        """
        if not force:
            self.window.ui.dialog['create'].id = 'remote_store.google.new'
            self.window.ui.dialog['create'].input.setText("New file search store")
            self.window.ui.dialog['create'].current = "New file search store"
            self.window.ui.dialog['create'].show()
            return

        self.window.ui.dialog['create'].close()
        self.window.update_status(trans('status.sending'))
        QApplication.processEvents()

        store = self.window.core.remote_store.google.create(name)
        if store is None:
            self.window.update_status(trans('status.error'))
            self.window.ui.dialogs.alert("Failed to create new File Search store")
            return

        self.window.update_status(trans('status.finished'))

        self.window.core.remote_store.google.update(store)
        self.update()

        self.current = store.id
        idx = self.get_tab_by_id(self.current)
        self.set_by_tab(idx)
        self.init()
        self.restore_selection()
        self.refresh_by_store_id(store.id)
        self.update_files_list()

    def delete_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Delete store(s) by index

        :param idx: index or list of indexes
        :param force: force confirm
        """
        store_ids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            store_id = self.get_by_tab_idx(i)
            if store_id is not None:
                store_ids.append(store_id)
        self.delete(store_ids, force=force)

    def delete(self, store_id: Optional[Union[str, list]] = None, force: bool = False):
        """
        Delete store(s) by ID

        :param store_id: id or list
        :param force: force confirm
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type="remote_store.google.delete",
                id=store_id,
                msg=trans("dialog.remote_store.delete.confirm"),
            )
            return

        if store_id is None:
            self.window.ui.dialogs.alert("Please select File Search store first.")
            return

        self.window.update_status(trans('status.sending'))
        updated = False
        QApplication.processEvents()
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            if self.current == sid:
                self.current = None
            try:
                print("Deleting store: {}".format(sid))
                if self.window.core.remote_store.google.delete(sid):
                    self.window.controller.assistant.batch.remove_store_from_assistants(sid)
                    self.window.update_status(trans('status.deleted'))
                    self.window.core.remote_store.google.save()
                    updated = True
                else:
                    self.window.update_status(trans('status.error'))
            except Exception as e:
                self.window.update_status(trans('status.error'))
                self.window.ui.dialogs.alert(e)
        if updated:
            self.window.controller.assistant.files.update()
            self.update()
            self.init()
            self.restore_selection()
            self.update_files_list()

    def set_by_tab(self, idx: int):
        """Set current by list index"""
        store_idx = 0
        for id in self.window.core.remote_store.google.get_ids():
            if self.window.core.remote_store.google.is_hidden(id):
                continue
            if store_idx == idx:
                self.current = id
                break
            store_idx += 1
        current = self.window.ui.models['remote_store.google.list'].index(idx, 0)
        self.window.ui.nodes['remote_store.google.list'].setCurrentIndex(current)

    def set_tab_by_id(self, store_id: str):
        """Set current list to id"""
        idx = self.get_tab_idx(store_id)
        current = self.window.ui.models['remote_store.google.list'].index(idx, 0)
        self.window.ui.nodes['remote_store.google.list'].setCurrentIndex(current)

    def get_tab_idx(self, store_id: str) -> int:
        """Get list index by id"""
        store_idx = None
        i = 0
        for id in self.window.core.remote_store.google.get_ids():
            if self.window.core.remote_store.google.is_hidden(id):
                continue
            if id == store_id:
                store_idx = i
                break
            i += 1
        return store_idx

    def get_tab_by_id(self, store_id: str) -> int:
        """Get list index by id"""
        idx = None
        i = 0
        for id in self.window.core.remote_store.google.get_ids():
            if self.window.core.remote_store.google.is_hidden(id):
                continue
            if id == store_id:
                idx = i
                break
            i += 1
        return idx

    def get_by_tab_idx(self, idx: int) -> Optional[str]:
        """Get id by list index"""
        store_idx = 0
        for id in self.window.core.remote_store.google.get_ids():
            if self.window.core.remote_store.google.is_hidden(id):
                continue
            if store_idx == idx:
                return id
            store_idx += 1
        return None

    def get_first_visible(self) -> Optional[str]:
        """Get first visible store id"""
        for id in self.window.core.remote_store.google.get_ids():
            if not self.window.core.remote_store.google.is_hidden(id):
                return id
        return None

    def open_by_idx(self, idx: int):
        store = self.window.core.remote_store.google.get_by_idx(idx)
        if store is None:
            return
        self.current = store
        self.open(force=True)

    def update(self):
        """Update editor"""
        self.reload_items()
        self.window.controller.assistant.editor.update_store_list()
        self.update_files_list()

    def set_hide_thread(self, state: bool):
        """Toggle show thread stores"""
        self.window.core.config.set("remote_store.google.hide_threads", state)
        self.update()

    # ==================== Files (Documents) ====================

    def update_files_list(self):
        """
        Update files list (documents) for the current store from local DB
        """
        model_id = 'remote_store.google.files.list'
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

        files_db = self.window.core.remote_store.google.files
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
            size_val = data.get('size')

            size_txt = ""
            try:
                if size_val:
                    size_txt = self.window.core.filesystem.sizeof_fmt(int(size_val))
            except Exception:
                pass

            extra = []
            if size_txt:
                extra.append(size_txt)
            label = name
            if extra:
                label += " ({})".format(", ".join(extra))

            item = QStandardItem(label)
            item.setEditable(False)
            item.setData(file_id, Qt.UserRole)
            model.setItem(i, 0, item)
            self._files_row_to_id.append(data['file_id'] if 'file_id' in data else file_id)
            i += 1

    def delete_file_by_idx(self, idx: int, force: bool = False):
        """
        Delete a single document from the current store.

        :param idx: row index
        :param force: skip confirm
        """
        if self.current is None:
            self.window.ui.dialogs.alert("Please select File Search store first.")
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.file.delete',
                id=idx,
                msg=trans('confirm.remote_store.file.delete'),
            )
            return

        model_id = 'remote_store.google.files.list'
        if model_id not in self.window.ui.models:
            return
        if idx < 0 or idx >= len(self._files_row_to_id):
            return

        file_id = self._files_row_to_id[idx]
        if not file_id:
            return

        self.window.update_status(trans('status.sending'))
        QApplication.processEvents()

        try:
            api = self.window.core.api.google.store
            removed = False

            if hasattr(api, 'remove_store_file'):
                try:
                    api.remove_store_file(self.current, file_id)
                    removed = True
                except Exception as e:
                    self.window.core.debug.log(e)

            if not removed and hasattr(api, 'delete_store_file'):
                try:
                    api.delete_store_file(self.current, file_id)
                    removed = True
                except Exception as e:
                    self.window.core.debug.log(e)

            if not removed:
                raise RuntimeError("Remove file API not available.")

            try:
                self.window.core.remote_store.google.files.delete_by_file_id(file_id)
            except Exception as e:
                self.window.core.debug.log(e)

            try:
                self.window.ui.models[model_id].removeRow(idx)
                try:
                    del self._files_row_to_id[idx]
                except Exception:
                    pass
            except Exception:
                pass

            # Ensure the list panel is in sync immediately
            try:
                self.update_files_list()
            except Exception:
                pass

            try:
                self.window.update_status("Refreshing status...")
                QTimer.singleShot(1000, lambda: self.window.controller.remote_store.google.refresh_status())
            except Exception as e:
                self.window.core.debug.log(e)

            self.window.update_status(trans('status.deleted'))

        except Exception as e:
            self.window.update_status(trans('status.error'))
            self.window.ui.dialogs.alert("Failed to delete file: {}".format(e))
            self.window.core.debug.log(e)
            self.update_files_list()