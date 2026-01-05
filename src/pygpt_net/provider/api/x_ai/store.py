#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

import os
import time
import mimetypes
from typing import Optional, List, Dict, Any

from .worker.importer import Importer


class Store:
    """
    xAI Files API wrapper.
    """

    def __init__(self, window=None):
        """
        xAI Files API store wrapper

        :param window: Window instance
        """
        self.window = window
        self.importer = Importer(window)

    def get_client(self):
        """
        Get xAI client (xai_sdk.Client or OpenAI-compatible client)
        """
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

    # -----------------------------
    # Files service
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
        with open(path, "rb") as f:
            data = f.read()
        # Try xai_sdk first
        try:
            return client.files.upload(data, filename=os.path.basename(path))
        except Exception:
            # OpenAI-compatible path
            try:
                return client.files.create(file=open(path, "rb"), purpose="assistants")
            except Exception:
                # Another fallback
                return client.files.create(file=open(path, "rb"))

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
        # Preferred SDK call
        try:
            data = client.files.content(file_id)
        except Exception:
            data = None

        if data is None:
            # HTTP fallback for OpenAI-compatible endpoints
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

            if meta is not None:
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
        data = getattr(pager, "data", None)
        if data is None:
            data = pager
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
        Import all files into local DB.
        """
        client = self.get_client()
        total = 0
        try:
            pager = client.files.list(limit=1000)
        except Exception:
            pager = client.files.list()
        data = getattr(pager, "data", None)
        if data is None:
            data = pager
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
        data = getattr(pager, "data", None)
        if data is None:
            data = pager
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