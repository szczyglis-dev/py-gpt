#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 19:00:00                  #
# ================================================== #

import datetime
import os

from .ctx_item import ContextItem
from .tokens import num_tokens_from_context_item
from .provider.ctx.json_files import JsonFilesCtxProvider
from .utils import trans


class Context:
    def __init__(self, window=None):
        """
        Context handler

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_files"
        self.contexts = {}
        self.items = []
        self.current_ctx = None
        self.current_assistant = None
        self.current_thread = None
        self.current_run = None
        self.current_status = None
        self.current_preset = None
        self.current_mode = None
        self.last_mode = None

        # register ctx data providers
        self.add_provider(JsonFilesCtxProvider())  # json files provider

    def add_provider(self, provider):
        """
        Add context provider

        :param provider: Context provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].window = self.window

    def load_list(self):
        """Load ctx list from provider"""
        if self.provider in self.providers:
            try:
                self.contexts = self.providers[self.provider].get_list()
            except Exception as e:
                self.window.app.error.log(e)
                self.contexts = {}

    def load(self, id):
        """
        Load ctx data from provider

        :param id: context id
        :return: context items
        :rtype: list
        """
        if self.provider in self.providers:
            try:
                return self.providers[self.provider].load(id)
            except Exception as e:
                self.window.app.error.log(e)
        return []

    def update(self):
        """
        Update current context parent (when context item load from the list or setting mode)
        """
        self.current_mode = self.window.config.get('mode')

        if self.current_ctx is None:
            return
        self.contexts[self.current_ctx]['mode'] = self.current_mode
        self.save(self.current_ctx)

    def post_update(self, mode):
        """
        Update current (last) context data

        :param mode: mode name
        """
        if self.current_ctx is None:
            return

        # update current
        self.current_assistant = self.window.config.get('assistant')  # update assistant
        self.current_preset = self.window.config.get('preset')  # update preset

        # update current context data
        self.contexts[self.current_ctx]['last_mode'] = mode
        self.contexts[self.current_ctx]['preset'] = self.current_preset

        # if assistant then update assistant
        if mode == 'assistant':
            self.contexts[self.current_ctx]['assistant'] = self.current_assistant

        # save context
        self.save(self.current_ctx)

    def create_id(self):
        """
        Create unique context ID

        :return: generated ID
        :rtype: str
        """
        if self.provider in self.providers:
            try:
                return self.providers[self.provider].create_id()
            except Exception as e:
                self.window.app.error.log(e)

    def is_empty(self):
        """
        Check if context is empty

        :return: true if empty, false otherwise
        :rtype: bool
        """
        if self.current_ctx is None:
            return True
        else:
            if len(self.items) == 0:
                return True
        return False

    def new(self):
        """
        Create new context

        :return: created context name (id)
        :rtype: str
        """
        id = self.create_id()  # create unique id
        self.contexts[id] = {
            'id': id,
            "name": "{}".format(trans('ctx.new.prefix')),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            'mode': self.window.config.get('mode'),
            'last_mode': self.window.config.get('mode'),
            'thread': None,
            'assistant': None,
            'preset': None,
            'run': None,
            'status': None,
            'initialized': False,
        }
        self.current_ctx = id
        self.current_thread = None
        self.current_assistant = None
        self.current_mode = self.window.config.get('mode')
        self.current_preset = self.window.config.get('preset')
        self.items = []
        self.save(id)

        return id

    def is_ctx_initialized(self):
        """
        Check if context is initialized (name assigned)

        :return: true if initialized, False otherwise
        :rtype: bool
        """
        if self.current_ctx is None:
            return
        if self.current_ctx in self.contexts:
            if 'initialized' in self.contexts[self.current_ctx]:
                return self.contexts[self.current_ctx]['initialized']
        return True  # old versions compatibility

    def set_ctx_initialized(self):
        """
        Set context as initialized (name assigned)
        """
        if self.current_ctx is None:
            return
        if self.current_ctx in self.contexts:
            self.contexts[self.current_ctx]['initialized'] = True
            self.save(self.current_ctx)

    def append_thread(self, thread):
        """
        Append thread to context

        :param thread: thread ID
        """
        self.current_thread = thread
        if self.current_ctx is None:
            return
        if self.current_ctx in self.contexts:
            self.contexts[self.current_ctx]['thread'] = self.current_thread
            self.save(self.current_ctx)

    def append_run(self, run):
        """
        Append run ID to context

        :param run: run ID
        """
        self.current_run = run
        if self.current_ctx is None:
            return
        if self.current_ctx in self.contexts:
            self.contexts[self.current_ctx]['run'] = self.current_run
            self.save(self.current_ctx)

    def append_status(self, status):
        """
        Append status to context

        :param status: status
        """
        self.current_status = status
        if self.current_ctx is None:
            return
        if self.current_ctx in self.contexts:
            self.contexts[self.current_ctx]['status'] = self.current_status
            self.save(self.current_ctx)

    def save(self, id):
        """
        Dump context to file

        :param id: context id
        """
        if not self.window.config.get('store_history'):
            return

        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(id, self.contexts.copy(), self.items)
            except Exception as e:
                self.window.app.error.log(e)

    def get_list(self):
        """
        Get context items sorted descending by date

        :return: contexts dict
        """
        return dict(sorted(self.contexts.items(), reverse=True))

    def get_name_by_idx(self, idx):
        """
        Get context name (id) by index

        :param idx: index
        :return: context name (id)
        :rtype: str or None
        """
        i = 0
        for name in self.get_list():
            if i == idx:
                return name
            i += 1

    def get_idx_by_name(self, ctx):
        """
        Get context index by name (id)

        :param ctx: name (id)
        :return: idx
        :rtype: int or None
        """
        items = self.get_list()
        if ctx in items:
            return list(items.keys()).index(ctx)

    def get_first_ctx(self):
        """
        Return first context from list

        :return: context name (id)
        :rtype: str or None
        """
        for name in self.get_list():
            return name

    def get_context_by_name(self, name):
        """
        Return context by name

        :param name: context name (id)
        :return: context dict
        :rtype: dict or None
        """
        if name in self.contexts:
            return self.contexts[name]

    def delete_ctx(self, id):
        """
        Delete context by id

        :param id: context id
        """
        if id in self.contexts:
            del self.contexts[id]
            if self.provider in self.providers:
                try:
                    self.providers[self.provider].remove(id)
                except Exception as e:
                    self.window.app.error.log(e)

    def truncate(self):
        """Delete all ctx"""
        # empty ctx index
        self.contexts = {}

        # remove all ctx data in provider
        if self.provider in self.providers:
            try:
                self.providers[self.provider].truncate()
            except Exception as e:
                self.window.app.error.log(e)

        # delete all txt history files from history dir
        path = os.path.join(self.window.config.path, 'history')
        for file in os.listdir(path):
            if file.endswith('.txt'):
                try:
                    os.remove(os.path.join(path, file))
                except Exception as e:
                    self.window.app.error.log(e)

    def prepare(self):
        """Prepare context for prompt"""
        # if no contexts, create new one
        if len(self.contexts) == 0:
            self.new()

    def count_prompt_items(self, model, mode, used_tokens=100, max_tokens=1000):
        """
        Count context items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: context items count, context tokens count
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
        Return context items to add to prompt

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
        Return all context items

        :return: context items list
        :rtype: list
        """
        items = []
        for item in reversed(self.items):
            items.append(item)

        # reverse items
        items.reverse()
        return items

    def clear(self):
        """Clears context"""
        self.items = []

    def select(self, name):
        """
        Select context

        :param name: context name (id)
        """
        if name in self.contexts:
            ctx = self.contexts[name]
            self.current_ctx = name

            # reset
            self.current_thread = None
            self.current_mode = None
            self.current_assistant = None

            # restore
            if 'thread' in ctx:
                self.current_thread = ctx['thread']
            if 'mode' in ctx:
                self.current_mode = ctx['mode']
            if 'assistant' in ctx:
                self.current_assistant = ctx['assistant']
            if 'preset' in ctx:
                self.current_preset = ctx['preset']

            self.items = self.load(name)

    def add(self, item):
        """
        Add item to contexts and saves context

        :param item: item to add
        """
        self.items.append(item)  # add item to context

        # save context to file
        self.store()

    def store(self):
        """Store current context to file"""
        if self.current_ctx is not None and self.current_ctx in self.contexts:
            self.save(self.current_ctx)

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

    def count(self):
        """
        Count context items

        :return: context items count
        :rtype: int
        """
        return len(self.items)

    def all(self):
        """
        Return context items

        :return: context items
        :rtype: list
        """
        return self.items

    def get(self, index):
        """
        Return context item by index

        :param index: item index
        :return: context item
        :rtype: ContextItem or None
        """
        if index < len(self.items):
            return self.items[index]

    def get_last(self):
        """
        Return last item from context

        :return: last context item
        :rtype: ContextItem or None
        """
        if len(self.items) > 0:
            return self.items[-1]
        return None

    def get_tokens_left(self, max):
        """
        Return remaining tokens in context

        :param max: max tokens
        :return: remaining tokens in context
        :rtype: int
        """
        return max - self.get_total_tokens()

    def check(self, threshold, max_total):
        """
        Check context and clear if limit exceeded

        :param threshold: threshold
        :param max_total: max total tokens
        """
        if self.get_tokens_left(max_total) <= threshold:
            self.remove_first()

    def remove_last(self):
        """Remove last item"""
        if len(self.items) > 0:
            self.items.pop()

    def remove_first(self):
        """Remove first item"""
        if len(self.items) > 0:
            self.items.pop(0)

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
