#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 02:00:00                  #
# ================================================== #

import copy
import datetime
import uuid
from typing import Optional, Tuple, List, Dict

from packaging.version import Version

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
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
    MODE_AGENT_OPENAI,
)
from pygpt_net.item.ctx import CtxItem, CtxMeta, CtxGroup
from pygpt_net.provider.core.ctx.base import BaseProvider
from pygpt_net.provider.core.ctx.db_sqlite import DbSqliteProvider
from pygpt_net.utils import trans

from .idx import Idx
from .container import Container
from .output import Output


class Ctx:
    def __init__(self, window=None):
        """
        Context core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.container = Container(window)  # context container
        self.output = Output(window)  # context render output
        self.idx = Idx(window)  # context indexing core
        self.meta = {}
        self.current = None
        self.last_item = None
        self.assistant = None
        self.mode = None
        self.model = None
        self.preset = None
        self.run = None
        self.status = None
        self.thread = None
        self.last_mode = None
        self.last_model = None
        self.tmp_meta = None
        self.search_string = None  # search string
        self.groups = {}  # groups
        self.filters = {}  # search filters
        self.filters_labels = []  # search labels
        self.current_cmd = []  # current commands
        self.current_cmd_schema = "" # current commands schema
        self.all_modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_IMAGE,
            MODE_LANGCHAIN,
            MODE_VISION,
            MODE_ASSISTANT,
            MODE_LLAMA_INDEX,
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_AGENT_OPENAI,
            MODE_EXPERT,
            MODE_AUDIO,
            MODE_RESEARCH,
            MODE_COMPUTER,
        ]
        self.allowed_modes = {
            MODE_CHAT: self.all_modes,
            MODE_COMPLETION: self.all_modes,
            MODE_IMAGE: [MODE_IMAGE],
            MODE_LANGCHAIN: self.all_modes,
            MODE_VISION: self.all_modes,
            MODE_ASSISTANT: [MODE_ASSISTANT],
            MODE_LLAMA_INDEX: self.all_modes,
            MODE_EXPERT: self.all_modes,
            MODE_AUDIO: self.all_modes,
            MODE_AGENT: self.all_modes,
            MODE_AGENT_LLAMA: self.all_modes,
            MODE_AGENT_OPENAI: self.all_modes,
            MODE_RESEARCH: self.all_modes,
            MODE_COMPUTER: self.all_modes,
        }
        self.current_sys_prompt = ""
        self.groups_loaded = False

    def get_items(self) -> List[CtxItem]:
        """
        Get context items

        :return: context items
        """
        return self.container.get_items()

    def set_items(self, items: List[CtxItem]):
        """
        Set context items

        :param items: context items
        """
        self.container.set_items(items)

    def clear_items(self):
        """Clear context items"""
        self.container.clear_items()

    def count_items(self) -> int:
        """
        Count context items
        :return: context items count
        """
        return self.container.count_items()

    def get_current(self) -> int:
        """
        Get current context ID

        :return: current context ID
        """
        return self.current

    def set_current(self, current: int):
        """
        Set current context ID

        :param current: current context ID
        """
        self.current = current

    def clear_current(self):
        """Clear current context ID"""
        self.current = None

    def get_last_item(self) -> Optional[CtxItem]:
        """
        Get last item

        :return: last item
        """
        return self.last_item

    def set_last_item(self, last_item: Optional[CtxItem]):
        """
        Set last item

        :param last_item: last item
        """
        self.last_item = last_item

    def get_assistant(self) -> str:
        """
        Get assistant name

        :return: assistant name
        """
        return self.assistant

    def set_assistant(self, assistant: str):
        """
        Set assistant name

        :param assistant: assistant name
        :return: assistant name
        """
        self.assistant = assistant

    def get_mode(self) -> str:
        """
        Get mode

        :return: mode
        """
        return self.mode

    def set_mode(self, mode: str):
        """
        Set mode

        :param mode: mode
        """
        self.mode = mode

    def get_model(self) -> str:
        """
        Get model name
        :return: model name
        """
        return self.model

    def set_model(self, model: str):
        """
        Set model name

        :param model: model name
        """
        self.model = model

    def get_preset(self) -> str:
        """
        Get preset name
        :return: preset
        """
        return self.preset

    def set_preset(self, preset: str):
        """
        Set preset name

        :param preset: preset name
        """
        self.preset = preset

    def get_run(self) -> str:
        """
        Get run ID

        :return: run ID
        """
        return self.run

    def set_status(self, status: int):
        """
        Set status (label color)

        :param status: status
        """
        self.status = status

    def get_status(self) -> int:
        """
        Get status (label color)

        :return: status
        """
        return self.status

    def set_run(self, run: str):
        """
        Set run ID

        :param run: run ID
        """
        self.run = run

    def get_thread(self) -> str:
        """
        Get thread ID

        :return: thread ID
        """
        return self.thread

    def set_thread(self, thread: str):
        """
        Set thread ID

        :param thread: thread ID
        """
        self.thread = thread

    def clear_thread(self):
        """Clear thread ID"""
        self.thread = None

    def get_last_mode(self) -> str:
        """
        Get last mode

        :return: last mode
        """
        return self.last_mode

    def set_last_mode(self, last_mode: str):
        """
        Set last mode

        :param last_mode: last mode
        """
        self.last_mode = last_mode

    def get_last_model(self) -> str:
        """
        Get last model name

        :return: last model
        """
        return self.last_model

    def set_last_model(self, last_model: str):
        """
        Set last model name

        :param last_model: last model name
        """
        self.last_model = last_model

    def get_tmp_meta(self) -> Optional[CtxMeta]:
        """
        Get temporary meta

        :return: temporary meta
        """
        return self.tmp_meta

    def set_tmp_meta(self, tmp_meta: Optional[CtxMeta]):
        """
        Set temporary meta

        :param tmp_meta: temporary meta
        """
        self.tmp_meta = tmp_meta

    def get_search_string(self) -> Optional[str]:
        """
        Get search string

        :return: search string
        """
        return self.search_string

    def set_search_string(self, search_string: Optional[str]):
        """
        Set search string

        :param search_string: search string
        """
        self.search_string = search_string

    def clear_search_string(self):
        """Clear search string"""
        self.search_string = None

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def get_provider(self) -> BaseProvider:
        """
        Get provider instance

        :return: provider instance
        """
        return self.provider

    def select(
            self,
            id: int,
            restore_model: bool = True
    ):
        """
        Select ctx meta by ID and load ctx items

        :param id: context meta id
        :param restore_model: restore model
        """
        if id not in self.meta:
            self.load_tmp_meta(id)

        if id in self.meta:
            ctx = self.meta[id]
            self.current = id

            self.thread = None
            self.mode = None
            self.assistant = None

            self.thread = ctx.thread
            self.mode = ctx.mode
            self.assistant = ctx.assistant
            self.preset = ctx.preset

            if restore_model:
                if ctx.last_model is not None \
                        and self.window.core.models.has_model(self.mode, ctx.last_model):
                    self.model = ctx.last_model
                elif ctx.model is not None \
                        and self.window.core.models.has_model(self.mode, ctx.model):
                    self.model = ctx.model

            self.set_items(self.load(id))

    def new(
            self,
            group_id: Optional[int] = None
    ) -> Optional[CtxMeta]:
        """
        Create new ctx and set as current

        :param group_id: group id
        :return: CtxMeta instance (new ctx meta)
        """
        meta = self.create(group_id)
        if meta is None:
            self.window.core.debug.log("Error creating new ctx")
            return
        preset = self.window.core.config.get('preset')
        meta.preset = preset
        self.meta[meta.id] = meta
        self.tmp_meta = meta
        self.current = meta.id
        self.last_item = None
        self.thread = None
        self.assistant = None
        self.mode = self.window.core.config.get('mode')
        self.model = self.window.core.config.get('model')
        self.preset = preset
        self.clear_items()
        self.save(meta.id)

        return meta

    def build(self) -> CtxMeta:
        """
        Build new ctx

        :return: created CtxMeta instance
        """
        meta = CtxMeta()
        meta.name = "{}".format(trans('ctx.new.prefix'))
        meta.date = datetime.datetime.now().strftime("%Y-%m-%d")
        meta.mode = self.window.core.config.get('mode')
        meta.model = self.window.core.config.get('model')
        meta.last_mode = self.window.core.config.get('mode')
        meta.last_model = self.window.core.config.get('model')
        meta.initialized = False
        return meta

    def create(
            self,
            group_id: Optional[int] = None
    ) -> CtxMeta:
        """
        Send created meta to provider and return new ID

        :param group_id: group id
        :return: CtxMeta instance
        """
        meta = self.build()
        if group_id is not None:
            meta.group_id = group_id
        id = self.provider.create(meta)
        meta.id = id
        return meta

    def add(
            self,
            item: CtxItem,
            parent_id: Optional[int] = None
    ):
        """
        Add CtxItem to contexts and saves context

        :param item: CtxItem to append
        :param parent_id: parent id
        """
        if parent_id is not None:
            self.add_to_meta(item, parent_id)
            return

        items = self.get_items()
        items.append(item)

        if self.current is not None:
            if self.current not in self.meta:
                self.load_tmp_meta(self.current)
            if self.current in self.meta:
                meta = self.meta[self.current]
                result = self.provider.append_item(meta, item)
                if not result:
                    self.store()

    def add_to_meta(
            self,
            item: CtxItem,
            meta_id: Optional[int] = None
    ):
        """
        Add CtxItem to custom meta

        :param item: CtxItem to append
        :param meta_id: meta id
        """
        if meta_id in self.meta:
            meta = self.meta[meta_id]
        else:
            meta = self.provider.get_meta_by_id(meta_id)
        if meta is not None:
            self.provider.append_item(meta, item)

    def update_item(self, item: CtxItem):
        """
        Update CtxItem in context

        :param item: CtxItem to update
        """
        self.provider.update_item(item)

    def update_indexed_ts_by_id(self, id: int, ts: int):
        """
        Update indexed timestamp by ID

        :param id: context id
        :param ts: timestamp
        """
        if id in self.meta:
            self.meta[id].indexed = ts

    def is_empty(self) -> bool:
        """
        Check if ctx is empty

        :return: True if empty, false otherwise
        """
        if self.current is None:
            return True
        return self.count_items() == 0

    def update(self):
        """
        Update current parent (when ctx item load from the list or setting mode)
        """
        self.mode = self.window.core.config.get('mode')

        if self.current is None:
            return

        if self.current not in self.meta:
            self.load_tmp_meta(self.current)

        if self.current not in self.meta:
            return

        self.meta[self.current].mode = self.mode
        self.save(self.current)

    def replace(self, meta: CtxMeta):
        """
        Replace meta

        :param meta: CtxMeta
        """
        self.meta[meta.id] = meta

    def post_update(self, mode: str):
        """
        Update current (last) ctx data

        :param mode: mode name
        """
        if self.current is None:
            return

        if self.current not in self.meta:
            self.load_tmp_meta(self.current)

        if self.current not in self.meta:
            return

        self.assistant = self.window.core.config.get('assistant')
        self.preset = self.window.core.config.get('preset')
        self.model = self.window.core.config.get('model')

        self.meta[self.current].last_mode = mode
        self.meta[self.current].last_model = self.model
        self.meta[self.current].preset = self.preset

        if mode == MODE_ASSISTANT:
            self.meta[self.current].assistant = self.assistant

        self.save(self.current)

    def is_initialized(self) -> bool:
        """
        Check if ctx is initialized (name assigned)

        :return: True if initialized, false otherwise
        """
        if self.current is None:
            return False
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            return self.meta[self.current].initialized
        return False

    def set_initialized(self):
        """Set ctx as initialized (name assigned)"""
        if self.current is None:
            return
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            self.meta[self.current].initialized = True
            self.save(self.current)

    def has(self, id: int) -> bool:
        """
        Check if ctx meta exists

        :param id: ctx ID
        :return: True if exists, false otherwise
        """
        return id in self.meta

    def get(self, idx: int) -> CtxItem:
        """
        Return ctx item by index

        :param idx: item index
        :return: context item
        """
        if idx < self.count_items():
            return self.get_items()[idx]

    def get_item_by_id(self, id: int) -> CtxItem:
        """
        Return ctx item by id

        :param id: item id
        :return: context item
        """
        items = self.get_items()
        for item in items:
            if item.id == id:
                return item
        return self.fetch_item_by_id(id)

    def fetch_item_by_id(self, id: int) -> CtxItem:
        """
        Fetch ctx item by id

        :param id: item id
        :return: context item
        """
        return self.provider.get_item_by_id(id)

    def get_meta(self, reload: bool = False) -> dict:
        """
        Get ctx items sorted descending by date

        :param reload: True if reload from provider
        :return: ctx metas dict
        """
        if reload:
            self.load_meta()
        return self.meta

    def get_current_meta(self) -> Optional[CtxMeta]:
        """
        Get current meta

        :return: current meta
        """
        if self.current is not None:
            return self.get_meta_by_id(self.current)

    def get_id_by_idx(self, idx: int) -> int:
        """
        Get ctx id (id) by index

        :param idx: index
        :return: ctx id
        """
        i = 0
        for id in self.get_meta():
            if i == idx:
                return id
            i += 1

    def get_idx_by_id(self, id: int) -> int:
        """
        Get ctx index by id

        :param id: id
        :return: idx
        """
        for i, key in enumerate(self.get_meta()):
            if key == id:
                return i

    def get_first(self) -> str:
        """
        Return first ctx ID from list

        :return: ctx id
        """
        for id in self.get_meta():
            return id

    def get_meta_by_id(self, id: int) -> CtxMeta:
        """
        Return ctx meta by id

        :param id: ctx id
        :return: ctx meta object
        """
        self.load_tmp_meta(id)
        if id in self.meta:
            return self.meta[id]

    def get_last(self) -> Optional[CtxItem]:
        """
        Return last item from ctx

        :return: last ctx item
        """
        items = self.get_items()
        if items:
            return items[-1]
        return None

    def is_first_item(self, item_id: int) -> bool:
        """
        Check if item is first in ctx

        :param item_id: item id
        :return: True if first
        """
        items = self.get_items()
        if items:
            return items[0].id == item_id
        return False

    def is_last_item(self, item_id: int) -> bool:
        """
        Check if item is last in ctx

        :param item_id: item id
        :return: True if last
        """
        items = self.get_items()
        if items:
            return items[-1].id == item_id
        return False

    def get_previous_item(self, item_id: int) -> Optional[CtxItem]:
        """
        Get previous item from ctx

        :param item_id: item id
        :return: ctx item
        """
        items = self.get_items()
        prev = None
        for it in items:
            if it.id == item_id:
                return prev
            prev = it
        return None

    def prepare(self):
        """Prepare context for prompt"""
        if self.count_meta() == 0:
            self.new()

    def count(self) -> int:
        """
        Count ctx items

        :return: ctx items count
        """
        return self.count_items()

    def count_meta(self) -> int:
        """
        Count ctx meta items

        :return: ctx meta count
        """
        return len(self.meta) + (1 if self.tmp_meta is not None else 0)

    def count_found_meta(self) -> int:
        """
        Count ctx meta items

        :return: ctx meta count
        """
        return len(self.meta)

    def all(
            self,
            meta_id: Optional[int] = None
    ) -> List[CtxItem]:
        """
        Return ctx items (current or by meta_id if provided)

        :param meta_id: meta id
        :return: ctx items
        """
        if meta_id is None:
            return self.get_items()
        else:
            return self.load(meta_id)

    def remove(self, id: int):
        """
        Delete ctx by id

        :param id: ctx id
        """
        if id in self.meta:
            del self.meta[id]
            self.provider.remove(id)

    def remove_item(self, id: int):
        """
        Remove ctx item by id

        :param id: ctx id
        """
        items = self.get_items()
        for i, item in enumerate(items):
            if item.id == id:
                items.pop(i)
                self.provider.remove_item(id)
                break

    def remove_items_from(
            self,
            meta_id: int,
            item_id: int
    ):
        """
        Remove ctx items from meta_id

        :param meta_id: meta_id
        :param item_id: item_id
        """
        items = [item for item in self.get_items() if item.id < item_id]
        self.set_items(items)
        return self.provider.remove_items_from(meta_id, item_id)

    def truncate(self):
        """Delete all ctx"""
        self.meta = {}
        self.provider.truncate()

    def clear(self):
        """Clear ctx items"""
        self.clear_items()

    def append_thread(self, thread: str):
        """
        Append thread ID to ctx

        :param thread: thread ID
        """
        self.thread = thread
        if self.current is None:
            return
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            self.meta[self.current].thread = self.thread
            self.save(self.current)

    def append_run(self, run):
        """
        Append run ID to ctx

        :param run: run ID
        """
        self.run = run
        if self.current is None:
            return
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            self.meta[self.current].run = self.run
            self.save(self.current)

    def append_status(self, status: int):
        """
        Append status (label color) to ctx

        :param status: status
        """
        self.status = status
        if self.current is None:
            return
        if self.current in self.meta:
            self.meta[self.current].status = self.status
            self.save(self.current)

    def get_or_create_slave_meta(
            self,
            master_ctx: CtxItem,
            preset_id: str
    ) -> CtxMeta:
        """
        Get or create slave meta

        :param master_ctx: master context
        :param preset_id: preset ID
        :return: slave meta
        """
        slaves = []
        if master_ctx.meta is not None:
            slaves = self.provider.get_meta_by_root_id_and_preset_id(
                master_ctx.meta.id,
                preset_id,
            )
        if len(slaves) > 0:
            return next(iter(slaves.values()))
        slave = self.build()

        if master_ctx.meta is not None:
            slave.root_id = master_ctx.meta.id
            slave.parent_id = master_ctx.meta.id

        slave.preset = preset_id
        id = self.provider.create(slave)
        slave.id = id
        return slave

    def get_prev(self) -> Optional[int]:
        """
        Get previous context

        :return: previous context
        """
        if self.current is None:
            return None
        idx = self.get_idx_by_id(self.current)
        if idx is not None and idx > 0:
            return self.get_id_by_idx(idx - 1)

    def get_next(self) -> Optional[int]:
        """
        Get next context

        :return: next context
        """
        if self.current is None:
            return None
        idx = self.get_idx_by_id(self.current)
        if idx is not None and idx < self.count_meta() - 1:
            return self.get_id_by_idx(idx + 1)

    def get_last_meta(self) -> Optional[int]:
        """
        Get last context

        :return: last meta
        """
        return self.provider.get_last_meta_id()

    def count_history(
            self,
            history_items: List[CtxItem],
            model: str,
            mode: str,
            used_tokens: int = 100,
            max_tokens: int = 1000
    ) -> Tuple[int, int]:
        """
        Count ctx items to add to prompt

        :param history_items: history items list
        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: ctx items count, ctx tokens count
        """
        i = 0
        tokens = used_tokens
        context_tokens = 0
        from_ctx = self.window.core.tokens.from_ctx
        for item in reversed(history_items):
            num = from_ctx(item, mode, model)
            new_total = tokens + num
            if max_tokens > 0 and new_total > max_tokens:
                break
            tokens = new_total
            context_tokens += num
            i += 1

        return i, context_tokens

    def get_history(
            self,
            history_items: List[CtxItem],
            model: str,
            mode: str = MODE_CHAT,
            used_tokens: int = 100,
            max_tokens: int = 1000,
            ignore_first: bool = True
    ) -> list:
        """
        Return ctx items to add to prompt

        :param history_items: history items list
        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        """
        items = []
        tokens = used_tokens
        is_first = True
        from_ctx = self.window.core.tokens.from_ctx
        for item in reversed(history_items):
            if is_first and ignore_first:
                is_first = False
                continue
            cost = from_ctx(item, mode, model)
            new_total = tokens + cost
            if 0 < max_tokens < new_total:
                break
            tokens = new_total
            items.append(item)

        items.reverse()
        return items

    def count_prompt_items(
            self,
            model: str,
            mode: str,
            used_tokens: int = 100,
            max_tokens: int = 1000
    ) -> Tuple[int, int]:
        """
        Count ctx items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: ctx items count, ctx tokens count
        """
        return self.count_history(
            self.get_items(),
            model,
            mode,
            used_tokens,
            max_tokens,
        )

    def get_prompt_items(
            self,
            model: str,
            mode: str = MODE_CHAT,
            used_tokens: int = 100,
            max_tokens: int = 1000,
            ignore_first: bool = True
    ) -> list:
        """
        Return ctx items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        """
        return self.get_history(
            self.get_items(),
            model,
            mode,
            used_tokens,
            max_tokens,
            ignore_first,
        )

    def get_all_items(self, ignore_first: bool = True) -> list:
        """
        Return all ctx items

        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        """
        items = self.get_items()
        if ignore_first:
            return items[:-1]
        return items[:]

    def check(self, threshold: int, max_total: int):
        """
        Check context and clear if limit exceeded

        :param threshold: threshold
        :param max_total: max total tokens
        """
        if self.get_tokens_left(max_total) <= threshold:
            self.remove_first()

    def get_tokens_left(self, max: int) -> int:
        """
        Return remaining tokens in context

        :param max: max tokens
        :return: remaining tokens in context
        """
        return max - self.get_total_tokens()

    def get_total_tokens(self) -> int:
        """
        Return current prompt tokens

        :return: total tokens
        """
        last = self.get_last()
        if last is not None:
            return last.total_tokens
        return 0

    def get_last_tokens(self) -> int:
        """
        Return last tokens count

        :return: last tokens
        """
        return self.get_total_tokens()

    def remove_last(self):
        """Remove last item"""
        items = self.get_items()
        if items:
            items.pop()

    def duplicate(self, id: int) -> int:
        """
        Duplicate ctx and return new ctx id

        :param id: ctx id
        :return: new ctx id
        """
        if id in self.meta:
            meta = self.create(self.meta[id].group_id)
            new_id = meta.id
            old_data = self.meta[id].to_dict()
            meta.from_dict(old_data)
            meta.id = new_id
            items = self.load(id)
            self.provider.save_all(meta.id, meta, items)
            return meta.id

    def remove_first(self):
        """Remove first item"""
        items = self.get_items()
        if items:
            items.pop(0)

    def set_display_filters(self, filters: dict):
        """
        Update current display filters

        :param filters: filters dict
        """
        self.filters = filters

    def is_allowed_for_mode(
            self,
            mode: str,
            check_assistant: bool = True
    ) -> bool:
        """
        Check if ctx is allowed for this mode

        :param mode: mode name
        :param check_assistant: True if check also current assistant
        :return: True if allowed for mode
        """
        if not self.window.core.config.get('lock_modes'):
            return True

        if self.is_empty():
            return True

        if self.current is None or self.current == '' or not self.has(self.current):
            return True

        meta = self.get_meta_by_id(self.current)

        if meta.last_mode is None:
            return True

        prev_mode = meta.last_mode
        if prev_mode not in self.allowed_modes[mode]:
            if mode == MODE_ASSISTANT:
                if meta.assistant is not None:
                    if meta.assistant == self.window.core.config.get('assistant'):
                        return True
                else:
                    return True
            return False

        if mode == MODE_ASSISTANT and check_assistant:
            if meta.assistant is None:
                return True
            if meta.assistant != self.window.core.config.get('assistant'):
                return False
        return True

    def has_labels(self) -> bool:
        """
        Check if label query is needed

        :return: True if labels not default
        """
        num_all = len(self.window.controller.ui.get_colors())
        return len(self.filters_labels) < num_all

    def load_meta(self):
        """Load ctx list from provider"""
        limit = 0
        if self.window.core.config.has('ctx.records.limit'):
            limit = int(self.window.core.config.get('ctx.records.limit') or 0)

        if "is_important" not in self.filters and "indexed_ts" not in self.filters:
            filters_pinned = self.get_parsed_filters()
            filters_pinned['is_important'] = {
                "mode": "=",
                "value": 1,
            }
            meta_pinned = self.provider.get_meta(
                search_string=self.search_string,
                order_by='updated_ts',
                order_direction='DESC',
                limit=0,
                filters=filters_pinned,
                search_content=self.is_search_content(),
            )

            filters = self.get_parsed_filters()
            meta_unpinned = self.provider.get_meta(
                search_string=self.search_string,
                order_by='updated_ts',
                order_direction='DESC',
                limit=limit,
                filters=filters,
                search_content=self.is_search_content(),
            )

            self.meta = {**meta_pinned, **meta_unpinned}

        else:
            filters = self.get_parsed_filters()
            self.meta = self.provider.get_meta(
                search_string=self.search_string,
                order_by='updated_ts',
                order_direction='DESC',
                limit=limit,
                filters=filters,
                search_content=self.is_search_content(),
            )

    def load_tmp_meta(self, meta_id: int):
        """
        Load tmp meta

        :param meta_id: meta id
        """
        meta = self.provider.get_meta(
            order_by='updated_ts',
            order_direction='DESC',
            limit=1,
            filters={
                "id": {
                    "mode": "=",
                    "value": meta_id,
                },
            }
        )
        if len(meta) > 0:
            self.tmp_meta = next(iter(meta.values()))
            if self.tmp_meta.id not in self.meta:
                self.meta = {self.tmp_meta.id: self.tmp_meta, **self.meta}

    def clear_tmp_meta(self):
        """Clear tmp meta"""
        if self.tmp_meta is not None and self.current != self.tmp_meta.id:
            self.tmp_meta = None

    def get_parsed_filters(self) -> dict:
        """
        Get parsed filters

        :return: parsed filters
        """
        filters = copy.deepcopy(self.filters)
        if self.has_labels():
            filters['label'] = {
                "mode": "IN",
                "value": self.filters_labels,
            }
        return filters

    def load(self, id: int) -> List[CtxItem]:
        """
        Load ctx items from provider and append meta to each item

        :param id: ctx id
        :return: ctx items list
        """
        items = self.provider.load(id)
        meta = self.get_meta_by_id(id)
        for item in items:
            item.meta = meta
        return items

    def load_groups(self):
        """Load groups"""
        self.groups = self.provider.get_groups()

    def has_group(self, id: int) -> bool:
        """
        Check if group exists

        :param id: group id
        :return: True if exists
        """
        return id in self.groups

    def get_groups(self) -> Dict[int, CtxGroup]:
        """
        Get groups

        :return: groups
        """
        if not self.groups_loaded:
            self.load_groups()
            self.groups_loaded = True
        return self.groups

    def get_group_by_id(self, id: int) -> Optional[CtxGroup]:
        """
        Get group by ID

        :param id: group id
        :return: group instance
        """
        if not self.groups_loaded:
            self.load_groups()
            self.groups_loaded = True
        if id not in self.groups:
            return None
        return self.groups[id]

    def update_model_in_current(self, model):
        """
        Update model in current context

        :param model: model name
        """
        if self.current is None:
            return
        meta = self.meta.get(self.current)
        if meta is not None:
            meta.last_model = model
            self.save(self.current)

    def remove_group(
            self,
            group: CtxGroup,
            all: bool = False
    ):
        """
        Remove group

        :param group: group instance
        :param all: remove all items
        """
        self.provider.remove_group(group.id, all=all)
        self.load_groups()

    def truncate_groups(self):
        """Remove all groups"""
        self.provider.truncate_groups()
        self.load_groups()

    def make_group(self, name: str) -> CtxGroup:
        """
        Make group

        :param name: group name
        :return: group instance
        """
        group = CtxGroup()
        group.uuid = str(uuid.uuid4())
        group.name = name
        return group

    def insert_group(self, group: CtxGroup) -> int:
        """
        Insert group

        :param group: group instance
        :return: group id
        """
        id = self.provider.insert_group(group)
        self.load_groups()
        return id

    def update_group(self, group: CtxGroup):
        """
        Update group

        :param group: group instance
        """
        self.provider.update_group(group)
        self.load_groups()

    def update_meta_group_id(self, id: int, group_id: int):
        """
        Update meta group ID

        :param id: meta id
        :param group_id: group id
        """
        meta = self.get_meta_by_id(id)
        if meta is None:
            return
        meta.group_id = group_id
        self.provider.update_meta_group_id(id, group_id)
        self.load_groups()

    def get_items_by_id(self, id: int) -> List[str]:
        """
        Get ctx items by id as string list

        :param id: ctx id
        :return: ctx items list
        """
        items = self.provider.load(id)
        data = []
        for item in items:
            data.append("Human: " + str(item.input) + "\n" + "Assistant: " + str(item.output) + "\n")
        return data

    def get_list_in_date_range(
            self,
            search_string: Optional[str] = None,
            limit: int = 0
    ) -> List[Dict[str, Dict]]:
        """
        Get ctx list in date range

        :param search_string: search string
        :param limit: limit
        :return: ctx list
        """
        meta = self.provider.get_meta(
            search_string=search_string,
            order_by='updated_ts',
            order_direction='DESC',
            limit=limit,
            filters={},
            search_content=self.is_search_content(),
        )
        data = []
        for key in meta:
            item = meta[key]
            data.append({key: {
                "subject": item.name,
                "last_updated": datetime.datetime.fromtimestamp(item.updated).strftime('%Y-%m-%d %H:%M:%S'),
            }})
        return data

    def is_search_content(self) -> bool:
        """
        Check if search in content is enabled

        :return: True if enabled
        """
        return bool(self.window.core.config.get('ctx.search_content'))

    def save(self, id: int):
        """
        Save ctx data

        :param id: ctx id
        """
        self.provider.save(id, self.meta[id], self.get_items())

    def store(self):
        """Store current ctx"""
        cur = self.current
        if cur is not None:
            if cur not in self.meta:
                self.load_tmp_meta(cur)
            if cur in self.meta:
                self.save(cur)

    def reset_meta(self, id: int):
        """
        Reset meta

        :param id: meta id
        """
        if id in self.meta:
            self.provider.clear_meta(id)
            self.meta[id].initialized = False
        self.load_meta()

    def as_previous(self, ctx: CtxItem) -> CtxItem:
        """
        Prepare previous context item and clear current reply results

        :param ctx: CtxItem instance (current)
        :return: CtxItem instance (previous)
        """
        prev_ctx = CtxItem()
        for name in (
            "urls", "urls_before", "images", "images_before", "files", "files_before",
            "attachments", "attachments_before", "results", "index_meta", "doc_ids",
            "input_name", "output_name"
        ):
            setattr(prev_ctx, name, copy.deepcopy(getattr(ctx, name)))
        ctx.clear_reply()
        if len(ctx.cmds) == 0:
            ctx.from_previous()
        return prev_ctx

    def dump(self, ctx: CtxItem) -> str:
        """
        Dump context item

        :param ctx: CtxItem instance
        """
        return self.provider.dump(ctx)

    def reset(self):
        """Reset all data"""
        self.meta = {}
        self.clear_items()
        self.current = None
        self.last_item = None
        self.assistant = None
        self.mode = None
        self.model = None
        self.preset = None
        self.run = None
        self.status = None
        self.thread = None
        self.last_mode = None
        self.last_model = None
        self.tmp_meta = None
        self.search_string = None  # search string
        self.groups = {}  # groups
        self.filters = {}  # search filters
        self.filters_labels = []  # search labels
        self.current_cmd = []  # current commands
        self.current_cmd_schema = ""  # current commands schema
        self.current_sys_prompt = ""
        self.groups_loaded = False