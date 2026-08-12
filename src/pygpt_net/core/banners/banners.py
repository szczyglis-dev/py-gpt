#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 14:30:00                  #
# ================================================== #

import hashlib
import json
import os
import re
import ssl
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class Banners(QObject):
    """Loads banner configuration and images without blocking the UI thread."""

    loaded = Signal(object)

    DEFAULT_API_URL = "https://pygpt.net/api/banners.json"

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self._loading = False
        self._worker = None

    def get_default_path(self) -> str:
        """Return the bundled default banner path."""
        return os.path.join(
            self.window.core.config.get_app_path(),
            "data",
            "default.png",
        )

    def run_load(self):
        """Start banner synchronization in the global thread pool."""
        if self._loading or self.window is None or self.window.is_closing:
            return

        self._ensure_config()
        config = self.window.core.config
        app_path = config.get_app_path()
        user_tmp_path = config.get_user_dir("tmp")
        api_url = str(config.get("app_banners_api_url", self.DEFAULT_API_URL) or "").strip()

        self._loading = True
        worker = BannersWorker(
            api_url=api_url,
            app_path=app_path,
            user_tmp_path=user_tmp_path,
        )
        self._worker = worker
        worker.signals.loaded.connect(self._handle_loaded)
        worker.signals.finished.connect(self._handle_finished)
        self.window.threadpool.start(worker)

    def _ensure_config(self):
        """Append banner defaults to existing user configs, including same-version configs."""
        config = self.window.core.config
        changed = False

        # Banner dimensions are intentionally code-only. Remove legacy values
        # if they were written by an earlier development build.
        for key in ("app_banners_width", "app_banners_height"):
            if config.has(key):
                config.data.pop(key, None)
                changed = True

        if not config.has("app_banners_api_url"):
            value = config.get_base("app_banners_api_url")
            config.set(
                "app_banners_api_url",
                self.DEFAULT_API_URL if value is None else value,
            )
            changed = True

        if changed:
            config.save()

    @Slot(object)
    def _handle_loaded(self, result: Dict[str, Any]):
        source = result.get("source", "bundled")
        error = result.get("error")
        if error:
            pass
            # print(f"Banners: remote load failed ({error}); using bundled fallback.")
        else:
            pass
            # print(f"Banners: loaded from {source}.")
        self.loaded.emit(result.get("items", []))

    @Slot()
    def _handle_finished(self):
        self._loading = False
        self._worker = None


class BannersWorkerSignals(QObject):
    loaded = Signal(object)
    finished = Signal()


class BannersWorker(QRunnable):
    """Network/file worker used by :class:`Banners`."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) "
        "Gecko/20100101 Firefox/141.0"
    )
    JSON_MAX_BYTES = 2 * 1024 * 1024
    IMAGE_MAX_BYTES = 16 * 1024 * 1024
    DEFAULT_DURATION = 30.0

    CACHE_MANIFEST = ".pygpt_banners_cache.json"

    def __init__(self, api_url: str, app_path: str, user_tmp_path: str):
        super().__init__()
        self.api_url = api_url
        self.app_path = app_path
        self.user_tmp_path = user_tmp_path
        self.signals = BannersWorkerSignals()

    @Slot()
    def run(self):
        result = None
        remote_error = None
        try:
            if self.api_url:
                try:
                    items = self._load_remote()
                    result = {
                        "items": items,
                        "source": "remote",
                        "error": None,
                    }
                except Exception as e:
                    remote_error = str(e)

            if result is None:
                items = self._load_local()
                result = {
                    "items": items,
                    "source": "bundled",
                    "error": remote_error,
                }

            self.signals.loaded.emit(result)
        except Exception as e:
            # Even a broken/missing bundled JSON must not break application startup.
            self.signals.loaded.emit({
                "items": [],
                "source": "default",
                "error": remote_error or str(e),
            })
        finally:
            self.signals.finished.emit()

    def _load_remote(self) -> List[Dict[str, Any]]:
        data = self._fetch_json(self.api_url)
        raw_items = self._extract_items(data)

        cache_dir = self.user_tmp_path
        os.makedirs(cache_dir, exist_ok=True)

        # Keep banner cache directly in ./config/tmp, but never clear the whole
        # tmp directory because it is shared with other PyGPT subsystems. A small
        # manifest tracks only files owned by the banner loader.
        self._clear_previous_cache(cache_dir)

        if not raw_items:
            self._save_cache_manifest(cache_dir, [])
            return []

        items = []
        created_files = []
        try:
            for index, raw in enumerate(raw_items):
                item = self._normalize_item(raw, index)
                img = item.pop("img", "")
                item["path"] = None
                if img:
                    image_url = self._resolve_remote_image_url(img)
                    image_data = self._fetch_bytes(image_url, self.IMAGE_MAX_BYTES)
                    if not image_data:
                        raise ValueError(f"Empty banner image: {image_url}")

                    digest = hashlib.sha1(image_data).hexdigest()
                    extension = self._get_image_extension(img, image_data)
                    filename = f"{self._safe_id(item['id'])}_{digest}{extension}"
                    image_path = os.path.join(cache_dir, filename)
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    created_files.append(filename)
                    item["path"] = image_path
                items.append(item)

            self._save_cache_manifest(cache_dir, created_files)
            return items
        except Exception:
            # Do not leave a half-downloaded remote set behind when fallback is
            # selected for this startup.
            self._remove_cache_files(cache_dir, created_files)
            self._save_cache_manifest(cache_dir, [])
            raise

    def _manifest_path(self, cache_dir: str) -> str:
        return os.path.join(cache_dir, self.CACHE_MANIFEST)

    def _clear_previous_cache(self, cache_dir: str):
        manifest_path = self._manifest_path(cache_dir)
        files = []
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                files = [name for name in data if isinstance(name, str)]
        except (OSError, json.JSONDecodeError):
            pass

        self._remove_cache_files(cache_dir, files)
        try:
            os.remove(manifest_path)
        except OSError:
            pass

    @staticmethod
    def _remove_cache_files(cache_dir: str, files: List[str]):
        for name in files:
            # Manifest entries must be plain filenames; never allow it to escape
            # the shared tmp directory.
            if not name or os.path.basename(name) != name:
                continue
            try:
                os.remove(os.path.join(cache_dir, name))
            except OSError:
                pass

    def _save_cache_manifest(self, cache_dir: str, files: List[str]):
        manifest_path = self._manifest_path(cache_dir)
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(files, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _load_local(self) -> List[Dict[str, Any]]:
        config_path = os.path.join(self.app_path, "data", "banners.json")
        if not os.path.isfile(config_path):
            return []

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_items = self._extract_items(data)
        banner_dir = os.path.join(self.app_path, "data", "banners")
        items = []
        for index, raw in enumerate(raw_items):
            item = self._normalize_item(raw, index)
            img = item.pop("img", "")
            path = None
            if img:
                # Bundled assets are deliberately constrained to data/banners.
                # This also avoids path traversal from an accidentally edited JSON.
                candidate = os.path.join(banner_dir, os.path.basename(img))
                if os.path.isfile(candidate):
                    path = candidate
            item["path"] = path
            items.append(item)
        return items

    def _fetch_json(self, url: str) -> Dict[str, Any]:
        raw = self._fetch_bytes(url, self.JSON_MAX_BYTES, accept="application/json,text/plain,*/*")
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid banners JSON: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("Invalid banners JSON root; expected an object")
        return data

    def _fetch_bytes(self, url: str, max_bytes: int, accept: str = "image/avif,image/webp,image/png,image/gif,image/jpeg,*/*") -> bytes:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Unsupported banner URL scheme: {parsed.scheme or '(none)'}")

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        request = Request(url=url, headers=headers)
        context = ssl.create_default_context()
        context.check_hostname = True

        with urlopen(request, context=context, timeout=6) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    parsed_length = int(content_length)
                except (TypeError, ValueError):
                    parsed_length = None
                if parsed_length is not None and parsed_length > max_bytes:
                    raise ValueError(f"Banner response too large: {content_length} bytes")

            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError(f"Banner response exceeds {max_bytes} bytes")
            return data

    def _resolve_remote_image_url(self, img: str) -> str:
        url = urljoin(self.api_url, img)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Unsupported banner image URL: {img}")
        return url

    @staticmethod
    def _extract_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_items = data.get("items", [])
        if raw_items is None:
            return []
        if isinstance(raw_items, dict):
            raw_items = list(raw_items.values())
        if not isinstance(raw_items, list):
            raise ValueError("Invalid banners JSON; 'items' must be a list or object")

        items = []
        for item in raw_items:
            if isinstance(item, dict):
                items.append(item)
        return items

    def _normalize_item(self, raw: Dict[str, Any], index: int) -> Dict[str, Any]:
        item_id = str(raw.get("id") or f"banner_{index + 1}").strip()
        img = str(raw.get("img") or "").strip()
        tooltip = str(raw.get("tooltip") or "").strip()
        url = self._sanitize_click_url(str(raw.get("url") or "").strip())
        duration = self._parse_duration(raw.get("duration", self.DEFAULT_DURATION))
        return {
            "id": item_id,
            "img": img,
            "tooltip": tooltip,
            "url": url,
            "duration": duration,
        }

    @classmethod
    def _parse_duration(cls, value: Any) -> float:
        try:
            duration = float(value)
        except (TypeError, ValueError):
            duration = cls.DEFAULT_DURATION
        # Avoid a zero-duration tight rotation loop and unreasonable timer values.
        return min(max(duration, 1.0), 86400.0)

    @staticmethod
    def _sanitize_click_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ""
        return url

    @staticmethod
    def _safe_id(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
        return value[:80] or "banner"

    @staticmethod
    def _get_image_extension(img: str, data: bytes = b"") -> str:
        # Prefer content sniffing so animated GIFs still work for CDN URLs
        # without a useful filename extension.
        if data.startswith((b"GIF87a", b"GIF89a")):
            return ".gif"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if data.startswith(b"BM"):
            return ".bmp"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ".webp"

        suffix = Path(urlparse(img).path).suffix.lower()
        allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        return suffix if suffix in allowed else ".img"
