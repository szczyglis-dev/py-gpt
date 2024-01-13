#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 21:00:00                  #
# ================================================== #

import datetime
import os.path
from packaging.version import Version

from llama_index.llms import ChatMessage, MessageRole
from llama_index.prompts import ChatPromptTemplate

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.index.json_file import JsonFileProvider

from .indexing import Indexing
from .storage import Storage


class Idx:
    def __init__(self, window=None):
        """
        Indexers core

        :param window: Window instance
        """
        self.window = window
        self.indexing = Indexing(window)
        self.storage = Storage(window)
        self.provider = JsonFileProvider(window)
        self.items = {}
        self.initialized = False

    def store_index(self, idx: str = "base"):
        """
        Store index

        :param idx: Index name
        """
        self.storage.store(idx)

    def remove_index(self, idx: str = "base") -> bool:
        """
        Truncate index

        :param idx: Index name
        :return: True if success
        """
        return self.storage.remove(idx)

    def index_files(self, idx: str = "base", path: str = None) -> tuple:
        """
        Index file or directory of files

        :param idx: Index name
        :param path: Path to file or directory
        :return: dict with indexed files, errors
        """
        index = self.storage.get(idx)  # get or create index
        files, errors = self.indexing.index_files(index, path)  # index files
        if len(files) > 0:
            self.storage.store(id=idx, index=index)  # store index
        return files, errors

    def index_db_by_meta_id(self, idx: str = "base", id: int = 0) -> tuple:
        """
        Index records from db by meta id

        :param idx: Index name
        :param id: Meta id
        :return: dict with indexed files, errors
        """
        index = self.storage.get(idx)  # get or create index
        num, errors = self.indexing.index_db_by_meta_id(index, id)  # index db records
        if num > 0:
            self.storage.store(id=idx, index=index)  # store index
        return num, errors

    def index_db_from_updated_ts(self, idx: str = "base", from_ts: int = 0) -> tuple:
        """
        Index records from db by meta id

        :param idx: Index name
        :param from_ts: From timestamp
        :return: dict with indexed files, errors
        """
        index = self.storage.get(idx)  # get or create index
        num, errors = self.indexing.index_db_from_updated_ts(index, from_ts)  # index db records
        if num > 0:
            self.storage.store(id=idx, index=index)  # store index
        return num, errors

    def get_custom_prompt(self, prompt: str = None) -> ChatPromptTemplate or None:
        """
        Get custom prompt template if sys prompt is not empty

        :param prompt: System prompt
        :return: ChatPromptTemplate
        """
        if prompt is None or prompt.strip() == "":
            return None

        qa_msgs = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=prompt,
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=(
                    "Context information is below.\n"
                    "---------------------\n"
                    "{context_str}\n"
                    "---------------------\n"
                    "Given the context information and not prior knowledge, "
                    "answer the question: {query_str}\n"
                ),
            ),
        ]
        return ChatPromptTemplate(qa_msgs)

    def query(self, query, idx: str = "base", model: str = "gpt-3.5-turbo", sys_prompt: str = None) -> str:
        """
        Query index

        :param query: Query string
        :param idx: Index name
        :param model: Model name
        :param sys_prompt: System prompt
        :return: Response
        """
        # log query
        is_log = False
        if self.window.core.config.has("llama.log") and self.window.core.config.get("llama.log"):
            is_log = True

        if is_log:
            print("[LLAMA-INDEX] Query index...")
            print("[LLAMA-INDEX] Idx: {}, query: {}, model: {}".format(idx, query, model))

        # check if index exists
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")
        index = self.storage.get(idx, model=model)  # get index

        # query index
        tpl = self.get_custom_prompt(sys_prompt)
        if tpl is not None:
            if is_log:
                print("[LLAMA-INDEX] Query index with custom prompt: {}...".format(sys_prompt))
            response = index.as_query_engine(
                text_qa_template=tpl
            ).query(query)  # query with custom sys prompt
        else:
            response = index.as_query_engine().query(query)  # query with default prompt
        return str(response)  # TODO: handle stream response

    def sync_items(self):
        """
        Sync from config
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            for item in items:
                idx = item['id']
                if idx not in self.items:
                    self.items[idx] = IndexItem()
                    self.items[idx].id = idx
                    self.items[idx].name = idx
                else:
                    self.items[idx].id = idx
                    self.items[idx].name = idx
            self.save()

    def get_idx_data(self, idx: str = None) -> dict:
        """
        Get indexed files data
        :param idx: Index name
        :return: Indexed files data
        """
        indexes = {}
        if idx is not None:
            if idx in self.items:
                indexes[idx] = self.items[idx].items
        else:
            # all indexes
            for idx in self.items:
                indexes[idx] = self.items[idx].items

        return indexes

    def get_by_idx(self, idx: int) -> str:
        """
        Return idx by list index

        :param idx: idx
        :return: idx name
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            if idx < len(items):
                return items[idx]['id']

    def get_idx_by_name(self, name: str) -> int:
        """
        Return idx by name

        :param name: idx name
        :return: idx on list
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            for idx, item in enumerate(items):
                if item['id'] == name:
                    return idx

    def get_default_idx(self) -> str:
        """
        Return default idx

        :return: idx name
        """
        if len(self.items) > 0:
            return self.get_by_idx(0)

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version):
        """
        Patch provider data

        :param app_version: App version
        """
        self.provider.patch(app_version)

    def init(self):
        """Initialize indexes"""
        if not self.initialized:
            self.load()
            self.initialized = True

    def get(self, idx: str) -> IndexItem:
        """
        Return index data

        :param idx: index id
        :return: IndexItem object
        """
        if idx in self.items:
            return self.items[idx]

    def get_all(self) -> dict:
        """
        Return all indexes

        :return: all indexes
        """
        return self.items

    def get_idx_config(self, idx: str) -> dict:
        """
        Return index config

        :param idx: index id
        :return: index config
        """
        indexes = self.window.core.config.get('llama.idx.list')
        if indexes is not None:
            for item in indexes:
                if item['id'] == idx:
                    return item

    def has(self, idx: str) -> bool:
        """
        Check if index exists

        :param idx: index id
        :return: True if index exists
        """
        return idx in self.items

    def is_indexed(self, idx: str, file: str) -> bool:
        """
        Check if file is indexed

        :param idx: index id
        :param file: file path
        :return: True if file is indexed
        """
        if idx in self.items:
            return file in self.items[idx].items
        return False

    def to_file_id(self, path: str) -> str:
        """
        Prepare file id

        :param path: file path
        :return: file id
        """
        path = os.path.normpath(path)
        root_path = os.path.normpath(self.window.core.config.get_user_dir('data'))
        path = path.replace(root_path, '')
        path = path.replace("\\", "/").strip(r'\/')
        return path

    def append(self, idx: str, files: dict):
        """
        Append indexed files to index

        :param idx: index id
        :param files: dict of indexed files
        """
        if idx not in self.items:
            self.items[idx] = IndexItem()
            self.items[idx].id = idx
            self.items[idx].name = idx  # use index id as name

        for path in files:
            file = files[path]
            file_id = self.to_file_id(path)
            self.items[idx].items[file_id] = {
                "path": path,
                "indexed_ts": datetime.datetime.now().timestamp(),
                "id": file,
            }
        self.save()

    def clear(self, idx: str):
        """
        Clear index items

        :param idx: index id
        """
        if idx in self.items:
            self.items[idx].items = {}
            self.save()

    def load(self):
        """
        Load indexes
        """
        self.items = self.provider.load()

    def save(self):
        """Save indexes"""
        self.provider.save(self.items)

    def get_version(self) -> str:
        """
        Get config version

        :return: config version
        """
        return self.provider.get_version()
