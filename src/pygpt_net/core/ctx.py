#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

import datetime
import os

from .item.ctx import CtxItem, CtxMeta
from .tokens import num_tokens_from_context_item
from .provider.ctx.json_file import JsonFileProvider
from .utils import trans


class Ctx:
    def __init__(self, window=None):
        """
        Context handler

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_file"
        self.meta = {}
        self.items = []
        self.current = None
        self.assistant = None
        self.mode = None
        self.preset = None
        self.run = None
        self.status = None
        self.thread = None
        self.last_mode = None

        # register data providers
        self.add_provider(JsonFileProvider())  # json file provider

    def add_provider(self, provider):
        """
        Add ctx provider

        :param provider: ctx provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].window = self.window

    def install(self):
        """Install provider data"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].install()
            except Exception as e:
                self.window.app.errors.log(e)

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

            self.items = self.load(id)

    def new(self):
        """
        Create new ctx and set as current

        :return: CtxMeta instance (new ctx meta)
        :rtype: CtxMeta
        """
        meta = self.create()  # create new ctx meta

        if meta is None:
            self.window.app.errors.log("Error creating new ctx")
            return

        self.meta[meta.id] = meta
        self.current = meta.id
        self.thread = None
        self.assistant = None
        self.mode = self.window.app.config.get('mode')
        self.preset = self.window.app.config.get('preset')
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
        meta.mode = self.window.app.config.get('mode')
        meta.last_mode = self.window.app.config.get('mode')
        meta.initialized = False
        return meta

    def create(self):
        """
        Send created meta to provider and return new ID

        :return: created ID
        """
        meta = self.build()
        if self.provider in self.providers:
            try:
                id = self.providers[self.provider].create(meta)
                meta.id = id
                return meta
            except Exception as e:
                self.window.app.errors.log(e)

    def add(self, item):
        """
        Add CtxItem to contexts and saves context

        :param item: CtxItem to append
        """
        self.items.append(item)  # add CtxItem to context items

        # save context to file
        self.store()

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
        self.mode = self.window.app.config.get('mode')

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
        self.assistant = self.window.app.config.get('assistant')  # update assistant
        self.preset = self.window.app.config.get('preset')  # update preset

        # update current meta
        self.meta[self.current].last_mode = mode
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

    def get_meta(self):
        """
        Get ctx items sorted descending by date

        :return: ctx metas dict
        """
        return dict(sorted(self.meta.items(), reverse=True))

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
        :return: ctx dict
        :rtype: dict or None
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
            if self.provider in self.providers:
                try:
                    self.providers[self.provider].remove(id)
                except Exception as e:
                    self.window.app.errors.log(e)

    def truncate(self):
        """Delete all ctx"""
        # empty ctx index
        self.meta = {}

        # remove all ctx data in provider
        if self.provider in self.providers:
            try:
                self.providers[self.provider].truncate()
            except Exception as e:
                self.window.app.errors.log(e)

        # delete all txt history files from history dir
        path = os.path.join(self.window.app.config.path, 'history')
        for file in os.listdir(path):
            if file.endswith('.txt'):
                try:
                    os.remove(os.path.join(path, file))
                except Exception as e:
                    self.window.app.errors.log(e)

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
            num = num_tokens_from_context_item(item, mode, model)  # get num tokens for input and output
            tokens += num
            if tokens > max_tokens:
                break
            context_tokens += num
            i += 1

        return i, context_tokens

    def get_prompt_items(self, model, used_tokens=100, max_tokens=1000):
        """
        Return ctx items to add to prompt

        :param model: model
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: context items list
        :rtype: list
        """
        items = []
        # loop on items from end to start
        tokens = used_tokens
        for item in reversed(self.items):
            tokens += num_tokens_from_context_item(item, model)
            if tokens > max_tokens:
                break
            items.append(item)

        # reverse items
        items.reverse()
        return items

    def get_all_items(self):
        """
        Return all ctx items

        :return: ctx items list
        :rtype: list
        """
        items = []
        for item in reversed(self.items):
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

    def load_meta(self):
        """Load ctx list from provider"""
        if self.provider in self.providers:
            try:
                self.meta = self.providers[self.provider].get_meta()
            except Exception as e:
                self.window.app.errors.log(e)
                self.meta = {}

    def load(self, id):
        """
        Load ctx data from provider

        :param id: ctx id
        :return: ctx items
        :rtype: list
        """
        if self.provider in self.providers:
            try:
                return self.providers[self.provider].load(id)
            except Exception as e:
                self.window.app.errors.log(e)
        return []

    def save(self, id):
        """
        Save ctx data

        :param id: ctx id
        """
        if not self.window.app.config.get('store_history'):
            return

        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(id, self.meta[id], self.items)
            except Exception as e:
                self.window.app.errors.log(e)

    def store(self):
        """Store current ctx"""
        if self.current is not None and self.current in self.meta:
            self.save(self.current)

    def dump(self, ctx):
        """
        Dump context item

        :param ctx: CtxItem instance
        """
        if self.provider in self.providers:
            try:
                return self.providers[self.provider].dump(ctx)
            except Exception as e:
                self.window.app.errors.log(e)
