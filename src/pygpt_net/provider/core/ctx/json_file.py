#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import datetime
import json
import os

from packaging.version import Version

from pygpt_net.provider.core.ctx.base import BaseProvider
from pygpt_net.item.ctx import CtxItem, CtxMeta


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "ctx"

    def install(self):
        """
        Install provider data
        """
        context_dir = os.path.join(self.window.core.config.path, 'context')
        if not os.path.exists(context_dir):
            os.mkdir(context_dir)

    def create_id(self) -> str:
        """
        Create unique ctx ID, in JSON file this is a timestamp with microseconds

        Format: YYYYMMDDHHMMSS.MICROSECONDS.json

        :return: generated ID
        """
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S.%f")

    def create(self, meta: CtxMeta) -> str:
        """
        Create new ctx and return its ID

        :param meta: CtxMeta object
        :return: ctx ID
        """
        if meta.id is None or meta.id == "":
            meta.id = self.create_id()
        return meta.id

    def get_meta(self, search_string: str = None, order_by: str = None, order_direction: str = None,
                 limit: int = None, offset: int = None) -> dict:
        """
        Load ctx metadata from file

        :param search_string: search string
        :param order_by: order by field
        :param order_direction: order direction
        :param limit: limit
        :param offset: offset
        :return: ctx metadata
        """
        contexts = {}
        path = os.path.join(self.window.core.config.path, 'context.json')
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return contexts
                    contexts = self.parse_meta(data['items'])
        except Exception as e:
            self.window.core.debug.log(e)
            contexts = {}

        return contexts

    def load(self, id: str) -> list:
        """
        Load ctx data from json file

        :param id: context id
        :return: context items (list of CtxItem)
        """
        data = []
        path = os.path.join(self.window.core.config.path, 'context', id + '.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding="utf-8") as file:
                    data = self.parse_data(json.load(file))
                    if data == "" or data is None:
                        return []
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error while loading context: {}".format(id))
                data = []
        return data

    def append(self, meta: CtxMeta, item: CtxItem) -> bool:
        """
        Append item to ctx

        :param meta: ctx meta (CtxMeta)
        :param item: ctx item (CtxItem)
        """
        return False  # handled after in save() method

    def save(self, id: str, meta: CtxMeta, items: list):
        """
        Dump ctx to json file

        :param id: ctx id
        :param meta: ctx meta (CtxMeta)
        :param items: ctx items (list of CtxItem)
        """
        try:
            # update current ctx items
            items_path = os.path.join(self.window.core.config.path, 'context', id + '.json')
            serialized_items = []
            for item in items:
                serialized_items.append(self.serialize_item(item))
            dump = json.dumps(serialized_items, indent=4)

            # save items
            with open(items_path, 'w', encoding="utf-8") as f:
                f.write(dump)

            # update ctx meta (index)
            index_path = os.path.join(self.window.core.config.path, 'context.json')
            metas = self.get_meta()
            metas[id] = meta
            data = {}
            serialized_meta = {}
            for n in metas:
                serialized_meta[n] = self.serialize_meta(metas[n])

            data['items'] = serialized_meta
            data['__meta__'] = self.window.core.config.append_meta()
            dump = json.dumps(data, indent=4)

            # save index
            with open(index_path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while dumping context: {}".format(id))

    def remove(self, id: str):
        """
        Delete ctx by id

        :param id: ctx id
        """
        # delete ctx meta (index)
        index_path = os.path.join(self.window.core.config.path, 'context.json')
        metas = self.get_meta()
        if id in metas:
            del metas[id]
        data = {}
        serialized_meta = {}
        for n in metas:
            serialized_meta[n] = self.serialize_meta(metas[n])
        data['items'] = serialized_meta
        data['__meta__'] = self.window.core.config.append_meta()
        dump = json.dumps(data, indent=4)

        # save index
        with open(index_path, 'w', encoding="utf-8") as f:
            f.write(dump)

        # delete items
        path = os.path.join(self.window.core.config.path, 'context', id + '.json')
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                self.window.core.debug.log(e)

    def truncate(self):
        """Delete all ctx"""
        # delete all ctx files
        contexts = self.get_meta()
        for id in contexts:
            path = os.path.join(self.window.core.config.path, 'context', id + '.json')
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    self.window.core.debug.log(e)

        # truncate ctx index
        index_path = os.path.join(self.window.core.config.path, 'context.json')
        data = {}
        data['items'] = {}
        data['__meta__'] = self.window.core.config.append_meta()
        try:
            dump = json.dumps(data, indent=4)
            with open(index_path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.core.debug.log(e)

    def patch(self, version: Version) -> bool:
        """
        Migrate ctx to current app version

        :param version: current app version
        :return: True if migrated
        """
        return False

    @staticmethod
    def serialize_meta(meta: CtxMeta) -> dict:
        """
        Serialize CtxMeta to dict

        :param meta: CtxMeta
        :return: serialized CtxMeta dict
        """
        return {
            'id': meta.id,
            'name': meta.name,
            'date': meta.date,
            'mode': meta.mode,
            'last_mode': meta.last_mode,
            'thread': meta.thread,
            'assistant': meta.assistant,
            'preset': meta.preset,
            'run': meta.run,
            'status': meta.status,
            'initialized': meta.initialized,
        }

    @staticmethod
    def deserialize_meta(data: dict, meta: CtxMeta):
        """
        Deserialize CtxMeta from dict

        :param data: dict
        :param meta: CtxMeta
        """
        if 'id' in data:
            meta.id = data['id']
        if 'name' in data:
            meta.name = data['name']
        if 'date' in data:
            meta.date = data['date']
        if 'mode' in data:
            meta.mode = data['mode']
        if 'last_mode' in data:
            meta.last_mode = data['last_mode']
        if 'thread' in data:
            meta.thread = data['thread']
        if 'assistant' in data:
            meta.assistant = data['assistant']
        if 'preset' in data:
            meta.preset = data['preset']
        if 'run' in data:
            meta.run = data['run']
        if 'status' in data:
            meta.status = data['status']
        if 'initialized' in data:
            meta.initialized = data['initialized']
        return meta

    @staticmethod
    def serialize_item(ctx: CtxItem) -> dict:
        """
        Serialize CtxItem to dict

        :param ctx: CtxItem
        :return: serialized item dict
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

    @staticmethod
    def deserialize_item(data: dict, ctx: CtxItem):
        """
        Deserialize CtxItem from dict

        :param data: data dict
        :param ctx: CtxItem
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

    def dump(self, ctx: CtxItem) -> str:
        """
        Dump ctx to string

        :param ctx: CtxItem
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize_item(ctx))

    def parse_data(self, data: list) -> list:
        """
        Parse ctx data from json to objects

        :param data: ctx items data
        :return: ctx items (deserialized) as objects list
        """
        items = []
        for item in data:
            ctx = CtxItem()
            self.deserialize_item(item, ctx)
            items.append(ctx)
        return items

    def parse_meta(self, data: dict) -> dict:
        """
        Parse ctx data from json to objects

        :param data: ctx items data
        :return: ctx items (deserialized) dict
        """
        items = {}
        for k in data:
            meta = CtxMeta()
            self.deserialize_meta(data[k], meta)
            items[meta.id] = meta
        return items
