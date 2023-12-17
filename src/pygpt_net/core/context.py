#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

import datetime
import json
import os
import time

from .tokens import num_tokens_from_context_item
from .utils import trans


class Context:
    def __init__(self, config=None):
        """
        Context handler

        :param config: Config instance
        """
        self.config = config
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

    def load_list(self):
        """Loads contexts list from file"""
        path = os.path.join(self.config.path, 'context.json')
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    file.close()
                    if data == "" or data is None or 'items' not in data:
                        self.contexts = {}
                        return
                    self.contexts = data['items']
        except Exception as e:
            print(e)
            self.contexts = {}

    def load(self, name):
        """
        Load context from file

        :param name: context name (id)
        :return: context items
        :rtype: list
        """
        path = os.path.join(self.config.path, 'context', name + '.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding="utf-8") as file:
                    data = self.parse(json.load(file))
                    file.close()
                    if data == "" or data is None:
                        return []
                    return data
            except Exception as e:
                print("Error while loading context: {}".format(name))
                print(e)
                return []
        else:
            return []

    def parse(self, data):
        """
        Parse context data

        :param data: context items data
        :return: context items (deserialized) as objects list
        :rtype: list
        """
        items = []
        for item in data:
            ctx = ContextItem()
            ctx.deserialize(item)
            items.append(ctx)
        return items

    def update(self):
        """
        Update current context parent (when context item load from the list or setting mode)
        """
        self.current_mode = self.config.get('mode')

        if self.current_ctx is None:
            return
        self.contexts[self.current_ctx]['mode'] = self.current_mode
        self.dump_context(self.current_ctx)

    def post_update(self, mode):
        """
        Update current (last) context data

        :param mode: mode name
        """
        if self.current_ctx is None:
            return

        # update current
        self.current_assistant = self.config.get('assistant')  # update assistant
        self.current_preset = self.config.get('preset')  # update preset

        # update current context data
        self.contexts[self.current_ctx]['last_mode'] = mode
        self.contexts[self.current_ctx]['preset'] = self.current_preset

        # if assistant then update assistant
        if mode == 'assistant':
            self.contexts[self.current_ctx]['assistant'] = self.current_assistant

        # save context
        self.dump_context(self.current_ctx)

    def create_id(self):
        """
        Create context ID

        Format: YYYYMMDDHHMMSS.MICROSECONDS.json

        :return: Generated ID
        :rtype: str
        """
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S.%f")

    def new(self):
        """
        Create new context

        :return: created context name (id)
        :rtype: str
        """
        name = self.create_id()  # create unique id
        self.contexts[name] = {
            'id': name,
            "name": "{}".format(trans('ctx.new.prefix')),
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            'mode': self.config.get('mode'),
            'last_mode': self.config.get('mode'),
            'thread': None,
            'assistant': None,
            'preset': None,
            'run': None,
            'status': None,
            'initialized': False,
        }
        self.current_ctx = name
        self.current_thread = None
        self.current_assistant = None
        self.current_mode = self.config.get('mode')
        self.current_preset = self.config.get('preset')
        self.items = []
        self.dump_context(name)

        return name

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
            self.dump_context(self.current_ctx)

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
            self.dump_context(self.current_ctx)

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
            self.dump_context(self.current_ctx)

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
            self.dump_context(self.current_ctx)

    def dump_context(self, name):
        """
        Dump context to file

        :param name: context name (id)
        """
        if not self.config.get('store_history'):
            return

        try:
            # update current context items
            items_path = os.path.join(self.config.path, 'context', name + '.json')
            items = []
            for item in self.items:
                items.append(item.serialize())
            dump = json.dumps(items, indent=4)
            with open(items_path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

            # update contexts index
            index_path = os.path.join(self.config.path, 'context.json')
            data = {}
            data['items'] = self.contexts.copy()
            data['__meta__'] = self.config.append_meta()
            dump = json.dumps(data, indent=4)
            with open(index_path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

        except Exception as e:
            print("Error while dumping context: {}".format(name))
            print(e)

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

    def delete_ctx(self, name):
        """
        Delete context by name

        :param name: context name (id)
        """
        if name in self.contexts:
            del self.contexts[name]
            path = os.path.join(self.config.path, 'context', name + '.json')
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(e)

    def prepare(self):
        """Prepare context for prompt"""
        # if no contexts, create new one
        if len(self.contexts) == 0:
            self.new()

    def delete_all_ctx(self):
        """Delete all contexts"""
        # delete all context files
        for name in self.contexts:
            path = os.path.join(self.config.path, 'context', name + '.json')
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(e)
        self.contexts = {}

        # update contexts index
        index_path = os.path.join(self.config.path, 'context.json')
        data = {}
        data['items'] = {}
        data['__meta__'] = self.config.append_meta()
        try:
            dump = json.dumps(data, indent=4)
            with open(index_path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()
        except Exception as e:
            print(e)

        # delete all txt history files from history dir
        path = os.path.join(self.config.path, 'history')
        for file in os.listdir(path):
            if file.endswith('.txt'):
                try:
                    os.remove(os.path.join(path, file))
                except Exception as e:
                    print(e)

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
            self.dump_context(self.current_ctx)

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


class ContextItem:
    def __init__(self, mode=None):
        """
        Context item

        :param mode: Mode (completion, chat, img, vision, langchain, assistant)
        """
        self.stream = None
        self.results = []
        self.reply = False
        self.input = None
        self.output = None
        self.mode = mode
        self.thread = None
        self.msg_id = None
        self.run_id = None
        self.input_name = None
        self.output_name = None
        self.input_timestamp = None
        self.output_timestamp = None
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def set_input(self, input, name=None):
        """
        Set input

        :param input: input text (prompt)
        :param name: input person name
        """
        self.input = input
        self.input_name = name
        self.input_timestamp = int(time.time())

    def set_output(self, output, name=None):
        """
        Set output

        :param output: output text
        :param name: output person name
        """
        self.output = output
        self.output_name = name
        self.output_timestamp = int(time.time())

    def set_tokens(self, input_tokens, output_tokens):
        """
        Set tokens usage

        :param input_tokens: prompt tokens
        :param output_tokens: output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens

    def serialize(self):
        """
        Serialize item to dict

        :return: serialized item
        :rtype: dict
        """
        return {
            'input': self.input,
            'output': self.output,
            'mode': self.mode,
            'thread': self.thread,
            'msg_id': self.msg_id,
            'run_id': self.run_id,
            'input_name': self.input_name,
            'output_name': self.output_name,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'input_timestamp': self.input_timestamp,
            'output_timestamp': self.output_timestamp
        }

    def deserialize(self, data):
        """
        Deserialize item from dict

        :param data: data dict
        """
        if 'input' in data:
            self.input = data['input']
        if 'output' in data:
            self.output = data['output']
        if 'mode' in data:
            self.mode = data['mode']
        if 'thread' in data:
            self.thread = data['thread']
        if 'msg_id' in data:
            self.msg_id = data['msg_id']
        if 'run_id' in data:
            self.run_id = data['run_id']
        if 'input_name' in data:
            self.input_name = data['input_name']
        if 'output_name' in data:
            self.output_name = data['output_name']
        if 'input_tokens' in data:
            self.input_tokens = data['input_tokens']
        if 'output_tokens' in data:
            self.output_tokens = data['output_tokens']
        if 'total_tokens' in data:
            self.total_tokens = data['total_tokens']
        if 'input_timestamp' in data:
            self.input_timestamp = data['input_timestamp']
        if 'output_timestamp' in data:
            self.output_timestamp = data['output_timestamp']

    def dump(self):
        """
        Dump item to string

        :return: dumped item
        :rtype: str
        """
        return json.dumps(self.serialize())
