#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 12:48:00                  #
# ================================================== #

import datetime
import json
from typing import Optional, Tuple, List, Dict, Any

from packaging.version import Version

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.core.index.base import BaseProvider
from pygpt_net.provider.core.index.json_file import JsonFileProvider
from pygpt_net.provider.core.index.db_sqlite import DbSqliteProvider
from pygpt_net.provider.vector_stores import Storage
from pygpt_net.utils import trans

from .indexing import Indexing
from .llm import Llm
from .chat import Chat
from .completion import Completion
from .metadata import Metadata
from .ui import UI
from .project import Project

from .types.ctx import Ctx
from .types.external import External
from .types.files import Files


class Idx:
    def __init__(self, window=None):
        """
        Indexer core

        :param window: Window instance
        """
        self.window = window
        self.indexing = Indexing(window)
        self.llm = Llm(window)
        self.storage = Storage(window)
        self.chat = Chat(window, self.storage)
        self.completion = Completion(window)
        self.metadata = Metadata(window)
        self.ui = UI(window)

        self.providers = {
            "json_file": JsonFileProvider(window),  # only for patching
            "db_sqlite": DbSqliteProvider(window),
        }
        self.provider = "db_sqlite"
        self.items = {}
        self.initialized = False

        # internal types
        self.ctx = Ctx(window, self.get_provider())
        self.external = External(window, self.get_provider())
        self.files = Files(window, self.get_provider())
        self.project = Project(window, self.get_provider())

    def install(self):
        """Install provider data"""
        self.get_provider().install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if success
        """
        return self.get_provider().patch(app_version)

    def init(self):
        """Initialize indexes"""
        if not self.initialized:
            self.load()
            self.initialized = True

    def is_valid(self, idx: str = None) -> bool:
        """
        Check if index is valid

        :param idx: index name
        :return: True if index is valid
        """
        if idx and idx != "_":
            if self.project.is_virtual(idx):
                return self.project.get_current_group_id() is not None
            return self.has(idx)
        return False

    def get_current_store(self) -> str:
        """
        Get current vector store name/ID

        :return: vector store name
        """
        return self.window.core.config.get('llama.idx.storage')

    def get_provider(self) -> BaseProvider:
        """
        Get provider instance

        :return: provider instance
        """
        return self.providers.get(self.provider)

    def resolve_idx(self, idx: Optional[str], group_id: Optional[int] = None) -> Optional[str]:
        """Resolve runtime virtual index IDs to physical storage IDs."""
        return self.project.resolve(idx, group_id)

    def get_current_project_idx(self, virtual: bool = False) -> Optional[str]:
        """Return current project's virtual or physical index ID."""
        group_id = self.project.get_current_group_id()
        if group_id is None:
            return None
        return self.project.VIRTUAL_ID if virtual else self.project.get_idx_id(group_id)

    def get_file_index_status(self, path: str) -> dict:
        """Lazy per-file index status for the Files explorer."""
        file_id = self.files.get_id(path)
        rows = self.files.get_status(self.get_current_store(), file_id)
        if not rows:
            return {'indexed': False}
        current_project = self.get_current_project_idx(virtual=False)
        timestamps = {}
        last_index_at = 0
        for row in rows:
            idx = row.get('idx')
            if not idx:
                continue
            ts = int(row.get('updated_ts') or 0)
            timestamps[idx] = max(timestamps.get(idx, 0), ts)
            last_index_at = max(last_index_at, ts)
        project_ids = [idx for idx in timestamps if self.project.is_project_idx(idx)]
        global_ids = [idx for idx in timestamps if not self.project.is_project_idx(idx)]
        labels = sorted(global_ids, key=lambda x: timestamps.get(x, 0), reverse=True)
        if project_ids:
            if len(project_ids) == 1 and project_ids[0] == current_project:
                labels.append(trans('idx.current_project'))
            else:
                labels.append(trans('idx.projects.count').replace('{n}', str(len(project_ids))))
        return {
            'indexed': True,
            'indexed_in': labels,
            'last_index_at': last_index_at,
            'project_indexes': project_ids,
            'global_indexes': global_ids,
        }

    def store_index(self, idx: str = "base"):
        """Store (persist) index data."""
        idx = self.resolve_idx(idx)
        if idx is None:
            return
        self.storage.store(idx)

    def remove_index(
            self,
            idx: str = "base",
            truncate: bool = False,
            store_id: Optional[str] = None
    ) -> bool:
        """Remove/truncate an index and all local tracking rows."""
        idx = self.resolve_idx(idx)
        if idx is None:
            return False
        store = store_id or self.get_current_store()
        self.ctx.truncate(store, idx)
        self.files.truncate(store, idx)
        self.external.truncate(store, idx)
        self.window.core.ctx.idx.truncate_indexed(store, idx)
        try:
            if store_id is None:
                exists = self.storage.exists(idx)
            else:
                exists = self.storage.exists(idx, store_id=store)
        except Exception:
            exists = False
        if not exists:
            return True
        if store_id is None:
            return self.storage.truncate(idx) if truncate else self.storage.remove(idx)
        if truncate:
            return self.storage.truncate(idx, store_id=store)
        return self.storage.remove(idx, store_id=store)

    def remove_context_data(
            self,
            meta_id: Optional[int] = None,
            group_id: Optional[int] = None
    ) -> int:
        """
        Remove conversation documents from vector stores and ``idx_ctx``.

        ``idx_ctx`` stores one current doc_id per context/index, while project
        indexing may have inserted multiple documents for the same context.
        Therefore cleanup merges both sources of truth: ``ctx_meta.indexes_json``
        (all known doc IDs) and ``idx_ctx`` (tracking/orphan fallback).
        """
        provider = self.get_provider()
        rows = provider.get_ctx_records(meta_id=meta_id, group_id=group_id)
        meta_rows = provider.get_ctx_meta_index_data(
            meta_id=meta_id, group_id=group_id
        )

        docs = set()
        for meta_row in meta_rows:
            raw = meta_row.get('indexes_json')
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                data = {}
            if not isinstance(data, dict):
                continue
            for store, indexes in data.items():
                if not isinstance(indexes, dict):
                    continue
                for idx, doc_data in indexes.items():
                    if isinstance(doc_data, dict):
                        doc_ids = list(doc_data.keys())
                    elif isinstance(doc_data, (list, tuple, set)):
                        doc_ids = list(doc_data)
                    elif doc_data:
                        doc_ids = [doc_data]
                    else:
                        doc_ids = []
                    for doc_id in doc_ids:
                        if store and idx and doc_id:
                            docs.add((str(store), str(idx), str(doc_id)))

        # Tracking rows are also used as a fallback for legacy/stale metadata
        # and allow cleanup of orphan idx_ctx rows whose ctx_meta is already gone.
        for row in rows:
            store = row.get('store')
            idx = row.get('idx')
            doc_id = row.get('doc_id')
            if store and idx and doc_id:
                docs.add((str(store), str(idx), str(doc_id)))

        for store, idx, doc_id in docs:
            try:
                if self.storage.exists(idx, store_id=store):
                    self.storage.remove_document(idx, doc_id, store_id=store)
            except Exception as e:
                # The vector store can already be gone or unavailable. DB
                # tracking still has to be cleaned to avoid permanent garbage.
                self.window.core.debug.log(e)

        for row in rows:
            row_id = int(row.get('id') or 0)
            if row_id:
                provider.remove_ctx_record(row_id)

        return len(docs)

    def index_files(
            self, idx: str = "base", path: Optional[str] = None,
            replace: Optional[bool] = None, recursive: Optional[bool] = None,
    ) -> Tuple[Dict, List[str]]:
        idx = self.resolve_idx(idx)
        if idx is None:
            return {}, ["Project index requested outside a project"]
        llm, embed_model = self.llm.get_service_context(stream=False)
        index = self.storage.get(id=idx, llm=llm, embed_model=embed_model)
        files, errors = self.indexing.index_files(
            idx=idx, index=index, path=path, replace=replace, recursive=recursive)
        if files:
            self.storage.store(id=idx, index=index)
            group_id = self.project.get_group_id_from_idx(idx)
            if group_id is not None:
                state = self.project.get(group_id) or {}
                self.project.touch(
                    group_id, state.get('last_meta', 0), state.get('last_item', 0)
                )
        if errors:
            self.log(f"Error: {errors}")
        return files, errors

    def index_db_by_meta_id(
            self, idx: str = "base", id: int = 0, from_ts: int = 0
    ) -> Tuple[int, List[str]]:
        idx = self.resolve_idx(idx)
        if idx is None:
            return 0, ["Project index requested outside a project"]
        llm, embed_model = self.llm.get_service_context(stream=False)
        index = self.storage.get(id=idx, llm=llm, embed_model=embed_model)
        num, errors = self.indexing.index_db_by_meta_id(
            idx=idx, index=index, id=id, from_ts=from_ts)
        if num > 0:
            self.storage.store(id=idx, index=index)

            # Contexts may also be indexed manually into a project-local index
            # (e.g. from the context-list RMB menu). Keep idx_proj aware of
            # that physical index without advancing the project's last_item
            # cursor, because a manual selection may cover only part of the
            # project. This keeps cleanup and last-update status correct while
            # preserving safe incremental project indexing.
            group_id = self.project.get_group_id_from_idx(idx)
            if group_id is not None:
                state = self.project.get(group_id) or {}
                self.project.touch(
                    group_id,
                    max(int(state.get('last_meta', 0) or 0), int(id or 0)),
                    int(state.get('last_item', 0) or 0),
                )
        if errors:
            self.log(f"Error: {errors}")
        return num, errors

    def index_db_from_updated_ts(
            self, idx: str = "base", from_ts: int = 0
    ) -> Tuple[int, List[str]]:
        idx = self.resolve_idx(idx)
        if idx is None:
            return 0, ["Project index requested outside a project"]
        llm, embed_model = self.llm.get_service_context(stream=False)
        index = self.storage.get(id=idx, llm=llm, embed_model=embed_model)
        num, errors = self.indexing.index_db_from_updated_ts(
            idx=idx, index=index, from_ts=from_ts)
        if num > 0:
            self.storage.store(id=idx, index=index)
        if errors:
            self.log(f"Error: {errors}")
        return num, errors

    def index_project(
            self, group_id: int, from_last: bool = True
    ) -> Tuple[int, List[str]]:
        """Index new conversation items for one project using idx_proj cursor."""
        idx = self.project.get_idx_id(group_id)
        state = self.project.get(group_id)
        last_item = int(state.get('last_item', 0)) if state and from_last else 0
        if last_item > 0 and not self.storage.exists(idx):
            last_item = 0
        if not from_last:
            if self.storage.exists(idx):
                self.remove_index(idx, truncate=True)
            # A full rebuild starts a new cursor even when the project is empty.
            self.project.remove_state(group_id)
            state = None
            last_item = 0
        llm, embed_model = self.llm.get_service_context(stream=False)
        index = self.storage.get(id=idx, llm=llm, embed_model=embed_model)
        n, errors, last_meta, max_item = self.indexing.index_db_project(
            idx=idx, index=index, group_id=group_id, last_item=last_item)
        if n > 0:
            self.storage.store(id=idx, index=index)
            self.project.touch(group_id, last_meta, max_item)
        elif state is None:
            # Track an intentionally empty project index as well; this makes
            # later truncate/delete operations deterministic.
            self.project.ensure(group_id)
        if errors:
            self.log(f"Error: {errors}")
        return n, errors

    def duplicate_project_index(
            self, source_group_id: int, target_group_id: int
    ) -> Tuple[int, List[str]]:
        """Rebuild a duplicated project's index and copy its tracked file inputs."""
        source_group_id = int(source_group_id)
        target_group_id = int(target_group_id)
        source_idx = self.project.get_idx_id(source_group_id)
        source_state = self.project.get(source_group_id)
        if source_state is None and not self.storage.exists(source_idx):
            return 0, []

        store_id = self.get_current_store()
        source_files = self.get_provider().get_files_by_index(store_id, source_idx)
        num, errors = self.index_project(target_group_id, from_last=False)
        target_idx = self.project.get_idx_id(target_group_id)
        for path in source_files:
            indexed, file_errors = self.index_files(
                target_idx, path=path, replace=False, recursive=False
            )
            num += len(indexed)
            errors.extend(file_errors)
        return num, errors

    def truncate_project(self, group_id: int) -> bool:
        idx = self.project.get_idx_id(group_id)
        ok = True
        stores = set(self.get_provider().get_index_stores(idx))
        stores.add(self.get_current_store())
        try:
            for store_id in [store for store in stores if store]:
                try:
                    ok = self.remove_index(idx, truncate=True, store_id=store_id) and ok
                except Exception as e:
                    ok = False
                    self.window.core.debug.log(e)
            return ok
        finally:
            # Never leave a stale incremental cursor after a truncate attempt.
            self.project.remove_state(group_id)

    def truncate_projects(self) -> bool:
        ok = True
        handled = set()
        for state in list(self.project.all()):
            group_id = int(state.get('group_id'))
            handled.add(self.project.get_idx_id(group_id))
            try:
                ok = self.truncate_project(group_id) and ok
            except Exception as e:
                ok = False
                self.window.core.debug.log(e)
                self.project.remove_state(group_id)

        # Also clean project indexes created by file indexing before idx_proj
        # existed, as long as they are discoverable in index tracking tables.
        stores = set(self.storage.get_ids())
        stores.add(self.get_current_store())
        for store_id in [store for store in stores if store]:
            for idx in self.get_provider().get_index_ids(store_id):
                if self.project.is_project_idx(idx) and idx not in handled:
                    try:
                        ok = self.remove_index(
                            idx, truncate=True, store_id=store_id
                        ) and ok
                    except Exception as e:
                        ok = False
                        self.window.core.debug.log(e)
        self.get_provider().truncate_projects()
        return ok

    def index_urls(
            self, idx: str = "base", urls: Optional[List[str]] = None,
            type: str = "webpage", extra_args: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, List[str]]:
        idx = self.resolve_idx(idx)
        if idx is None:
            return 0, ["Project index requested outside a project"]
        llm, embed_model = self.llm.get_service_context(stream=False)
        index = self.storage.get(id=idx, llm=llm, embed_model=embed_model)
        n, errors = self.indexing.index_urls(
            idx=idx, index=index, urls=urls, type=type, extra_args=extra_args)
        if n > 0:
            self.storage.store(id=idx, index=index)
        if errors:
            self.log(f"Error: {errors}")
        return n, errors

    def index_web(
            self, idx: str = "base", type: str = "webpage",
            params: Optional[Dict[str, Any]] = None,
            config: Optional[Dict[str, Any]] = None, replace: Optional[bool] = None,
    ) -> Tuple[int, list]:
        idx = self.resolve_idx(idx)
        if idx is None:
            return 0, ["Project index requested outside a project"]
        self.indexing.update_loader_args(type, config)
        llm, embed_model = self.llm.get_service_context(stream=False)
        index = self.storage.get(id=idx, llm=llm, embed_model=embed_model)
        n, errors = self.indexing.index_url(
            idx=idx, index=index, url="", type=type, extra_args=params,
            is_tmp=False, replace=replace)
        if n > 0:
            self.storage.store(id=idx, index=index)
        if errors:
            self.log(f"Error: {errors}")
        return n, errors

    def get_idx_data(
            self,
            idx: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Get indexed files data

        :param idx: index name
        :return: indexed files data (idx -> items)
        """
        indexes = {}
        store_id = self.get_current_store()
        if idx is not None:
            if store_id in self.items and idx in self.items[store_id]:
                indexes[idx] = self.items[store_id][idx].items
        else:
            # all indexes
            if store_id in self.items:
                for idx in self.items[store_id]:
                    indexes[idx] = self.items[store_id][idx].items
        return indexes

    def get_by_idx(self, idx: int) -> Optional[str]:
        """
        Return idx by list index

        :param idx: idx on list
        :return: idx name
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            if idx < len(items):
                return items[idx]['id']

    def get_idx_by_name(self, name: str) -> Optional[int]:
        """
        Return idx on list by name

        :param name: idx name
        :return: idx on list
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            for idx, item in enumerate(items):
                if item['id'] == name:
                    return idx

    def get_default_idx(self) -> Optional[str]:
        """
        Return default idx

        :return: idx name
        """
        if len(self.items) > 0:
            return self.get_by_idx(0)

    def has(self, idx: str) -> bool:
        if self.project.is_virtual(idx):
            return self.project.get_current_group_id() is not None
        idx = self.resolve_idx(idx)
        if idx is None:
            return False
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            return True
        try:
            return self.storage.exists(idx)
        except Exception:
            return False

    def get(self, idx: str) -> Optional[IndexItem]:
        idx = self.resolve_idx(idx)
        store_id = self.get_current_store()
        if idx is not None and store_id in self.items and idx in self.items[store_id]:
            return self.items[store_id][idx]

    def get_all(self) -> Dict[str, IndexItem]:
        """
        Return all indexes in current store

        :return: all indexes
        """
        store_id = self.get_current_store()
        if store_id in self.items:
            return self.items[store_id]
        return {}

    def append(self, idx: str, files: Dict[str, str]):
        """Update indexed-file tracking without hydrating the full idx_file table."""
        idx = self.resolve_idx(idx)
        if idx is None:
            return
        store_id = self.get_current_store()
        if store_id not in self.items:
            self.items[store_id] = {}
        if idx not in self.items[store_id]:
            item = IndexItem(); item.id = idx; item.name = idx; item.store = store_id
            self.items[store_id][idx] = item
        for path, doc_id in files.items():
            file_id = self.files.get_id(path)
            ts = int(datetime.datetime.now().timestamp())
            record = self.files.get_record(store_id, idx, file_id)
            if record is None:
                self.files.append(store_id, idx, file_id, path, doc_id)
            else:
                self.files.update(record['id'], doc_id, ts)

    def remove_doc(self, idx: str, doc_id: str, store_id: Optional[str] = None):
        idx = self.resolve_idx(idx)
        if idx is None:
            return
        store = store_id or self.get_current_store()
        if store_id is None:
            exists = self.storage.exists(idx)
            removed = exists and self.storage.remove_document(idx, doc_id)
        else:
            exists = self.storage.exists(idx, store_id=store)
            removed = exists and self.storage.remove_document(
                idx, doc_id, store_id=store
            )
        if removed:
            self.log(f"Removed document from index: {idx} - {doc_id}")

    def remove_file(self, idx: str, file: str):
        idx = self.resolve_idx(idx)
        if idx is None:
            return
        store_id = self.get_current_store()
        file_id = self.files.get_id(file)
        record = self.files.get_record(store_id, idx, file_id)
        if record is None:
            return
        doc_id = record.get('doc_id')
        if doc_id and self.storage.exists(idx):
            self.storage.remove_document(id=idx, doc_id=doc_id)
        if doc_id:
            self.files.remove(store_id, idx, doc_id)

    def load(self):
        """Load only index identities; individual file rows are lazy-loaded."""
        self.items = {}
        for store_id in self.storage.get_ids():
            self.items[store_id] = {}
            for idx in self.get_provider().get_index_ids(store_id):
                item = IndexItem(); item.id = idx; item.name = idx; item.store = store_id
                self.items[store_id][idx] = item
        self.sync()

    def sync(self):
        """Sync idx items from config"""
        items = self.window.core.config.get('llama.idx.list')
        store_id = self.get_current_store()
        if items is not None:
            if store_id not in self.items:
                self.items[store_id] = {}
            for item in items:
                idx = item['id']
                if idx not in self.items[store_id]:
                    self.items[store_id][idx] = IndexItem()
                    self.items[store_id][idx].id = idx
                    self.items[store_id][idx].name = idx
                    self.items[store_id][idx].store = store_id
                else:
                    self.items[store_id][idx].id = idx
                    self.items[store_id][idx].name = idx

    def get_idx_ids(self) -> List[Dict[str, str]]:
        """
        Get list of indexes

        :return: list of indexes
        """
        ids = []
        data =  self.window.core.config.get('llama.idx.list')
        if data is not None:
            for item in data:
                name = item['name']
                if name is None or name == "":
                    name = item['id']
                ids.append({item['id']: name})
        return ids

    def clear(self, idx: str):
        idx = self.resolve_idx(idx)
        if idx is None:
            return
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            self.items[store_id][idx].items = {}
        self.get_provider().truncate(store_id, idx)

    def get_counters(self, type: str) -> Dict[str, Dict[str, int]]:
        """
        Get counters (stats, count items by type [file, ctx, external])

        :param type: type of counter (file, ctx, external)
        :return: dict of counters: [store][idx] -> count
        """
        return self.get_provider().get_counters(type)

    def get_version(self) -> str:
        """
        Get provider config version

        :return: provider config version
        """
        return self.get_provider().get_version()

    def log(self, msg: str):
        """
        Log info message

        :param msg: message
        """
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print(f"[LlamaIndex] {msg}")
        self.window.idx_logger_message.emit(msg)
