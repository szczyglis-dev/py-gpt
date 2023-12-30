#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

import datetime
import os

from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.provider.ctx.db_sqlite import DbSqliteProvider
from pygpt_net.utils import trans


class Ctx:
    def __init__(self, window=None):
        """
        Context handler

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.meta = {}
        self.items = []
        self.current = None
        self.assistant = None
        self.mode = None
        self.model = None
        self.preset = None
        self.run = None
        self.status = None
        self.thread = None
        self.last_mode = None
        self.last_model = None
        self.search_string = None
        self.allowed_modes = {
            'chat': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'completion': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'img': ['img'],
            'langchain': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'vision': ['chat', 'completion', 'img', 'langchain', 'vision', 'assistant'],
            'assistant': ['assistant'],
        }

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version):
        """Patch provider data"""
        self.provider.patch(app_version)

    def select(self, id):
        """
        Select ctx

        :param id: context id
        """
        if id in self.meta:
            ctx = self.meta[id]
            self.current = id

            # reset
            self.thread = None
            self.mode = None
            self.assistant = None

            # restore
            self.thread = ctx.thread
            self.mode = ctx.mode
            self.assistant = ctx.assistant
            self.preset = ctx.preset

            # restore model if exists in current mode
            if ctx.last_model is not None and self.window.core.models.has_model(self.mode, ctx.last_model):
                self.model = ctx.last_model
            elif ctx.model is not None and self.window.core.models.has_model(self.mode, ctx.model):
                self.model = ctx.model

            self.items = self.load(id)

    def new(self):
        """
        Create new ctx and set as current

        :return: CtxMeta instance (new ctx meta)
        :rtype: CtxMeta
        """
        meta = self.create()  # create new ctx meta
        if meta is None:
            self.window.core.debug.log("Error creating new ctx")
            return

        self.meta[meta.id] = meta
        self.current = meta.id
        self.thread = None
        self.assistant = None
        self.mode = self.window.core.config.get('mode')
        self.model = self.window.core.config.get('model')
        self.preset = self.window.core.config.get('preset')
        self.items = []
        self.save(meta.id)

        return meta

    def build(self):
        """
        Build new ctx

        :return: created CtxMeta instance
        :rtype: CtxMeta
        """
        meta = CtxMeta()  # create ctx meta
        meta.name = "{}".format(trans('ctx.new.prefix'))
        meta.date = datetime.datetime.now().strftime("%Y-%m-%d")
        meta.mode = self.window.core.config.get('mode')
        meta.model = self.window.core.config.get('model')
        meta.last_mode = self.window.core.config.get('mode')
        meta.last_model = self.window.core.config.get('model')
        meta.initialized = False
        return meta

    def create(self):
        """
        Send created meta to provider and return new ID

        :return: created ID
        """
        meta = self.build()
        id = self.provider.create(meta)
        meta.id = id
        return meta

    def add(self, item):
        """
        Add CtxItem to contexts and saves context

        :param item: CtxItem to append
        """
        self.items.append(item)  # add CtxItem to context items

        # append in provider
        if self.current is not None and self.current in self.meta:
            meta = self.meta[self.current]
            result = self.provider.append_item(meta, item)
            if not result:
                self.store()  # if not stored, e.g. in JSON file provider, then store whole ctx (save all)

    def update_item(self, item):
        """
        Update CtxItem in context

        :param item: CtxItem to update
        """
        self.provider.update_item(item)

    def is_empty(self):
        """
        Check if ctx is empty

        :return: true if empty, false otherwise
        :rtype: bool
        """
        if self.current is None:
            return True
        else:
            if len(self.items) == 0:
                return True
        return False

    def update(self):
        """
        Update current parent (when ctx item load from the list or setting mode)
        """
        self.mode = self.window.core.config.get('mode')

        if self.current is None:
            return
        self.meta[self.current].mode = self.mode
        self.save(self.current)

    def post_update(self, mode):
        """
        Update current (last) ctx data

        :param mode: mode name
        """
        if self.current is None:
            return

        # update current
        self.assistant = self.window.core.config.get('assistant')  # update assistant
        self.preset = self.window.core.config.get('preset')  # update preset
        self.model = self.window.core.config.get('model')  # get current model

        # update current meta
        self.meta[self.current].last_mode = mode
        self.meta[self.current].last_model = self.model
        self.meta[self.current].preset = self.preset

        # if assistant then update assistant
        if mode == 'assistant':
            self.meta[self.current].assistant = self.assistant

        # save ctx
        self.save(self.current)

    def is_initialized(self):
        """
        Check if ctx is initialized (name assigned)

        :return: true if initialized, false otherwise
        :rtype: bool
        """
        if self.current is None:
            return
        if self.current in self.meta:
            return self.meta[self.current].initialized

    def set_initialized(self):
        """
        Set ctx as initialized (name assigned)
        """
        if self.current is None:
            return
        if self.current in self.meta:
            self.meta[self.current].initialized = True
            self.save(self.current)

    def has(self, id):
        """
        Check if ctx meta exists

        :param id: ctx ID
        :return: true if exists, false otherwise
        :rtype: bool
        """
        if id in self.meta:
            return True
        return False

    def get(self, idx):
        """
        Return ctx item by index

        :param idx: item index
        :return: context item
        :rtype: CtxItem or None
        """
        if idx < len(self.items):
            return self.items[idx]

    def get_meta(self, reload=False):
        """
        Get ctx items sorted descending by date

        :return: ctx metas dict
        """
        if reload:
            self.load_meta()
        return self.meta

    def get_id_by_idx(self, idx):
        """
        Get ctx id (id) by index

        :param idx: index
        :return: ctx id
        :rtype: str or None
        """
        i = 0
        for id in self.get_meta():
            if i == idx:
                return id
            i += 1

    def get_idx_by_id(self, id):
        """
        Get ctx index by id

        :param id: id
        :return: idx
        :rtype: int or None
        """
        items = self.get_meta()
        if id in items:
            return list(items.keys()).index(id)

    def get_first(self):
        """
        Return first ctx ID from list

        :return: ctx id
        :rtype: str or None
        """
        for id in self.get_meta():
            return id

    def get_meta_by_id(self, id):
        """
        Return ctx meta by id

        :param id: ctx id
        :return: ctx meta object
        :rtype: CtxMeta or None
        """
        if id in self.meta:
            return self.meta[id]

    def get_last(self):
        """
        Return last item from ctx

        :return: last ctx item
        :rtype: CtxItem or None
        """
        if len(self.items) > 0:
            return self.items[-1]
        return None

    def prepare(self):
        """Prepare context for prompt"""
        # if no contexts, create new one
        if len(self.meta) == 0:
            self.new()

    def count(self):
        """
        Count ctx items

        :return: ctx items count
        :rtype: int
        """
        return len(self.items)

    def count_meta(self):
        """
        Count ctx meta items

        :return: ctx meta count
        :rtype: int
        """
        return len(self.meta)

    def all(self):
        """
        Return ctx items

        :return: ctx items
        :rtype: list
        """
        return self.items

    def remove(self, id):
        """
        Delete ctx by id

        :param id: ctx id
        """
        if id in self.meta:
            del self.meta[id]
            self.provider.remove(id)

    def truncate(self):
        """Delete all ctx"""
        # empty ctx index
        self.meta = {}

        # remove all ctx data in provider
        self.provider.truncate()

        # delete all txt history files from history dir
        path = os.path.join(self.window.core.config.path, 'history')
        for file in os.listdir(path):
            if file.endswith('.txt'):
                try:
                    os.remove(os.path.join(path, file))
                except Exception as e:
                    self.window.core.debug.log(e)

    def clear(self):
        """Clear ctx items"""
        self.items = []

    def append_thread(self, thread):
        """
        Append thread ID to ctx

        :param thread: thread ID
        """
        self.thread = thread
        if self.current is None:
            return
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
        if self.current in self.meta:
            self.meta[self.current].run = self.run
            self.save(self.current)

    def append_status(self, status):
        """
        Append status to ctx

        :param status: status
        """
        self.status = status
        if self.current is None:
            return
        if self.current in self.meta:
            self.meta[self.current].status = self.status
            self.save(self.current)

    def count_prompt_items(self, model, mode, used_tokens=100, max_tokens=1000):
        """
        Count ctx items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: context items count, ctx tokens count
        :rtype: (int, int)
        """
        i = 0
        # loop on items from end to start
        tokens = used_tokens
        context_tokens = 0
        for item in reversed(self.items):
            num = self.window.core.tokens.from_ctx(item, mode, model)  # get num tokens for input and output
            tokens += num
            if tokens > max_tokens:
                break
            context_tokens += num
            i += 1

        return i, context_tokens

    def get_prompt_items(self, model, mode="chat", used_tokens=100, max_tokens=1000, ignore_first=True):
        """
        Return ctx items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :param ignore_first: ignore current item (provided by user)
        :return: context items list
        :rtype: list
        """
        items = []
        # loop on items from end to start
        tokens = used_tokens
        is_first = True
        for item in reversed(self.items):
            if is_first and ignore_first:
                is_first = False
                continue
            tokens += self.window.core.tokens.from_ctx(item, mode, model)
            if tokens > max_tokens:
                break
            items.append(item)

        # reverse items
        items.reverse()
        return items

    def get_all_items(self, ignore_first=True):
        """
        Return all ctx items

        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        :rtype: list
        """
        items = []
        is_first = True
        for item in reversed(self.items):
            if is_first and ignore_first:
                is_first = False
                continue
            items.append(item)

        # reverse items
        items.reverse()
        return items

    def check(self, threshold, max_total):
        """
        Check context and clear if limit exceeded

        :param threshold: threshold
        :param max_total: max total tokens
        """
        if self.get_tokens_left(max_total) <= threshold:
            self.remove_first()

    def get_tokens_left(self, max):
        """
        Return remaining tokens in context

        :param max: max tokens
        :return: remaining tokens in context
        :rtype: int
        """
        return max - self.get_total_tokens()

    def get_total_tokens(self):
        """
        Return current prompt tokens

        :return: total tokens
        :rtype: int
        """
        last = self.get_last()
        if last is not None:
            return last.total_tokens
        return 0

    def get_last_tokens(self):
        """
        Return last tokens count

        :return: last tokens
        :rtype: int
        """
        last = self.get_last()
        if last is not None:
            return last.total_tokens
        return 0

    def remove_last(self):
        """Remove last item"""
        if len(self.items) > 0:
            self.items.pop()

    def remove_first(self):
        """Remove first item"""
        if len(self.items) > 0:
            self.items.pop(0)

    def is_allowed_for_mode(self, mode, check_assistant=True):
        """
        Check if ctx is allowed for this mode

        :param mode: mode name
        :param check_assistant: True if check also current assistant
        :return: True if allowed for mode
        :rtype: bool
        """
        # always allow if lock_modes is disabled
        if not self.window.core.config.get('lock_modes'):
            return True

        if self.is_empty():
            return True

        # always allow if no ctx
        if self.current is None or self.current == '' or not self.has(self.current):
            return True

        meta = self.get_meta_by_id(self.current)

        # always allow if no last mode
        if meta.last_mode is None:
            return True

        # get last used mode from ctx meta
        prev_mode = meta.last_mode
        if prev_mode not in self.allowed_modes[mode]:
            # exception for assistant (if assistant exists in ctx then allow)
            if mode == 'assistant':
                if meta.assistant is not None:
                    # if the same assistant then allow
                    if meta.assistant == self.window.core.config.get('assistant'):
                        return True
                else:
                    return True  # if no assistant in ctx then allow
            # if other mode, then always disallow
            return False

        # check if the same assistant
        if mode == 'assistant' and check_assistant:
            # allow if no assistant yet in ctx
            if meta.assistant is None:
                return True
            # disallow if different assistant
            if meta.assistant != self.window.core.config.get('assistant'):
                return False
        return True

    def load_meta(self):
        """Load ctx list from provider"""
        limit = 0
        if self.window.core.config.has('ctx.records.limit'):
            limit = int(self.window.core.config.get('ctx.records.limit') or 0)
        self.meta = self.provider.get_meta(self.search_string, 'updated_ts', 'DESC', limit)

    def load(self, id):
        """
        Load ctx data from provider

        :param id: ctx id
        :return: ctx items
        :rtype: list
        """
        return self.provider.load(id)

    def save(self, id):
        """
        Save ctx data

        :param id: ctx id
        """
        if not self.window.core.config.get('store_history'):
            return

        self.provider.save(id, self.meta[id], self.items)

    def store(self):
        """Store current ctx"""
        if self.current is not None and self.current in self.meta:
            self.save(self.current)

    def dump(self, ctx):
        """
        Dump context item

        :param ctx: CtxItem instance
        """
        return self.provider.dump(ctx)
