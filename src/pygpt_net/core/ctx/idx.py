#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import time
from typing import Optional

from pygpt_net.item.ctx import CtxMeta
from pygpt_net.provider.core.ctx.base import BaseProvider


class Idx:
    def __init__(self, window=None):
        """
        Context indexing helpers core

        :param window: Window instance
        """
        self.window = window

    def get_provider(self) -> BaseProvider:
        """
        Get index config storage provider instance

        :return: provider instance
        """
        return self.window.core.ctx.get_provider()

    def set_meta_indexed_by_id(
            self,
            id: int,
            doc_id: str,
            ts: int
    ) -> bool:
        """
        Update ctx meta indexed timestamp

        :param id: ctx meta ID
        :param doc_id: document ID
        :param ts: timestamp
        :return: True if updated
        """
        return self.get_provider().set_meta_indexed_by_id(id, ts)

    def update_meta_indexed_by_id(
            self,
            id: int,
            doc_id: str
    ) -> bool:
        """
        Update ctx meta indexed timestamp

        :param id: ctx meta ID
        :param doc_id: document ID
        :return: True if updated
        """
        return self.get_provider().update_meta_indexed_by_id(id)

    def update_meta_indexed_to_ts(self, ts: int) -> bool:
        """
        Update ctx meta updated timestamp

        :param ts: timestamp to update to
        :return: True if updated
        """
        return self.get_provider().update_meta_indexed_to_ts(ts)

    def clear_meta_indexed_by_id(self, id: int) -> bool:
        """
        Clear ctx meta indexed timestamp

        :param id: ctx meta ID
        :return: True if updated
        """
        return self.get_provider().clear_meta_indexed_by_id(id)

    def clear_meta_indexed_all(self) -> bool:
        """
        Clear all ctx meta indexed timestamps

        :return: True if cleared
        """
        return self.get_provider().clear_meta_indexed_all()

    def remove_meta_from_indexed(
            self,
            store: str,
            id: int,
            idx: str,
            doc_id: Optional[str] = None
    ) -> bool:
        """
        Remove ctx meta from indexed storage and tracking.

        Project-only context indexing does not necessarily set indexed_ts, so
        cleanup must be based on idx_ctx/indexes_json rather than that cursor.
        """
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is None:
            meta = self.get_provider().get_meta_by_id(id)

        doc_ids = []
        if doc_id:
            doc_ids.append(doc_id)
        if meta is not None and isinstance(meta.indexes, dict):
            if store in meta.indexes and idx in meta.indexes[store]:
                value = meta.indexes[store][idx]
                if isinstance(value, dict):
                    doc_ids.extend(value.keys())
                elif isinstance(value, (list, tuple, set)):
                    doc_ids.extend(value)

        # Fallback to idx_ctx if indexes_json is stale or incomplete.
        if not doc_ids:
            try:
                tracked = self.window.core.idx.ctx.get_doc_id(store, idx, id)
                if tracked:
                    doc_ids.append(tracked)
            except Exception:
                pass

        for tracked_doc_id in list(dict.fromkeys(doc_ids)):
            try:
                self.window.core.idx.remove_doc(
                    idx, tracked_doc_id, store_id=store
                )
            except Exception as e:
                self.window.core.debug.log(e)

        # Remove from idx tracking DB even when vector storage is already gone.
        self.window.core.idx.ctx.remove(store, idx, id)

        if meta is None:
            return True

        self.remove_idx_data_from_meta(meta, store, idx)
        self.get_provider().update_meta_indexes_by_id(id, meta)
        if not meta.indexes:
            self.clear_meta_indexed_by_id(id)
            self.window.core.ctx.update_indexed_ts_by_id(id, 0)
        return True

    def set_meta_as_indexed(
            self,
            id: int,
            idx: str,
            doc_id: str,
            update_timestamp: bool = True
    ) -> bool:
        """
        Set ctx meta as indexed

        :param id: ctx meta ID
        :param idx: index name
        :param doc_id: document ID
        :return: True if updated
        """
        # get meta
        meta = self.window.core.ctx.get_meta_by_id(id)
        if meta is None:
            return False

        ts = int(time.time())
        store = self.window.core.idx.get_current_store()

        # add to index db
        if not self.window.core.idx.ctx.exists(store, idx, id):
            self.window.core.idx.ctx.append(
                store_id=store,  # current store
                idx=idx,  # index name
                meta_id=id,  # ctx meta id
                doc_id=doc_id,  # document id
            )
        else:
            # update document id in index db if already indexed, by meta id
            self.window.core.idx.ctx.update(
                store_id=store,
                idx=idx,
                meta_id=id,  # ctx meta id
                doc_id=doc_id,  # document id
            )

        # Project indexes have their own incremental cursor in idx_proj; do not
        # move the global ctx_meta.indexed_ts cursor when indexing a project.
        if update_timestamp:
            self.get_provider().set_meta_indexed_by_id(id, ts)
            self.window.core.ctx.update_indexed_ts_by_id(id, ts)

        # append index data to ctx meta object
        self.store_idx_data_in_meta(meta, store, idx, doc_id)

        # update ctx meta indexes data in db
        self.get_provider().update_meta_indexes_by_id(id, meta)
        return True

    def store_idx_data_in_meta(
            self,
            ctx: CtxMeta,
            store_id: str,
            idx: str,
            doc_id: str
    ):
        """
        Append index data to ctx meta object

        :param ctx: ctx meta
        :param store_id: store id
        :param idx: index name
        :param doc_id: document id
        """
        current = ctx.indexes
        if not isinstance(current, dict):
            current = {}
        if store_id not in current:
            current[store_id] = {}
        if idx not in current[store_id]:
            current[store_id][idx] = {}
        current[store_id][idx][doc_id] = int(time.time())  # key = doc_id, value = last indexed timestamp
        ctx.indexes = current  # update ctx meta object

    def remove_idx_data_from_meta(
            self,
            ctx: CtxMeta,
            store_id: str,
            idx: str,
            doc_id: Optional[str] = None
    ):
        """
        Remove index data from ctx meta object

        :param ctx: ctx meta
        :param store_id: store id
        :param idx: index name
        :param doc_id: document id
        """
        current = ctx.indexes
        if not isinstance(current, dict):
            current = {}
        if store_id not in current:
            current[store_id] = {}
        if idx not in current[store_id]:
            current[store_id][idx] = {}

        # remove doc_id from index or all docs if doc_id is None
        if doc_id is None:
            del current[store_id][idx]
        else:
            if doc_id in current[store_id][idx]:
                current[store_id][idx].remove(doc_id)
            # remove empty index
            if not current[store_id][idx]:
                del current[store_id][idx]

        # remove empty store (if no indexes left)
        if not current[store_id]:
            del current[store_id]

        ctx.indexes = current  # update ctx meta object

    def truncate_indexed(
            self,
            store_id: Optional[str] = None,
            idx: Optional[str] = None
    ) -> bool:
        """
        Truncate ctx meta indexed timestamps and statuses

        :param store_id: store id (optional)
        :param idx: index name (optional)
        :return: True if truncated
        """
        metas = self.get_provider().get_meta_indexed()
        for meta_id in metas:
            meta = metas[meta_id]
            if store_id and idx:
                if store_id in meta.indexes and idx in meta.indexes[store_id]:
                    # remove index data from meta indexes
                    self.remove_idx_data_from_meta(meta, store_id, idx)

                    # update indexes in db
                    self.get_provider().update_meta_indexes_by_id(meta.id, meta)

                    # clear indexed timestamp if no indexes left
                    if not meta.indexes:
                        self.clear_meta_indexed_by_id(meta.id)
        return True
