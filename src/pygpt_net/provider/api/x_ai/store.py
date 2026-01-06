#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 06:00:00                  #
# ================================================== #

import os
import time
import mimetypes
from typing import Optional, List, Dict, Any

from pygpt_net.item.store import RemoteStoreItem
from .worker.importer import Importer


class Store:
    """
    xAI API wrapper.

    Notes:
    - Existing Files API methods are kept intact for backward compatibility.
    - New Collections API helpers are added with suffix "_collections".
      The xAI Importer and Core use only the Collections methods.
    """

    def __init__(self, window=None):
        """
        xAI API store wrapper

        :param window: Window instance
        """
        self.window = window
        self.importer = Importer(window)

    # -----------------------------
    # Common helpers
    # -----------------------------

    def get_client(self):
        """
        Get xAI client (xai_sdk.Client or OpenAI-compatible client).
        Requires management_api_key.
        """
        management_api_key = self.window.core.config.get("api_key_management_xai")
        if management_api_key:
            return self.window.core.api.xai.get_client(management_api_key=management_api_key)
        return self.window.core.api.xai.get_client()

    def log(self, msg: str, callback: Optional[callable] = None):
        if callback is not None:
            callback(msg)
        else:
            print(msg)

    def _download_dir(self) -> str:
        """
        Resolve target download directory (uses download.dir if set).
        """
        if self.window.core.config.has("download.dir") and self.window.core.config.get("download.dir") != "":
            dir_path = os.path.join(
                self.window.core.config.get_user_dir('data'),
                self.window.core.config.get("download.dir"),
            )
        else:
            dir_path = self.window.core.config.get_user_dir('data')
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _ensure_unique_path(self, dir_path: str, filename: str) -> str:
        """
        Ensure unique filename in dir, add timestamp prefix if exists.
        """
        path = os.path.join(dir_path, filename)
        if os.path.exists(path):
            prefix = time.strftime("%Y%m%d_%H%M%S_")
            path = os.path.join(dir_path, f"{prefix}{filename}")
        return path

    def _extract_list(self, obj: Any, prefer: Optional[List[str]] = None) -> List[Any]:
        """
        Extract list-like data from xAI SDK responses.

        Strategy:
        - Check well-known attributes in preferred order (e.g. 'collections', 'documents', 'data', 'items', 'results')
        - Accept dicts with those keys
        - Accept already-iterables (list/tuple)
        - Fallback to empty list
        """
        if obj is None:
            return []

        if isinstance(obj, (list, tuple)):
            return list(obj)

        attrs = prefer or []
        # Append common candidates, keeping stable priority
        for a in ['collections', 'documents', 'data', 'items', 'results']:
            if a not in attrs:
                attrs.append(a)

        for a in attrs:
            try:
                val = getattr(obj, a, None)
            except Exception:
                val = None
            if val is not None:
                if isinstance(val, (list, tuple)):
                    return list(val)
                try:
                    return list(val)  # handle iterables
                except TypeError:
                    pass

        if isinstance(obj, dict):
            for a in attrs:
                if a in obj and isinstance(obj[a], (list, tuple)):
                    return list(obj[a])
            # As last resort, try values
            try:
                return list(obj.values())
            except Exception:
                pass

        try:
            return list(obj)
        except TypeError:
            return []

    # -----------------------------
    # Files service (kept)
    # -----------------------------

    def get_file(self, file_id: str):
        client = self.get_client()
        # Try SDK variants
        if hasattr(client, "files"):
            try:
                return client.files.get(file_id)
            except Exception:
                try:
                    return client.files.retrieve(file_id)
                except Exception:
                    return client.files.info(file_id)

    def upload(self, path: str):
        """
        Upload file to xAI Files API.

        :param path: file path
        :return: file object or None
        """
        client = self.get_client()
        if not os.path.exists(path):
            return None

        # Prefer SDK upload helper supporting file path / bytes / file object
        try:
            return client.files.upload(path)
        except Exception:
            pass

        # Fallbacks
        with open(path, "rb") as f:
            data = f.read()
        try:
            return client.files.upload(data, filename=os.path.basename(path))
        except Exception:
            try:
                return client.files.upload(open(path, "rb"), filename=os.path.basename(path))
            except Exception:
                return None

    def delete_file(self, file_id: str) -> Optional[str]:
        client = self.get_client()
        res = None
        try:
            res = client.files.delete(file_id)
        except Exception:
            try:
                res = client.files.delete(id=file_id)
            except Exception:
                pass
        if res is not None:
            try:
                return getattr(res, "id", file_id)
            except Exception:
                return file_id

    def download(self, file_id: str, path: str) -> bool:
        """
        Download a file contents to a local path.

        :param file_id: xAI file id
        :param path: target path
        :return: True on success
        """
        client = self.get_client()
        data = None
        try:
            data = client.files.content(file_id)
        except Exception:
            data = None

        if data is None:
            try:
                content = client.files.content(file_id)
                data = content if isinstance(content, (bytes, bytearray)) else None
            except Exception:
                data = None

        if data is None:
            return False

        try:
            with open(path, "wb") as f:
                f.write(data if isinstance(data, (bytes, bytearray)) else bytes(data))
            return True
        except Exception:
            return False

    def download_to_dir(self, file_id: str, prefer_name: Optional[str] = None) -> Optional[str]:
        """
        Download a file by ID into configured download directory.

        :param file_id: xAI file id
        :param prefer_name: optional preferred filename
        :return: saved path or None
        """
        dir_path = self._download_dir()
        filename = None

        if prefer_name:
            filename = os.path.basename(prefer_name)

        meta = None
        if not filename:
            try:
                meta = self.get_file(file_id)
            except Exception:
                meta = None

        if meta is not None and not filename:
            for attr in ("filename", "name", "id"):
                try:
                    val = getattr(meta, attr, None)
                    if isinstance(val, str) and val:
                        filename = os.path.basename(val)
                        break
                except Exception:
                    pass

        if not filename:
            filename = file_id

        if not os.path.splitext(filename)[1] and meta is not None:
            try:
                mime = getattr(meta, "mime_type", None) or getattr(meta, "type", None)
                ext = mimetypes.guess_extension(mime or "") or ""
                if ext and not filename.endswith(ext):
                    filename = filename + ext
            except Exception:
                pass

        path = self._ensure_unique_path(dir_path, filename)
        if self.download(file_id, path):
            return path
        return None

    def get_files_ids(self, limit: int = 1000) -> List[str]:
        client = self.get_client()
        items = []
        try:
            pager = client.files.list(limit=limit)
        except Exception:
            pager = client.files.list()
        data = self._extract_list(pager, prefer=['data'])
        for f in data:
            fid = getattr(f, "id", None) or getattr(f, "name", None)
            if fid and fid not in items:
                items.append(fid)
        return items

    def remove_files(self, callback: Optional[callable] = None) -> int:
        num = 0
        files = self.get_files_ids()
        for file_id in files:
            self.log("Removing file: " + file_id, callback)
            try:
                res = self.delete_file(file_id)
                if res:
                    num += 1
            except Exception as e:
                msg = "Error removing file {}: {}".format(file_id, str(e))
                self.log(msg, callback)
        return num

    def remove_file(self, file_id: str, callback: Optional[callable] = None) -> bool:
        self.log("Removing file: " + file_id, callback)
        try:
            res = self.delete_file(file_id)
            return res is not None
        except Exception as e:
            msg = "Error removing file {}: {}".format(file_id, str(e))
            self.log(msg, callback)
            raise

    def import_files(self, callback: Optional[callable] = None) -> int:
        """
        Import all Files-API files into local DB (workspace-level).
        """
        client = self.get_client()
        total = 0
        try:
            pager = client.files.list(limit=1000)
        except Exception:
            pager = client.files.list()
        data = self._extract_list(pager, prefer=['data'])
        for f in data:
            try:
                self.window.core.remote_store.xai.files.insert("files", f)
                total += 1
            except Exception as e:
                self.log("Error importing file {}: {}".format(getattr(f, "id", "?"), e), callback)
        return total

    def get_files_stats(self) -> Dict[str, Any]:
        client = self.get_client()
        count = 0
        total_bytes = 0
        try:
            pager = client.files.list(limit=1000)
        except Exception:
            pager = client.files.list()
        data = self._extract_list(pager, prefer=['data'])
        for f in data:
            count += 1
            try:
                size = getattr(f, "size_bytes", None)
                if size is None and hasattr(f, "size"):
                    size = getattr(f, "size")
                total_bytes += int(size or 0)
            except Exception:
                pass
        return {"count": count, "total_bytes": total_bytes}

    # -----------------------------
    # Collections service (new)
    # -----------------------------

    # Collections: management

    def create_collection_collections(self, name: str):
        client = self.get_client()
        return client.collections.create(name=name)

    def update_collection_collections(self, id: str, name: Optional[str] = None):
        client = self.get_client()
        return client.collections.update(id, name=name) if name is not None else client.collections.get(id)

    def get_collection_collections(self, id: str):
        client = self.get_client()
        return client.collections.get(id)

    def remove_collection_collections(self, id: str):
        client = self.get_client()
        return client.collections.delete(collection_id=id)

    def get_collections_ids_collections(self, items: list, limit: int = 100, after: Optional[str] = None) -> list:
        client = self.get_client()
        cols = client.collections.list()
        data = self._extract_list(cols, prefer=['collections', 'data'])
        for c in data:
            cid = getattr(c, "collection_id", None) or (c.get("collection_id") if isinstance(c, dict) else None)
            if cid and cid not in items:
                items.append(cid)
        return items

    def import_collections_collections(
        self,
        items: Dict[str, RemoteStoreItem],
        callback: Optional[callable] = None
    ) -> Dict[str, RemoteStoreItem]:
        """
        Import Collections into RemoteStoreItem map.
        """
        client = self.get_client()
        cols = client.collections.list()
        data = self._extract_list(cols, prefer=['collections', 'data'])
        for c in data:
            cid = getattr(c, "collection_id", None) or (c.get("collection_id") if isinstance(c, dict) else None)
            if not cid:
                continue
            if cid not in items:
                items[cid] = RemoteStoreItem()
            name = getattr(c, "collection_name", None)
            if name is None and isinstance(c, dict):
                name = c.get("collection_name")
            name = name or ""
            items[cid].id = cid
            items[cid].name = name
            items[cid].file_ids = []
            items[cid].status = {
                "status": "ready",
                "remote_display_name": name,
            }
            items[cid].provider = "xai"
            status, _ = self.window.core.remote_store.xai.get_status_data(cid)
            self.window.core.remote_store.xai.append_status(items[cid], status)
            self.log("Imported collection: " + cid, callback)
        return items

    def remove_all_collections_collections(self, callback: Optional[callable] = None) -> int:
        """
        Delete all collections.
        """
        num = 0
        ids = self.get_collections_ids_collections([])
        for cid in ids:
            self.log("Removing collection: " + cid, callback)
            try:
                self.remove_collection_collections(cid)
                num += 1
            except Exception as e:
                self.log("Error removing collection {}: {}".format(cid, e), callback)
        return num

    # Collections: documents membership

    def add_file_to_collection_collections(self, collection_id: str, file_id: str):
        client = self.get_client()
        try:
            return client.collections.add_document(collection_id=collection_id, file_id=file_id)
        except Exception:
            return client.collections.add_existing_document(collection_id=collection_id, file_id=file_id)

    def delete_collection_file_collections(self, collection_id: str, file_id: str):
        client = self.get_client()
        return client.collections.remove_document(collection_id=collection_id, file_id=file_id)

    def remove_store_file(self, store_id: str, file_id: str) -> bool:
        """
        Unified hook used by UI: remove a file from a specific 'store' (collection in xAI).
        """
        try:
            res = self.delete_collection_file_collections(store_id, file_id)
            return res is not None
        except Exception:
            return False

    def list_collection_documents_raw_(self, collection_id: str, limit: int = 1000) -> List[Any]:
        """
        Internal: list documents of a collection with various SDK method shapes.
        """
        client = self.get_client()

        # Variant 1: simple list method
        try:
            docs = client.collections.list_documents(collection_id=collection_id, limit=limit)
            return self._extract_list(docs, prefer=['documents', 'data'])
        except Exception:
            pass

        # Variant 2: nested resource .documents.list(...)
        try:
            docs = client.collections.documents.list(collection_id=collection_id, limit=limit)
            return self._extract_list(docs, prefer=['documents', 'data'])
        except Exception:
            pass

        # Variant 3: object + list()
        try:
            docs_obj = client.collections.documents(collection_id)
            docs = docs_obj.list(limit=limit)
            return self._extract_list(docs, prefer=['documents', 'data'])
        except Exception:
            pass

        return []

    def get_collection_files_ids_collections(self, collection_id: str, items: list, limit: int = 1000) -> list:
        """
        Return document file IDs for a collection.
        """
        data = self.list_collection_documents_raw_(collection_id, limit=limit)
        for d in data:
            fid = d.file_metadata.file_id
            if fid and fid not in items:
                items.append(fid)
        return items

    def remove_from_collection_collections(self, collection_id: str, callback: Optional[callable] = None) -> int:
        """
        Remove all documents from a specific collection.
        """
        num = 0
        files = self.get_collection_files_ids_collections(collection_id, [])
        for file_id in files:
            self.log("Removing document from collection [{}]: {}".format(collection_id, file_id), callback)
            try:
                self.delete_collection_file_collections(collection_id, file_id)
                num += 1
            except Exception as e:
                self.log("Error removing document {} from collection {}: {}".format(file_id, collection_id, e), callback)
        return num

    def remove_from_collections_collections(self, callback: Optional[callable] = None) -> int:
        """
        Remove all documents from all collections.
        """
        num = 0
        col_ids = self.get_collections_ids_collections([])
        for cid in col_ids:
            num += self.remove_from_collection_collections(cid, callback=callback)
        return num

    # Collections: import / upload

    def import_collection_files_collections(
        self,
        collection_id: str,
        items: list,
        limit: int = 1000,
        callback: Optional[callable] = None
    ) -> list:
        """
        Import and get all collection document IDs.
        """
        docs = self.list_collection_documents_raw_(collection_id, limit=limit)
        for d in docs:
            try:
                fid = d.file_metadata.file_id
                if not fid:
                    continue
                if fid not in items:
                    items.append(fid)
                    data = self.get_file(fid)
                    self.window.core.remote_store.xai.files.insert(collection_id, data)
                    self.log("Imported file ID {} to collection {}".format(fid, collection_id), callback)
            except Exception as e:
                self.log("Error importing file {} to collection {}: {}".format(getattr(d, "id", "?"), collection_id, e), callback)
        return items

    def import_collections_files_collections(self, callback: Optional[callable] = None) -> int:
        """
        Import all documents for all collections into DB.
        """
        col_ids = self.get_collections_ids_collections([])
        total = 0
        for cid in col_ids:
            items = []
            try:
                items = self.import_collection_files_collections(cid, items, callback=callback)
            except Exception as e:
                self.log("Error importing collection {} files: {}".format(cid, e), callback)
            total += len(items)
        return total

    def upload_to_collection_collections(
        self,
        collection_id: str,
        path: str,
        fields: Optional[Dict[str, str]] = None
    ):
        """
        Upload a file and attach to a collection (single-step helper).
        """
        client = self.get_client()
        if not os.path.exists(path):
            return None

        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()

        return client.collections.upload_document(
            collection_id=collection_id,
            name=os.path.basename(path),
            data=data,
            # content_type=content_type,  # TODO: check if supported???
            fields=fields or None,
        )

    def get_collection_stats_collections(self, collection_id: str) -> Dict[str, Any]:
        """
        Compute simple stats for a collection: total docs and total bytes.
        """
        count = 0
        total_bytes = 0
        docs = self.list_collection_documents_raw_(collection_id, limit=1000)
        for d in docs:
            count += 1
            try:
                fid = getattr(d, "id", None) or getattr(d, "file_id", None)
                if not fid and isinstance(d, dict):
                    fid = d.get("id") or d.get("file_id")
                meta = self.get_file(fid) if fid else None
                size = None
                if meta is not None:
                    size = getattr(meta, "size_bytes", None)
                    if size is None and hasattr(meta, "size"):
                        size = getattr(meta, "size")
                total_bytes += int(size or 0)
            except Exception:
                pass
        return {"count": count, "total_bytes": total_bytes}