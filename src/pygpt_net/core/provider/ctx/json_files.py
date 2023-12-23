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
import json
import os

from .base import BaseCtxProvider
from ...ctx_item import ContextItem


class JsonFilesCtxProvider(BaseCtxProvider):
    def __init__(self, window=None):
        super(JsonFilesCtxProvider, self).__init__(window)
        self.window = window
        self.id = "json_files"
        self.type = "ctx"

    def create_id(self):
        """
        Create unique ctx ID

        Format: YYYYMMDDHHMMSS.MICROSECONDS.json

        :return: generated ID
        :rtype: str
        """
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S.%f")

    def get_list(self):
        """Load ctx list from file"""
        contexts = {}
        path = os.path.join(self.window.config.path, 'context.json')
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return contexts
                    contexts = data['items']
        except Exception as e:
            self.window.app.error.log(e)
            contexts = {}

        return contexts

    def load(self, id):
        """
        Load ctx data from json file

        :param id: context id
        :return: context items
        :rtype: list
        """
        data = []
        path = os.path.join(self.window.config.path, 'context', id + '.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding="utf-8") as file:
                    data = self.parse(json.load(file))
                    if data == "" or data is None:
                        return []
            except Exception as e:
                self.window.app.error.log(e)
                print("Error while loading context: {}".format(id))
                data = []
        return data

    def save(self, id, ctx_list, ctx_items):
        """
        Dump ctx to file

        :param id: context id
        :param ctx_list: context list
        :param ctx_items: context items
        """
        try:
            # update current ctx items
            items_path = os.path.join(self.window.config.path, 'context', id + '.json')
            items = []
            for item in ctx_items:
                items.append(self.serialize_item(item))
            dump = json.dumps(items, indent=4)
            with open(items_path, 'w', encoding="utf-8") as f:
                f.write(dump)

            # update ctx index
            index_path = os.path.join(self.window.config.path, 'context.json')
            data = {}
            data['items'] = ctx_list
            data['__meta__'] = self.window.config.append_meta()
            dump = json.dumps(data, indent=4)
            with open(index_path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.app.error.log(e)
            print("Error while dumping context: {}".format(id))

    def remove(self, id):
        """
        Delete ctx by id

        :param id: context id
        """
        path = os.path.join(self.window.config.path, 'context', id + '.json')
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                self.window.app.error.log(e)

    def truncate(self):
        """Delete all ctx"""
        # delete all ctx files
        contexts = self.get_list()
        for id in contexts:
            path = os.path.join(self.window.config.path, 'context', id + '.json')
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    self.window.app.error.log(e)

        # truncate ctx index
        index_path = os.path.join(self.window.config.path, 'context.json')
        data = {}
        data['items'] = {}
        data['__meta__'] = self.window.config.append_meta()
        try:
            dump = json.dumps(data, indent=4)
            with open(index_path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.app.error.log(e)

    def serialize_item(self, ctx):
        """
        Serialize item to dict

        :param ctx: context item
        :return: serialized item
        :rtype: dict
        """
        return {
            'input': ctx.input,
            'output': ctx.output,
            'mode': ctx.mode,
            'thread': ctx.thread,
            'msg_id': ctx.msg_id,
            'run_id': ctx.run_id,
            'input_name': ctx.input_name,
            'output_name': ctx.output_name,
            'input_tokens': ctx.input_tokens,
            'output_tokens': ctx.output_tokens,
            'total_tokens': ctx.total_tokens,
            'input_timestamp': ctx.input_timestamp,
            'output_timestamp': ctx.output_timestamp
        }

    def deserialize_item(self, data, ctx):
        """
        Deserialize item from dict

        :param data: data dict
        :param ctx: context item
        """
        if 'input' in data:
            ctx.input = data['input']
        if 'output' in data:
            ctx.output = data['output']
        if 'mode' in data:
            ctx.mode = data['mode']
        if 'thread' in data:
            ctx.thread = data['thread']
        if 'msg_id' in data:
            ctx.msg_id = data['msg_id']
        if 'run_id' in data:
            ctx.run_id = data['run_id']
        if 'input_name' in data:
            ctx.input_name = data['input_name']
        if 'output_name' in data:
            ctx.output_name = data['output_name']
        if 'input_tokens' in data:
            ctx.input_tokens = data['input_tokens']
        if 'output_tokens' in data:
            ctx.output_tokens = data['output_tokens']
        if 'total_tokens' in data:
            ctx.total_tokens = data['total_tokens']
        if 'input_timestamp' in data:
            ctx.input_timestamp = data['input_timestamp']
        if 'output_timestamp' in data:
            ctx.output_timestamp = data['output_timestamp']

    def dump(self, ctx):
        """
        Dump ctx to string

        :return: dumped item
        :rtype: str
        """
        return json.dumps(self.serialize_item(ctx))

    def parse(self, data):
        """
        Parse context data from json to objects

        :param data: context items data
        :return: context items (deserialized) as objects list
        :rtype: list
        """
        items = []
        for item in data:
            ctx = ContextItem()
            self.deserialize_item(item, ctx)
            items.append(ctx)
        return items
