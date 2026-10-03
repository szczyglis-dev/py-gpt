#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
import json
import os
from datetime import datetime, timezone
from PySide6.QtCore import QUrl


class CanvasHistory:
    """Persist visited addresses and restore Canvas document navigation."""

    def __init__(self, runtime):
        self.runtime = runtime

    def path(self) -> str:
        """Return the persistent browser-history file for the active workdir/profile."""
        runtime = self.runtime
        return os.path.join(runtime.window.core.config.get_user_path(), runtime.BROWSER_HISTORY_FILE)

    def limit(self) -> int:
        """Return the configured persistent history limit with a safe clamp."""
        runtime = self.runtime
        try:
            value = int(runtime._opt("history_limit", 100) or 100)
        except (TypeError, ValueError):
            value = 100
        return max(1, min(value, 10000))

    def enabled(self) -> bool:
        runtime = self.runtime
        return bool(runtime._opt("store_history", True))

    @staticmethod
    def normalize_url(url: str) -> str:
        """Return an HTTP(S) URL eligible for persistent address history."""
        value = str(url or "").strip()
        if not value:
            return ""
        try:
            parsed = QUrl(value)
            if parsed.scheme().lower() not in ("http", "https"):
                return ""
        except Exception:
            return ""
        return value

    def load(self):
        """Load, sanitize, sort and trim persistent HTTP(S) address history."""
        runtime = self.runtime
        entries = []
        path = self.path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    raw = raw.get("entries", [])
                if isinstance(raw, list):
                    entries = raw
        except (OSError, ValueError, TypeError):
            entries = []

        cleaned = []
        for item in entries:
            if isinstance(item, str):
                url = self.normalize_url(item)
                timestamp = ""
            elif isinstance(item, dict):
                url = self.normalize_url(item.get("url", ""))
                timestamp = str(item.get("timestamp") or "")
                title = str(item.get("title") or "").strip()
            else:
                continue
            if not url:
                continue
            if isinstance(item, str):
                title = ""
            cleaned.append({"url": url, "timestamp": timestamp, "title": title})

        # ISO-8601 UTC timestamps sort lexicographically. Empty/malformed legacy
        # timestamps naturally fall to the end. De-duplicate after sorting so the
        # newest visit wins.
        cleaned.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
        unique = []
        seen = set()
        for item in cleaned:
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            unique.append(item)
            if len(unique) >= self.limit():
                break
        with runtime._browser_history_lock:
            runtime.browser_history = unique
        if os.path.exists(path) and entries != unique:
            self.save()
        self.notify()

    def save(self):
        """Persist the current address history atomically."""
        runtime = self.runtime
        path = self.path()
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        with runtime._browser_history_lock:
            payload = {
                "version": 1,
                "entries": list(runtime.browser_history[:self.limit()]),
            }
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp, path)
        except OSError:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

    def record(self, url: str, title: str = ""):
        """Move one visited HTTP(S) URL to the top and persist its timestamp/title."""
        runtime = self.runtime
        if runtime.runtime_root is not None:
            return runtime.runtime_root.history.record(url, title)
        if not self.enabled():
            return
        url = self.normalize_url(url)
        if not url:
            return
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        title = str(title or "").strip()
        limit = self.limit()
        with runtime._browser_history_lock:
            previous = next((item for item in runtime.browser_history if item.get("url") == url), None)
            if not title and previous is not None:
                title = str(previous.get("title") or "").strip()
            items = [item for item in runtime.browser_history if item.get("url") != url]
            items.insert(0, {"url": url, "timestamp": timestamp, "title": title})
            runtime.browser_history = items[:limit]
        self.save()
        self.notify()

    def update_title(self, url: str, title: str):
        """Update the last known title for an existing history URL without reordering it."""
        runtime = self.runtime
        if runtime.runtime_root is not None:
            return runtime.runtime_root.history.update_title(url, title)
        if not self.enabled():
            return
        url = self.normalize_url(url)
        title = str(title or "").strip()
        if not url or not title:
            return
        changed = False
        with runtime._browser_history_lock:
            for item in runtime.browser_history:
                if item.get("url") == url:
                    if item.get("title", "") != title:
                        item["title"] = title
                        changed = True
                    break
        if changed:
            self.save()
            self.notify()

    def entries(self) -> list:
        """Return persistent history entries in newest-first order for address UI."""
        runtime = self.runtime
        if runtime.runtime_root is not None:
            return runtime.runtime_root.history.entries()
        with runtime._browser_history_lock:
            return [dict(item) for item in runtime.browser_history if item.get("url")]

    def urls(self) -> list:
        """Return persistent history URLs in newest-first order."""
        runtime = self.runtime
        return [item.get("url", "") for item in self.entries()]

    def clear(self):
        """Delete persistent address history for the active workdir and refresh UI."""
        runtime = self.runtime
        with runtime._browser_history_lock:
            runtime.browser_history = []
        path = self.path()
        for candidate in (path, path + ".tmp"):
            try:
                if os.path.exists(candidate):
                    os.remove(candidate)
            except OSError:
                pass
        self.notify()

    def apply_settings(self):
        """Apply changed history limit/settings without touching Canvas Back/Forward state."""
        runtime = self.runtime
        limit = self.limit()
        changed = False
        with runtime._browser_history_lock:
            if len(runtime.browser_history) > limit:
                runtime.browser_history = runtime.browser_history[:limit]
                changed = True
        if changed:
            self.save()
        self.notify()

    def notify(self):
        runtime = self.runtime
        for entry in runtime._surfaces:
            entry['instance'].history.notify()
        owner = runtime.surface_owner
        if owner is not None:
            try:
                owner.update_address_history(self.entries())
            except Exception:
                pass

    def on_qt_url_changed(self, url: QUrl):
        runtime = self.runtime
        if runtime.backend != "qt":
            return
        value = url.toString() if url is not None else ""
        if value:
            runtime.virtual_url = value
        runtime.notify_state()

    def on_qt_title_changed(self, title: str):
        """Persist the latest page title for a real HTTP(S) navigation."""
        runtime = self.runtime
        if runtime.backend != "qt":
            return
        if runtime.surface is not None and runtime.current_canvas_history_is_url():
            self.update_title(runtime.surface.web.url().toString(), title)
        runtime.notify_state()

    def push(self, entry: dict):
        """Append one Canvas history entry and keep only the newest HISTORY_LIMIT items."""
        runtime = self.runtime
        if not isinstance(entry, dict):
            return
        if runtime.canvas_history_index + 1 < len(runtime.canvas_history):
            runtime.canvas_history = runtime.canvas_history[:runtime.canvas_history_index + 1]
        runtime.canvas_history.append(dict(entry))
        overflow = len(runtime.canvas_history) - runtime.HISTORY_LIMIT
        if overflow > 0:
            runtime.canvas_history = runtime.canvas_history[overflow:]
        runtime.canvas_history_index = len(runtime.canvas_history) - 1

    def update_current_url(self, url: str):
        """Update a pending URL entry after redirects resolve to their final address."""
        runtime = self.runtime
        if not url or not (0 <= runtime.canvas_history_index < len(runtime.canvas_history)):
            return
        entry = runtime.canvas_history[runtime.canvas_history_index]
        if entry.get("kind") == "url":
            entry["url"] = str(url)

    def record_navigation(self, url: str):
        """Record user/page navigation that was not initiated by a Canvas history restore."""
        runtime = self.runtime
        url = str(url or "").strip()
        if not url or url == "about:blank" or runtime.blank_canvas_active:
            return
        if 0 <= runtime.canvas_history_index < len(runtime.canvas_history):
            current = runtime.canvas_history[runtime.canvas_history_index]
            if current.get("kind") == "url" and current.get("url") == url:
                return
        self.push({"kind": "url", "url": url})

    def restore(self, index: int):
        """Restore an existing URL/HTML entry without creating another history item."""
        runtime = self.runtime
        if not (0 <= index < len(runtime.canvas_history)):
            return runtime.current_state()
        runtime.canvas_history_index = index
        entry = runtime.canvas_history[index]
        if entry.get("kind") == "html":
            return runtime.commands.set_html({
                "html": entry.get("html", ""),
                "base_url": entry.get("base_url", ""),
                "__workdir": entry.get("workdir") or os.getcwd(),
                "__ui": True,
                "__history_restore": True,
            })
        return runtime.commands.open({
            "url": entry.get("url", "about:blank"),
            "__ui": True,
            "__history_restore": True,
        })
