#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from threading import RLock

from .custom import Custom
from .legacy import Legacy
from .observer import Observer
from .provider import Provider
from .tools import Tools

class Agents:
    def __init__(self, window=None):
        """
        Agents core

        :param window: Window instance
        """
        self.window = window
        self.custom = Custom(window)
        self.legacy = Legacy(window)
        self._memory = None
        self.observer = Observer(window)
        self.provider = Provider(window)
        self._runner = None
        self._session_memory = {}
        self._session_memory_lock = RLock()
        self._unsaved_memory_meta = {}
        self.tools = Tools(window)


    @staticmethod
    def _meta_session_id(meta):
        """Tag database ids separately from unsaved object identities."""
        if isinstance(meta, (int, str)):
            return ("saved", str(meta))
        meta_id = getattr(meta, "id", None)
        return ("saved", str(meta_id)) if meta_id is not None else ("unsaved", id(meta))

    def get_session_memory(self, meta, namespace: str, key: str, factory):
        """Reuse one role memory across fresh workflow objects and worker loops."""
        if meta is None:
            return factory()  # detached calls must never share a global None session
        with self._session_memory_lock:
            session_id = self._meta_session_id(meta)
            temporary_id = ("unsaved", id(meta))
            if session_id[0] == "unsaved":
                # Keep an unsaved meta alive so Python cannot reuse its object id.
                self._unsaved_memory_meta[id(meta)] = meta
            elif id(meta) in self._unsaved_memory_meta:
                for old_key in list(self._session_memory):
                    if old_key[0] == temporary_id:
                        new_key = (session_id, *old_key[1:])
                        self._session_memory.setdefault(new_key, self._session_memory.pop(old_key))
                self._unsaved_memory_meta.pop(id(meta), None)
            cache_key = (session_id, str(namespace or ""), str(key or ""))
            if cache_key not in self._session_memory:
                self._session_memory[cache_key] = factory()
            return self._session_memory[cache_key]

    def clear_session_memory(self, meta=None):
        """Invalidate memory when a conversation is deleted, cleared or rewound."""
        with self._session_memory_lock:
            if meta is None:
                self._session_memory.clear()
                self._unsaved_memory_meta.clear()
                return
            session_ids = {self._meta_session_id(meta), ("unsaved", id(meta))}
            for cache_key in list(self._session_memory):
                if cache_key[0] in session_ids:
                    self._session_memory.pop(cache_key, None)
            self._unsaved_memory_meta.pop(id(meta), None)

    @property
    def memory(self):
        """Create LlamaIndex-backed legacy agent memory only when used."""
        if self._memory is None:
            from .memory import Memory
            self._memory = Memory(self.window)
        return self._memory

    @property
    def runner(self):
        """Create legacy agent runners only for an actual legacy agent request."""
        if self._runner is None:
            from .runner import Runner
            self._runner = Runner(self.window)
        return self._runner
