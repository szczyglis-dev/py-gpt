#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 03:00:00                  #
# ================================================== #

import copy
import uuid
from collections import OrderedDict
from typing import Optional, Tuple, Dict, List

from packaging.version import Version
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
    MODE_COMPUTER,
)
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.core.preset.json_file import JsonFileProvider


class Presets:
    _MODE_TO_ATTR = {
        MODE_CHAT: "chat",
        MODE_COMPLETION: "completion",
        MODE_IMAGE: "img",
        MODE_VISION: "vision",
        MODE_LANGCHAIN: "langchain",
        MODE_ASSISTANT: "assistant",
        MODE_LLAMA_INDEX: "llama_index",
        MODE_AGENT: "agent",
        MODE_AGENT_LLAMA: "agent_llama",
        MODE_AGENT_OPENAI: "agent_openai",
        MODE_EXPERT: "expert",
        MODE_RESEARCH: "research",
        MODE_COMPUTER: "computer",
        MODE_AUDIO: "audio",
    }

    def __init__(self, window=None):
        """
        Presets core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.items: Dict[str, PresetItem] = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version):
        """
        Patch provider data

        :param app_version: app version
        """
        self.provider.patch(app_version)

    def build(self) -> PresetItem:
        """
        Build empty preset

        :return: empty preset
        """
        preset = PresetItem()
        preset.uuid = str(uuid.uuid4())
        return preset

    def append_current(self):
        """Append current presets"""
        items = self.items
        ids = [
            ("current.chat", "chat"),
            ("current.completion", "completion"),
            ("current.img", "img"),
            ("current.vision", "vision"),
            ("current.langchain", "langchain"),
            ("current.assistant", "assistant"),
            ("current.llama_index", "llama_index"),
            ("current.agent", "agent"),
            ("current.agent_llama", "agent_llama"),
            ("current.agent_openai", "agent_openai"),
            ("current.expert", "expert"),
            ("current.audio", "audio"),
            ("current.computer", "computer"),
        ]
        front = {}
        for pid, attr in ids:
            if pid in items:
                obj = items[pid]
            else:
                obj = self.build()
                if pid == "current.chat":
                    obj.prompt = self.window.core.prompt.get("default")
            setattr(obj, attr, True)
            obj.name = "*"
            front[pid] = obj
        self.items = {**front, **items}

    def exists(self, id: str) -> bool:
        """
        Check if preset exists

        :param id: preset id
        :return: True if exists
        """
        return id in self.items

    def exists_uuid(self, uuid: str) -> bool:
        """
        Check if preset exists

        :param uuid: preset uuid
        :return: True if exists
        """
        return any(item.uuid == uuid for item in self.items.values())

    def enable(self, id: str):
        """
        Enable preset

        :param id: preset id
        """
        if id in self.items:
            self.items[id].enabled = True

    def disable(self, id: str):
        """
        Disable preset

        :param id: preset id
        """
        if id in self.items:
            self.items[id].enabled = False

    def get_first_mode(self, id: str) -> Optional[str]:
        """
        Return first mode for preset

        :param id: preset id
        :return: mode name
        """
        preset = self.items[id]
        if preset.chat:
            return MODE_CHAT
        if preset.completion:
            return MODE_COMPLETION
        if preset.img:
            return MODE_IMAGE
        if preset.assistant:
            return MODE_ASSISTANT
        if preset.llama_index:
            return MODE_LLAMA_INDEX
        if preset.agent:
            return MODE_AGENT
        if preset.agent_llama:
            return MODE_AGENT_LLAMA
        if preset.agent_openai:
            return MODE_AGENT_OPENAI
        if preset.expert:
            return MODE_EXPERT
        if preset.audio:
            return MODE_AUDIO
        if preset.research:
            return MODE_RESEARCH
        if preset.computer:
            return MODE_COMPUTER
        return None

    def has(self, mode: str, id: str) -> bool:
        """
        Check if preset for mode exists

        :param mode: mode name
        :param id : preset id
        :return: True if exists
        """
        item = self.items.get(id)
        if not item:
            return False
        attr = self._MODE_TO_ATTR.get(mode)
        return bool(attr and getattr(item, attr, False))

    def get_by_idx(self, idx: int, mode: str) -> str:
        """
        Return preset by index

        :param idx: index
        :param mode: mode
        :return: preset id
        """
        attr = self._MODE_TO_ATTR.get(mode)
        if not attr:
            return
        ids = list(self.get_by_mode(mode).keys())
        if idx < 0 or idx >= len(ids):
            return
        return ids[idx]

    def get_by_id(self, mode: str, id: str) -> Optional[PresetItem]:
        """
        Return preset by id

        :param mode: mode name
        :param id: preset id
        :return: preset item
        """
        item = self.items.get(id)
        if not item:
            return None
        attr = self._MODE_TO_ATTR.get(mode)
        if not attr:
            return None
        return item if getattr(item, attr, False) else None

    def get(self, id: str) -> Optional[PresetItem]:
        """
        Return preset by ID

        :param id: preset ID
        :return: preset item
        """
        return self.items.get(id)

    def get_by_uuid(self, uuid: str) -> Optional[PresetItem]:
        """
        Return preset by UUID

        :param uuid: preset UUID
        :return: preset item
        """
        return next((item for item in self.items.values() if item.uuid == uuid), None)

    def get_by_mode(self, mode: str) -> Dict[str, PresetItem]:
        """
        Return presets for mode

        :param mode: mode name
        :return: presets dict for mode
        """
        attr = self._MODE_TO_ATTR.get(mode)
        if not attr:
            return {}
        data = {id: item for id, item in self.items.items() if getattr(item, attr, False)}
        if not self._dnd_enabled():
            return data
        ordered_ids = self._ordered_ids_for_mode(mode)
        out = OrderedDict()
        for pid in ordered_ids:
            itm = data.get(pid)
            if itm is not None:
                out[pid] = itm
        for pid, itm in data.items():
            if pid not in out:
                out[pid] = itm
        return out

    def get_idx_by_id(self, mode: str, id: str) -> int:
        """
        Return preset index

        :param mode: mode name
        :param id: preset id
        :return: preset idx
        """
        if id is None:
            return 0
        ids = list(self.get_by_mode(mode).keys())
        try:
            return ids.index(id)
        except ValueError:
            return 0

    def get_default(self, mode: str) -> Optional[str]:
        """
        Return default preset for mode

        :param mode: mode name
        :return: default prompt name
        """
        data = self.get_by_mode(mode)
        for key in data.keys():
            return key
        return None

    def get_duplicate_name(self, id: str) -> Tuple[str, str]:
        """
        Prepare name for duplicated preset

        :param id: preset id
        :return: new ID, new name
        """
        old_name = self.items[id].name
        new_id = id
        new_name = old_name
        while True:
            new_id = new_id + '_copy'
            new_name = new_name + ' copy'
            if new_id not in self.items:
                return new_id, new_name

    def duplicate(self, id: str) -> str:
        """
        Make preset duplicate

        :param id: preset id
        :return: duplicated preset ID
        """
        prev_id = id
        id, name = self.get_duplicate_name(id)
        self.items[id] = copy.deepcopy(self.items[prev_id])
        self.items[id].name = name
        self.items[id].filename = id
        self.items[id].uuid = str(uuid.uuid4())
        self.sort_by_name()
        self._order_append_new_item(id)
        return id

    def remove(
            self,
            id: str,
            remove_file: bool = True
    ):
        """
        Delete preset

        :param id: preset id
        :param remove_file: also remove preset JSON config file
        """
        if id in self.items:
            item = self.items[id]
            rem_uuid = item.uuid
            self.items.pop(id)
            self._order_remove_uuid(rem_uuid)

        if remove_file:
            self.provider.remove(id)

    def sort_by_name(self):
        """Sort presets by name"""
        self.items = dict(
            sorted(
                self.items.items(),
                key=lambda item: item[1].name
            )
        )

    def update(self, preset: PresetItem):
        """
        Update preset

        :param preset: preset item
        """
        self.items[preset.filename] = preset
        self._order_append_new_item(preset.filename)

    def update_and_save(self, preset: PresetItem):
        """
        Update preset

        :param preset: preset item
        """
        self.items[preset.filename] = preset
        self.save(preset.filename)
        self._order_append_new_item(preset.filename)

    def get_all(self) -> Dict[str, PresetItem]:
        """
        Return all presets

        :return: presets dict
        """
        return self.items

    def restore(self, mode: str):
        """
        Restore default preset for mode

        :param mode: mode name
        """
        base = self.load_base()
        id = "current." + mode
        if id in base:
            self.items[id] = base[id]
            self.save(id)

    def load_base(self) -> Dict[str, PresetItem]:
        """
        Load base presets

        :return: base presets
        """
        return self.provider.load_base()

    def load(self):
        """Load presets templates"""
        self.items = self.provider.load()
        self.patch_empty()
        self.patch_duplicated()
        self.sort_by_name()
        self.append_current()
        self._order_sync_all()

    def save(self, id: str):
        """
        Save preset

        :param id: preset id
        """
        if id not in self.items:
            return
        self.provider.save(id, self.items[id])

    def save_all(self):
        """Save all presets"""
        self.provider.save_all(self.items)

    def add_expert(
            self,
            agent_uuid: str,
            expert_uuid: str
    ):
        """
        Add expert to agent

        :param agent_uuid: agent uuid
        :param expert_uuid: expert uuid
        """
        agent = self.get_by_uuid(agent_uuid)
        if agent is None:
            return
        if expert_uuid not in agent.experts:
            agent.experts.append(expert_uuid)
        self.save(agent.filename)

    def remove_expert(
            self,
            agent_uuid: str,
            expert_uuid: str
    ):
        """
        Remove expert from agent
        :param agent_uuid: agent uuid
        :param expert_uuid: expert uuid
        """
        agent = self.get_by_uuid(agent_uuid)
        if agent is None:
            return
        if expert_uuid in agent.experts:
            agent.experts.remove(expert_uuid)
        self.save(agent.filename)

    def patch_empty(self):
        """Patch UUIDs for all presets"""
        patched = False
        for key, item in self.items.items():
            if item.uuid is None:
                item.uuid = str(uuid.uuid4())
                patched = True
            if item.filename is None or item.filename == "":
                item.filename = key
                patched = True
        if patched:
            self.save_all()

    def patch_duplicated(self):
        """Patch UUIDs for all presets"""
        patched = False
        uuids = set()
        for item in self.items.values():
            if item.uuid in uuids:
                item.uuid = str(uuid.uuid4())
                patched = True
            uuids.add(item.uuid)
        if patched:
            self.save_all()

    # ----------------------------
    # Ordering (drag & drop) logic
    # ----------------------------

    def _cfg_get(self, key, default=None):
        try:
            return self.window.core.config.get(key)
        except Exception:
            return default

    def _cfg_set(self, key, value):
        try:
            self.window.core.config.set(key, value)
        except Exception:
            pass

    def _dnd_enabled(self) -> bool:
        """
        Check global switch for DnD ordering.
        """
        v = self._cfg_get('presets.drag_and_drop.enabled', False)
        return bool(v)

    @staticmethod
    def _is_special_id(pid: str) -> bool:
        """
        current.* presets are special and pinned at top; not movable.
        """
        return pid.startswith("current.")

    def _uuid_to_id_map(self) -> Dict[str, str]:
        return {item.uuid: pid for pid, item in self.items.items() if item.uuid}

    def _visible_ids_for_mode(self, mode: str) -> List[str]:
        attr = self._MODE_TO_ATTR.get(mode)
        if not attr:
            return []
        return [pid for pid, it in self.items.items() if getattr(it, attr, False)]

    def _visible_regular_ids_for_mode(self, mode: str) -> List[str]:
        return [pid for pid in self._visible_ids_for_mode(mode) if not self._is_special_id(pid)]

    def _visible_regular_uuids_for_mode(self, mode: str) -> List[str]:
        ids = self._visible_regular_ids_for_mode(mode)
        return [self.items[pid].uuid for pid in ids if pid in self.items and self.items[pid].uuid]

    def _build_global_uuid_order(self) -> List[str]:
        """
        Rebuild 'global' order each time based on name-sorted presets (excluding current.*).
        """
        regs = [(pid, it) for pid, it in self.items.items() if not self._is_special_id(pid)]
        regs.sort(key=lambda x: x[1].name)
        return [it.uuid for pid, it in regs if it.uuid]

    def _order_get_store(self) -> Dict[str, List[str]]:
        store = self._cfg_get('presets_order', {}) or {}
        fixed = {}
        for k, v in store.items():
            if isinstance(v, dict):
                try:
                    seq = [v[i] for i in sorted(v.keys(), key=lambda x: int(x))]
                except Exception:
                    seq = list(v.values())
                fixed[k] = seq
            elif isinstance(v, list):
                fixed[k] = v
        return fixed

    def _order_set_store(self, store: Dict[str, List[str]]):
        self._cfg_set('presets_order', store)

    def _order_sync_mode(self, mode: str, store: Dict[str, List[str]]) -> List[str]:
        """
        Ensure mode order is valid:
        - Start from mode order or fallback to global
        - Drop unknown UUIDs
        - Append missing visible UUIDs at the end
        """
        visible = self._visible_regular_uuids_for_mode(mode)
        visible_set = set(visible)

        base = list(store.get(mode) or [])
        if not base:
            base = [u for u in store.get('global', []) if u in visible_set]

        base = [u for u in base if u in visible_set]

        seen = set(base)
        for u in visible:
            if u not in seen:
                base.append(u)
                seen.add(u)

        dedup = []
        s = set()
        for u in base:
            if u not in s:
                dedup.append(u)
                s.add(u)

        store[mode] = dedup
        return dedup

    def _order_sync_all(self):
        """
        Sync presets_order with current items and rebuild 'global' each time.
        """
        store = self._order_get_store()
        store['global'] = self._build_global_uuid_order()

        existing = set([it.uuid for it in self.items.values() if it.uuid])
        for k, lst in list(store.items()):
            if isinstance(lst, list):
                store[k] = [u for u in lst if u in existing]

        for mode in self._MODE_TO_ATTR.keys():
            self._order_sync_mode(mode, store)

        self._order_set_store(store)

    def _ordered_ids_for_mode(self, mode: str) -> List[str]:
        """
        Produce ordered preset IDs for given mode:
        - current.<mode> first (if exists)
        - then remaining items by order stored as UUIDs
        """
        attr = self._MODE_TO_ATTR.get(mode)
        if not attr:
            return []
        store = self._order_get_store()
        ordered_uuids = self._order_sync_mode(mode, store)
        self._order_set_store(store)

        uuid_to_id = self._uuid_to_id_map()
        head_id = f"current.{mode}"
        out: List[str] = []
        if head_id in self.items and getattr(self.items[head_id], attr, False):
            out.append(head_id)
        for u in ordered_uuids:
            pid = uuid_to_id.get(u)
            if pid and getattr(self.items.get(pid, PresetItem()), attr, False):
                out.append(pid)
        return out

    def _order_append_new_item(self, pid: str):
        """
        Append new preset (by ID) to the end of all applicable mode orders.
        """
        if pid not in self.items:
            return
        if self._is_special_id(pid):
            return
        item = self.items[pid]
        if not item.uuid:
            return
        store = self._order_get_store()
        modes = [m for m, attr in self._MODE_TO_ATTR.items() if getattr(item, attr, False)]
        for m in modes:
            seq = list(store.get(m) or [])
            if item.uuid not in seq:
                seq.append(item.uuid)
                store[m] = seq
        self._order_set_store(store)

    def _order_remove_uuid(self, rem_uuid: Optional[str]):
        """
        Remove a UUID from all order lists (including global).
        """
        if not rem_uuid:
            return
        store = self._order_get_store()
        changed = False
        for k, lst in list(store.items()):
            if isinstance(lst, list) and rem_uuid in lst:
                store[k] = [u for u in lst if u != rem_uuid]
                changed = True
        if changed:
            self._order_set_store(store)