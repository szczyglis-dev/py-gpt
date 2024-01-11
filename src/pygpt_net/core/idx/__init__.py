#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.11 09:00:00                  #
# ================================================== #

import datetime
import os.path
from llama_index import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    ServiceContext,
    StorageContext,
    load_index_from_storage,
    download_loader
)
from llama_index.llms import OpenAI
from packaging.version import Version
from pathlib import Path

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.index.json_file import JsonFileProvider


class Idx:
    def __init__(self, window=None):
        """
        Indexers core

        :param window: Window instance
        """
        self.window = window
        self.indexes = {}
        self.loaders = {
            "pdf": "PDFReader",
            "docx": "DocxReader",
            "md": "MarkdownReader",
            "json": "JsonReader",
            "csv": "SimpleCSVReader",
            "epub": "EpubReader",
            "xlsx": "PandasExcelReader",
        }  # TODO: add adding custom loaders via dict config in settings
        self.current = "base"
        self.provider = JsonFileProvider(window)
        self.items = {}
        self.initialized = False

    def get_service_context(self, model: str = "gpt-3.5-turbo"):
        """
        Get service context

        :param model: Model name
        :return: Service context
        """
        # GPT
        if model.startswith("gpt-") or model.startswith("text-davinci-"):
            os.environ['OPENAI_API_KEY'] = self.window.core.config.get("api_key")
            llm = OpenAI(temperature=0.0, model=model)
            return ServiceContext.from_defaults(llm=llm)
        # TODO: add other models

    def get_documents(self, data_path):
        """
        Get documents from path

        :param data_path: Path to data
        :return: List of documents
        """
        if os.path.isdir(data_path):
            reader = SimpleDirectoryReader(
                input_dir=data_path,
                recursive=True,
                exclude_hidden=False
            )
            documents = reader.load_data()
        else:
            # get data loader by file extension
            ext = os.path.splitext(data_path)[1][1:]
            if ext in self.loaders:
                loader = download_loader(self.loaders[ext])  # download loader from hub
                reader = loader()
                documents = reader.load_data(file=Path(data_path))
            else:
                reader = SimpleDirectoryReader(input_files=[data_path])
                documents = reader.load_data()
        return documents

    def prepare(self, idx: str = "base", model: str = "gpt-3.5-turbo"):
        """
        Prepare index

        :param idx: Index name
        :param model: Model name
        """
        service_context = self.get_service_context(model=model)
        idx_path = os.path.join(self.window.core.config.path, "idx", idx)
        if not os.path.exists(idx_path):
            self.indexes[idx] = VectorStoreIndex([])  # create empty index
            self.store_index(idx=idx)
        else:
            storage_context = StorageContext.from_defaults(persist_dir=idx_path)
            self.indexes[idx] = load_index_from_storage(storage_context, service_context=service_context)

    def store_index(self, idx: str = "base"):
        """
        Store index

        :param idx: Index name
        """
        idx_path = os.path.join(self.window.core.config.path, "idx", idx)
        self.indexes[idx].storage_context.persist(persist_dir=idx_path)

    def remove_index(self, idx: str = "base") -> bool:
        """
        Truncate index

        :param idx: Index name
        :return: True if success
        """
        self.indexes[idx] = None
        idx_path = os.path.join(self.window.core.config.path, "idx", idx)
        if os.path.exists(idx_path):
            for f in os.listdir(idx_path):
                os.remove(os.path.join(idx_path, f))
            os.rmdir(idx_path)
        return True

    def index(self, idx: str = "base", data_path: str = None, model: str = "gpt-3.5-turbo") -> tuple:
        """
        Index all files in directory

        :param idx: Index name
        :param data_path: Path to data directory
        :param model: Model name
        :return: number of indexed files, errors
        """
        self.prepare(idx, model=model)

        indexed_files = {}
        errors = []
        files = []
        if os.path.isdir(data_path):
            files = [os.path.join(data_path, f) for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f))]
        elif os.path.isfile(data_path):
            files = [data_path]
        n = 0
        for file in files:   # per file to allow use of multiple loaders
            try:
                documents = self.get_documents(file)
                for d in documents:
                    self.indexes[idx].insert(document=d)
                    n += 1
                    indexed_files[file] = d.id_
            except Exception as e:
                errors.append(str(e))
                print(e)
                print("Error while indexing file: " + file)
                self.window.core.debug.log(e)
                continue

        if n > 0:
            self.store_index(idx=idx)  # save index

        return indexed_files, errors

    def query(self, query, idx: str = "base", model: str = "gpt-3.5-turbo") -> str:
        """
        Query index

        :param query: Query string
        :param idx: Index name
        :param model: Model name
        :return: Response
        """
        self.prepare(idx=idx, model=model)
        if idx not in self.indexes or self.indexes[idx] is None:
            raise Exception("Index not prepared")
        response = self.indexes[idx].as_query_engine().query(query)
        return str(response)  # TODO: handle stream response

    def get_idx_data(self, idx: str = "base") -> dict:
        """
        Get indexed files data
        :param idx: Index name
        :return: Indexed files data
        """
        if idx in self.items:
            return self.items[idx].items
        return {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version):
        """Patch provider data"""
        self.provider.patch(app_version)

    def init(self):
        """Initialize indexes"""
        if not self.initialized:
            self.load()
            self.initialized = True

    def get(self, index: str) -> IndexItem:
        """
        Return index data

        :param index: index id
        :return: index object
        """
        if index in self.items:
            return self.items[index]

    def get_all(self) -> dict:
        """
        Return all indexes

        :return: all indexes
        """
        return self.items

    def has(self, index: str) -> bool:
        """
        Check if index exists

        :param index: index id
        :return: True if index exists
        """
        return index in self.items

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

    def append(self, idx: str, files: dict):
        """
        Append indexed files to index

        :param idx: index id
        :param files: dict of indexed files
        """
        if idx in self.items:
            for path in files:
                file = files[path]
                self.items[idx].items[path] = {
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
