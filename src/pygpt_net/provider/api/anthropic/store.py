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
import mimetypes
import time
from typing import Optional, List, Dict, Any

from .worker.importer import Importer


class Store:
    """
    Anthropic Files API wrapper.
    """

    # Files API is in beta and requires this header, per official docs
    # https://docs.anthropic.com/en/docs/build-with-claude/files
    BETA_HEADER = ["files-api-2025-04-14"]

    def __init__(self, window=None):
        """
        Anthropic Files API store wrapper

        :param window: Window instance
        """
        self.window = window
        self.importer = Importer(window)

    def get_client(self):
        """
        Get Anthropic client

        :return: anthropic.Anthropic
        """
        return self.window.core.api.anthropic.get_client()

    def log(self, msg: str, callback: Optional[callable] = None):
        """
        Log message

        :param msg: message to log
        :param callback: callback log function
        """
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
        """
        Retrieve file metadata by ID using the SDK method names present in the installed version.
        Prefer 'retrieve', fallback to 'get' only if available to avoid attribute errors.
        """
        client = self.get_client()
        files_api = client.beta.files
        if hasattr(files_api, "retrieve"):
            return files_api.retrieve(file_id, betas=self.BETA_HEADER)
        if hasattr(files_api, "get"):
            return files_api.get(file_id, betas=self.BETA_HEADER)
        raise AttributeError("Anthropic Files API client does not expose 'retrieve' or 'get' for file metadata.")

    def upload(self, path: str):
        """
        Upload file to Anthropic Files API.

        Per SDK guidance, the Python client supports passing a PathLike, raw bytes,
        or a (filename, contents, media_type) tuple. Using the tuple form ensures the
        correct filename and MIME type are sent in multipart/form-data.

        :param path: file path
        :return: file object or None
        """
        client = self.get_client()
        if not os.path.exists(path):
            return None

        filename = os.path.basename(path)
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        file_part = (filename, data, mime_type)

        files_api = client.beta.files

        try:
            return files_api.upload(file=file_part, betas=self.BETA_HEADER)
        except Exception:
            if hasattr(files_api, "create"):
                return files_api.create(file=file_part, betas=self.BETA_HEADER)
            raise

    def delete_file(self, file_id: str) -> Optional[str]:
        """
        Delete a file by ID. Returns the file_id on success.
        """
        client = self.get_client()
        res = client.beta.files.delete(file_id, betas=self.BETA_HEADER)
        if res is not None:
            return file_id

    def download(self, file_id: str, path: str) -> bool:
        """
        Download a file content to a local path.

        :param file_id: Anthropic Files API file id
        :param path: target file path
        :return: True on success
        """
        client = self.get_client()
        try:
            # SDK returns raw bytes for file content
            data = client.beta.files.content(file_id, betas=self.BETA_HEADER)
        except Exception:
            data = None

        if data is None:
            return False

        try:
            if hasattr(data, "read"):
                content = data.read()
            else:
                content = data if isinstance(data, (bytes, bytearray)) else bytes(data)
            with open(path, "wb") as f:
                f.write(content)
            return True
        except Exception:
            return False

    def download_to_dir(self, file_id: str, prefer_name: Optional[str] = None) -> Optional[str]:
        """
        Download a file by ID into configured download directory.

        :param file_id: Anthropic Files API file id
        :param prefer_name: optional filename preference
        :return: saved file path or None
        """
        dir_path = self._download_dir()
        filename = None

        if prefer_name:
            filename = os.path.basename(prefer_name)

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
            else:
                filename = file_id

        if not os.path.splitext(filename)[1] and meta is not None:
            try:
                mime = getattr(meta, "mime_type", None)
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
        """
        Return a list of file IDs. Falls back to filename only if id is missing.
        """
        client = self.get_client()
        items: List[str] = []
        pager = client.beta.files.list(limit=limit, betas=self.BETA_HEADER)

        data = getattr(pager, "data", None)
        if data is None:
            data = pager

        for f in data:
            fid = getattr(f, "id", None) or getattr(f, "filename", None)
            if fid and fid not in items:
                items.append(fid)
        return items

    def remove_files(self, callback: Optional[callable] = None) -> int:
        """
        Remove all files from remote storage. Returns number of successfully removed files.
        """
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
        """
        Remove a single file by ID. Raises on errors to allow upstream handling.
        """
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
        Import all files from Anthropic Files API into local DB.

        :param callback: log callback
        :return: number of imported files
        """
        client = self.get_client()
        total = 0
        pager = client.beta.files.list(limit=1000, betas=self.BETA_HEADER)

        data = getattr(pager, "data", None)
        if data is None:
            data = pager

        for f in data:
            try:
                self.window.core.remote_store.anthropic.files.insert("files", f)
                total += 1
            except Exception as e:
                self.log("Error importing file {}: {}".format(getattr(f, "id", "?"), e), callback)
        return total

    def get_files_stats(self) -> Dict[str, Any]:
        """
        Compute files stats (count + total bytes).
        """
        client = self.get_client()
        count = 0
        total_bytes = 0
        pager = client.beta.files.list(limit=1000, betas=self.BETA_HEADER)

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