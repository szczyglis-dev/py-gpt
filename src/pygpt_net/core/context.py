#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
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
        Context

        :param config: config object
        """
        self.config = config
        self.contexts = {}
        self.items = []
        self.current_ctx = None

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
        Loads context from file

        :param name: context name (id)
        :return: context items
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
        Parses context data

        :param data: context items data
        :return: context items (deserialized) as objects list
        """
        items = []
        for item in data:
            ctx = ContextItem()
            ctx.deserialize(item)
            items.append(ctx)
        return items

    def create_id(self):
        """
        Creates context ID

        Format: YYYYMMDDHHMMSS.MICROSECONDS.json

        :return: context id
        """
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S.%f")

    def new(self):
        """
        Creates new context

        :return: created context name (id)
        """
        name = self.create_id()  # create unique id
        self.contexts[name] = {
            'id': name,
            "name": "{}".format(trans('ctx.new.prefix')),
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        self.current_ctx = name
        self.items = []
        self.dump_context(name)

        return name

    def dump_context(self, name):
        """
        Dumps context to file

        :param name: context name (id)
        """
        if not self.config.data['store_history']:
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
        Gets context items sorted descending by date

        :return: contexts dict
        """
        return dict(sorted(self.contexts.items(), reverse=True))

    def get_name_by_idx(self, idx):
        """
        Gets context name (id) by index

        :param idx: index
        :return: context name (id)
        """
        i = 0
        for name in self.get_list():
            if i == idx:
                return name
            i += 1

    def get_first_ctx(self):
        """
        Returns first context from list

        :return: context name (id)
        """
        for name in self.get_list():
            return name

    def get_context_by_name(self, name):
        """
        Returns context by name

        :param name: context name (id)
        :return: context dict
        """
        if name in self.contexts:
            return self.contexts[name]

    def delete_ctx(self, name):
        """
        Deletes context by name

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
        """Prepares context for prompt"""
        # if no contexts, create new one
        if len(self.contexts) == 0:
            self.new()

    def delete_all_ctx(self):
        """Deletes all contexts"""
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

    def count_prompt_items(self, model, used_tokens=100, max_tokens=1000):
        """
        Counts context items to add to prompt

        :param model: model
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: context items count, context tokens count
        """
        i = 0
        # loop on items from end to start
        tokens = used_tokens
        context_tokens = 0
        for item in reversed(self.items):
            num = num_tokens_from_context_item(item, model)
            tokens += num
            if tokens > max_tokens:
                break
            context_tokens += num
            i += 1

        return i, context_tokens

    def get_prompt_items(self, model, used_tokens=100, max_tokens=1000):
        """
        Returns context items to add to prompt

        :param model: model
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: context items list
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

    def clear(self):
        """Clears context"""
        self.items = []

    def select(self, name):
        """
        Selects context

        :param name: context name (id)
        """
        if name in self.contexts:
            self.current_ctx = name
            self.items = self.load(name)

    def add(self, item):
        """
        Adds item to contexts and saves context

        :param item: item to add
        """
        self.items.append(item)  # add item to context

        # save context to file
        self.store()

    def store(self):
        """Stores current context to file"""
        if self.current_ctx is not None and self.current_ctx in self.contexts:
            self.dump_context(self.current_ctx)

    def get_total_tokens(self):
        """
        Returns current prompt tokens

        :return: total tokens
        """
        last = self.get_last()
        if last is not None:
            return last.total_tokens
        return 0

    def count(self):
        """
        Counts context items

        :return: context items count
        """
        return len(self.items)

    def all(self):
        """
        Returns context items

        :return: context items
        """
        return self.items

    def get(self, index):
        """
        Returns context item by index

        :param index: item index
        :return: context item
        """
        if index < len(self.items):
            return self.items[index]

    def get_last(self):
        """
        Returns last item from context

        :return: last context item
        """
        if len(self.items) > 0:
            return self.items[-1]
        return None

    def get_tokens_left(self, max):
        """
        Returns remaining tokens in context

        :param max: max tokens
        :return: remaining tokens in context
        """
        return max - self.get_total_tokens()

    def check(self, threshold, max_total):
        """
        Checks context and clear if limit exceeded

        :param threshold: threshold
        :param max_total: max total tokens
        """
        if self.get_tokens_left(max_total) <= threshold:
            self.remove_first()

    def remove_last(self):
        """Removes last item"""
        if len(self.items) > 0:
            self.items.pop()

    def remove_first(self):
        """Removes first item"""
        if len(self.items) > 0:
            self.items.pop(0)

    def get_last_tokens(self):
        """
        Returns last tokens count

        :return: last tokens
        """
        last = self.get_last()
        if last is not None:
            return last.total_tokens
        return 0


class ContextItem:
    def __init__(self, mode=None):
        """
        Context item

        :param mode: Mode (completion or chat)
        """
        self.stream = None
        self.input = None
        self.output = None
        self.mode = mode
        self.input_name = None
        self.output_name = None
        self.input_timestamp = None
        self.output_timestamp = None
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def set_input(self, input, name=None):
        """
        Sets input

        :param input: Input text (prompt)
        :param name: Input person name
        """
        self.input = input
        self.input_name = name
        self.input_timestamp = int(time.time())

    def set_output(self, output, name=None):
        """
        Sets output

        :param output: Output text
        :param name: Output person name
        """
        self.output = output
        self.output_name = name
        self.output_timestamp = int(time.time())

    def set_tokens(self, input_tokens, output_tokens):
        """
        Sets tokens usage

        :param input_tokens: prompt tokens
        :param output_tokens: output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens

    def serialize(self):
        """
        Serializes item to dict

        :return: serialized item
        """
        return {
            'input': self.input,
            'output': self.output,
            'mode': self.mode,
            'input_name': self.input_name,
            'output_name': self.output_name,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'input_timestamp': self.input_timestamp,
            'output_timestamp': self.output_timestamp
        }

    def deserialize(self, data):
        """Deserializes item from dict"""
        if 'input' in data:
            self.input = data['input']
        if 'output' in data:
            self.output = data['output']
        if 'mode' in data:
            self.mode = data['mode']
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
        """Dumps item to string"""
        return json.dumps(self.serialize())
