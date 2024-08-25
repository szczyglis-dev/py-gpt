#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

import datetime
import os.path
import time

from pathlib import Path
from sqlalchemy import text

from llama_index.core.indices.base import BaseIndex
from llama_index.core.schema import Document
from llama_index.core import SimpleDirectoryReader

from pygpt_net.provider.loaders.base import BaseLoader
from pygpt_net.utils import parse_args, pack_arg


class Indexing:
    def __init__(self, window=None):
        """
        Indexing core

        :param window: Window instance
        """
        self.window = window
        self.loaders = {
            "file": {},  # file loaders
            "web": {},   # web loaders
        }
        self.data_providers = {}  # data providers (loaders)
        self.external_instructions = {}
        self.external_config = {}
        self.last_call = None

    def register_loader(self, loader: BaseLoader):
        """
        Register data loader

        :param loader: data loader instance
        """
        # check if compiled version is allowed
        is_compiled = self.window.core.config.is_compiled() or self.window.core.platforms.is_snap()
        if not loader.allow_compiled and is_compiled:
            self.window.core.idx.log("Loader not allowed in compiled version: " + loader.id)
            return

        loader.attach_window(self.window)
        self.data_providers[loader.id] = loader  # cache loader
        extensions = loader.extensions  # available extensions
        types = loader.type  # available types

        if "file" in types:
            loader.set_args(self.get_loader_arguments(loader.id, "file"))  # set reader arguments
            try:
                reader = loader.get()  # get data reader instance
                for ext in extensions:
                    self.loaders["file"][ext] = reader  # set reader instance, by file extension
            except ImportError as e:
                msg = "Error while registering data loader: " + loader.id + " - " + str(e)
                self.window.core.debug.log(msg)
                self.window.core.debug.log(e)

        if "web" in types:
            loader.set_args(self.get_loader_arguments(loader.id, "web"))  # set reader arguments
            try:
                reader = loader.get()  # get data reader instance
                self.loaders["web"][loader.id] = reader # set reader instance, by id
                if loader.instructions:
                    for item in loader.instructions:
                        cmd = list(item.keys())[0]
                        self.external_instructions[cmd] = item[cmd]
                if loader.init_args:
                    for key in loader.init_args:
                        if loader.id not in self.external_config:
                            self.external_config[loader.id] = {}
                        self.external_config[loader.id][key] = {
                            "key": key,
                            "value": loader.init_args[key],
                            "type": "str",  # default = str
                        }
                        # from config
                        if key in loader.args:
                            self.external_config[loader.id][key]["value"] = loader.args[key]
                        if key in loader.init_args_types:
                            self.external_config[loader.id][key]["type"] = loader.init_args_types[key]

            except ImportError as e:
                msg = "Error while registering data loader: " + loader.id + " - " + str(e)
                self.window.core.debug.log(msg)
                self.window.core.debug.log(e)

    def update_loader_args(self, loader: str, args: dict):
        """
        Update loader arguments

        :param loader: loader id
        :param args: keyword arguments
        """
        if loader in self.data_providers:
            self.data_providers[loader].set_args(args)
            reader = self.data_providers[loader].get()  # get data reader instance
            self.loaders["web"][loader] = reader  # update reader instance

            # update in config
            config = self.window.core.config.get("llama.hub.loaders.args")
            if config is None:
                config = []
            loader_key = "web_" + loader
            for arg in args:
                found = False
                for item in config:
                    if item["loader"] == loader_key and item["name"] == arg:
                        item["value"] = args[arg]
                        found = True
                if not found:
                    type = "str"
                    if arg in self.data_providers[loader].init_args_types:
                        type = self.data_providers[loader].init_args_types[arg]
                    # pack value
                    value = pack_arg(args[arg], type)
                    config.append({
                        "loader": loader_key,
                        "name": arg,
                        "value": value,
                        "type": type
                    })

    def reload_loaders(self):
        """Reload loaders (update arguments)"""
        self.window.core.idx.log("Reloading data loaders...")
        for loader in self.data_providers.values():
            self.register_loader(loader)
        self.window.core.idx.log("Data loaders reloaded.")

    def get_external_instructions(self) -> dict:
        """
        Get external instructions

        :return: dict of external instructions
        """
        return self.external_instructions

    def get_external_config(self) -> dict:
        """
        Get external config

        :return: dict of external config
        """
        return self.external_config

    def get_online_loader(self, ext: str):
        """
        Get online loader by extension (deprecated)

        :param ext: file extension
        """
        loaders = self.window.core.config.get("llama.hub.loaders")
        if loaders is None or not isinstance(loaders, list):
            return None
        ext = ext.lower()
        for loader in loaders:
            check = loader["ext"].lower()
            if "," in check:
                extensions = check.replace(" ", "").split(",")
            else:
                extensions = [check.strip()]
            if ext in extensions:
                return loader["loader"]

    def get_data_providers(self) -> dict:
        """
        Get data providers

        :return: dict of data providers (loaders)
        """
        return self.data_providers

    def get_loader_arguments(self, id: str, type: str = "file") -> dict:
        """
        Get keyword arguments for loader

        :param id: loader id
        :param type: loader type (file, web)
        :return: dict of keyword arguments
        """
        name = type + "_" + id
        args = {}
        data = self.window.core.config.get("llama.hub.loaders.args")
        if isinstance(data, list):
            data_args = []
            # collect keyword arguments for loader
            for item in data:
                if item["loader"] == name:
                    data_args.append(item)
            args = parse_args(data_args)  # parse arguments
        return args

    def is_excluded(self, ext: str) -> bool:
        """
        Check if extension is excluded

        :param ext: file extension
        :return: True if excluded
        """
        if ext in self.loaders["file"]:
            if not self.window.core.config.get("llama.idx.excluded.force"):
                return False

        excluded = self.window.core.config.get("llama.idx.excluded.ext")
        if excluded is not None and excluded != "":
            excluded = excluded.replace(" ", "").split(",")
            if ext.lower() in excluded:
                return True
        return False

    def is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded

        :param path: file path
        :return: True if excluded
        """
        data_dir = self.window.core.config.get_user_dir("data")
        # interpreter files
        excluded = [
            os.path.join(data_dir, ".interpreter.output.py"),
            os.path.join(data_dir, ".interpreter.input.py"),
            os.path.join(data_dir, ".interpreter.current.py"),
        ]
        if path in excluded:
            return True
        return False

    def is_allowed(self, path: str) -> bool:
        """
        Check if path is allowed for indexing

        :param path: file path
        :return: True if allowed
        """
        if os.path.isdir(path):
            return True
        ext = os.path.splitext(path)[1][1:]  # get extension
        ext = ext.lower()
        if self.is_excluded_path(path):
            return False
        if ext in self.loaders["file"] and not self.window.core.config.get("llama.idx.excluded.force"):
            return True
        if self.is_excluded(ext):
            return False
        return True

    def get_documents(self, path: str, force: bool = False) -> list[Document]:
        """
        Get documents from path

        :param path: path to data
        :param force: force reading
        :return: list of documents
        """
        self.window.core.idx.log("Reading documents from path: {}".format(path))
        if os.path.isdir(path):
            reader = SimpleDirectoryReader(
                input_dir=path,
                recursive=True,
                exclude_hidden=False,
            )
            documents = reader.load_data()
        else:
            # get extension
            ext = os.path.splitext(path)[1][1:].lower()

            # check if not excluded extension
            if self.is_excluded(ext) and not force:
                self.window.core.idx.log("Ignoring excluded extension: {}".format(ext))
                return []

            # check if not excluded path
            if self.is_excluded_path(path) and not force:
                self.window.core.idx.log("Ignoring excluded path: {}".format(path))
                return []

            if ext in self.loaders["file"]:
                self.window.core.idx.log("Using loader for: {}".format(ext))
                reader = self.loaders["file"][ext]
                documents = reader.load_data(file=Path(path))
            else:
                self.window.core.idx.log("Using default SimpleDirectoryReader for: {}".format(ext))
                reader = SimpleDirectoryReader(input_files=[path])
                documents = reader.load_data()

        # append custom metadata
        self.window.core.idx.metadata.append_file_metadata(documents, path)
        return documents

    def read_text_content(self, path: str) -> str:
        """
        Get content from file using loaders

        :param path: path to file
        :return: file content
        """
        docs = self.get_documents(path, force=True)
        data = []
        for doc in docs:
            data.append(doc.text)
        return "\n".join(data)

    def prepare_document(self, doc: Document):
        """
        Prepare document to store

        :param doc: Document
        """
        # fix empty date in Pinecode
        if "last_accessed_date" in doc.extra_info and doc.extra_info["last_accessed_date"] is None:
            if "creation_date" in doc.extra_info:
                doc.extra_info["last_accessed_date"] = doc.extra_info["creation_date"]

    def index_files(
            self,
            idx: str,
            index: BaseIndex,
            path: str = None,
            is_tmp: bool = False,
            replace: bool = None,
            recursive: bool = None
    ) -> tuple:
        """
        Index all files in directory

        :param idx: index name
        :param index: index instance
        :param path: path to file or directory
        :param is_tmp: True if temporary index
        :param replace: True if replace old document
        :param recursive: True if recursive indexing
        :return: dict with indexed files, errors
        """
        if recursive is not None:
            if recursive:
                return self.index_files_recursive(idx, index, path, is_tmp, replace)
        else:
            if self.window.core.config.get("llama.idx.recursive"):
                return self.index_files_recursive(idx, index, path, is_tmp, replace)

        indexed = {}
        errors = []
        files = []
        if os.path.isdir(path):
            files = [os.path.join(path, f)
                     for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        elif os.path.isfile(path):
            files = [path]

        for file in files:   # per file to allow use of multiple loaders
            try:
                # remove old file from index if exists
                file_id = self.window.core.idx.files.get_id(file)

                if self.is_stopped():  # force stop
                    break

                # force replace or not old document
                if replace is not None:
                    if replace:
                        self.remove_old_file(idx, file_id, force=True)
                else:
                    # if auto, only replace if not temporary
                    if not is_tmp:
                        self.remove_old_file(idx, file_id)

                # index new version of file
                documents = self.get_documents(file)
                for d in documents:
                    if self.is_stopped():  # force stop
                        break

                    self.prepare_document(d)
                    self.index_document(index, d)
                    indexed[file] = d.id_  # add to index
                    self.window.core.idx.log("Inserted document: {}, metadata: {}".format(d.id_, d.metadata))
            except Exception as e:
                errors.append(str(e))
                print("Error while indexing file: " + file)
                self.window.core.debug.log(e)
                if self.stop_enabled():
                    break  # break loop if error

        return indexed, errors

    def index_files_recursive(
            self,
            idx: str,
            index: BaseIndex,
            path: str = None,
            is_tmp: bool = False,
            replace: bool = None
    ) -> tuple:
        """
        Index all files in directory and subdirectories recursively.

        :param idx: index name
        :param index: index instance
        :param path: path to file or directory
        :param is_tmp: True if temporary index
        :param replace: True if replace old document
        :return: dict with indexed files, errors
        """
        indexed = {}
        errors = []
        is_break = False

        # directory
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # remove old file from index if exists
                        file_id = self.window.core.idx.files.get_id(file_path)

                        if self.is_stopped():  # force stop
                            break

                        # force replace or not old document
                        if replace is not None:
                            if replace:
                                self.remove_old_file(idx, file_id, force=True)
                        else:
                            # if auto, only replace if not temporary
                            if not is_tmp:
                                self.remove_old_file(idx, file_id)

                        # index new version of file
                        documents = self.get_documents(file_path)
                        for d in documents:
                            if self.is_stopped():  # force stop
                                break

                            self.prepare_document(d)
                            self.index_document(index, d)
                            indexed[file_path] = d.id_  # add to index
                            self.window.core.idx.log("Inserted document: {}, metadata: {}".format(d.id_, d.metadata))
                    except Exception as e:
                        errors.append(str(e))
                        print("Error while indexing file: " + file_path)
                        self.window.core.debug.log(e)
                        if self.stop_enabled():
                            is_break = True
                            break  # break loop if error

                if is_break or self.is_stopped():
                    break  # stop os.walk if error or forced stop

        # file
        elif os.path.isfile(path):
            try:
                # remove old file from index if exists
                file_id = self.window.core.idx.files.get_id(path)

                # force replace or not old document
                if replace is not None:
                    if replace:
                        self.remove_old_file(idx, file_id, force=True)
                else:
                    # if auto, only replace if not temporary
                    if not is_tmp:
                        self.remove_old_file(idx, file_id)

                # index new version of file
                documents = self.get_documents(path)
                for d in documents:
                    if self.is_stopped():  # force stop
                        break

                    self.prepare_document(d)
                    self.index_document(index, d)
                    indexed[path] = d.id_  # add to index
                    self.window.core.idx.log("Inserted document: {}, metadata: {}".format(d.id_, d.metadata))
            except Exception as e:
                errors.append(str(e))
                print("Error while indexing file: " + path)
                self.window.core.debug.log(e)

        return indexed, errors

    def get_db_data_from_ts(self, updated_ts: int = 0) -> list:
        """
        Get data from database from timestamp

        :param updated_ts: timestamp
        :return: list of documents
        """
        db = self.window.core.db.get_db()
        documents = []
        query = f"""
        SELECT
            'Human: ' || ctx_item.input || '\nAssistant: ' || ctx_item.output AS text,
            ctx_item.input_ts AS input_ts,
            ctx_item.meta_id AS meta_id,
            ctx_item.id AS item_id
        FROM 
            ctx_item
        LEFT JOIN
            ctx_meta
        ON
            ctx_item.meta_id = ctx_meta.id
        WHERE
            ctx_meta.updated_ts > {updated_ts}
        """
        with db.connect() as connection:
            result = connection.execute(text(query))
            for item in result.fetchall():
                data = item._asdict()
                doc = Document(
                    text=data["text"],
                    metadata={
                        "ctx_date": str(datetime.datetime.fromtimestamp(int(data["input_ts"]))),
                        "ctx_id": data["meta_id"],
                        "item_id": data["item_id"],
                        "indexed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                documents.append(doc)
        return documents

    def get_db_meta_ids_from_ts(self, updated_ts: int = 0) -> list:
        """
        Get IDs of meta from database from timestamp

        :param updated_ts: timestamp
        :return: list of IDs
        """
        db = self.window.core.db.get_db()
        ids = []
        query = f"""
        SELECT
            id
        FROM 
            ctx_meta
        WHERE
            ctx_meta.updated_ts > {updated_ts}
        """
        with db.connect() as connection:
            result = connection.execute(text(query))
            for row in result.fetchall():
                data = row._asdict()
                ids.append(data["id"])
        return ids

    def get_db_data_by_id(self, id: int = 0, updated_ts: int = 0) -> list:
        """
        Get data from database by meta id

        :param id: ctx meta id
        :param updated_ts: timestamp from which to get data
        :return: list of documents
        """
        db = self.window.core.db.get_db()
        documents = []
        query = f"""
        SELECT
            'Human: ' || input || '\nAssistant: ' || output AS text,
            input_ts AS input_ts,
            meta_id AS meta_id,
            id AS item_id
        FROM ctx_item
        WHERE meta_id = {id}
        """
        # restrict to updated data if from timestamp is given
        if updated_ts > 0:
            query += f" AND (input_ts > {updated_ts} OR output_ts > {updated_ts})"
        with db.connect() as connection:
            result = connection.execute(text(query))
            for item in result.fetchall():
                data = item._asdict()
                doc = Document(
                    text=data["text"],
                    metadata={
                        "ctx_date": str(datetime.datetime.fromtimestamp(int(data["input_ts"]))),
                        "ctx_id": data["meta_id"],
                        "item_id": data["item_id"],
                        "indexed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                documents.append(doc)
        return documents

    def index_db_by_meta_id(self, idx: str, index: BaseIndex, id: int = 0, from_ts: int = 0) -> (int, list):
        """
        Index data from database by meta id

        :param idx: index name
        :param index: index instance
        :param id: ctx meta id
        :param from_ts: timestamp from which to index
        :return: number of indexed documents, errors
        """
        errors = []
        n = 0
        try:
            # remove old document from index if indexing by ID only and not from timestamp
            if from_ts == 0:
                self.window.core.idx.log("Indexing documents from database by meta id: {}".format(id))
                self.remove_old_meta_id(idx, id)
            elif from_ts > 0:
                self.window.core.idx.log("Indexing documents from database by meta id: {} from timestamp: {}".format(id, from_ts))

            # get items from database
            documents = self.get_db_data_by_id(id, from_ts)
            for d in documents:
                if self.is_stopped():  # force stop
                    break

                self.index_document(index, d)
                doc_id = d.id_
                self.window.core.idx.log("Inserted ctx DB document: {} / {}, id: {}, metadata: {}".format(n+1, len(documents), d.id_, d.metadata))
                self.window.core.ctx.idx.set_meta_as_indexed(id, idx, doc_id)  # update ctx
                n += 1
        except Exception as e:
            errors.append(str(e))
            self.window.core.debug.log(e)
        return n, errors

    def index_db_from_updated_ts(self, idx: str, index: BaseIndex, from_ts: int = 0) -> (int, list):
        """
        Index data from database from timestamp

        :param idx: index name
        :param index: index instance
        :param from_ts: timestamp
        :return: number of indexed documents, errors
        """
        self.window.core.idx.log("Indexing documents from database from timestamp: {}".format(from_ts))
        errors = []
        n = 0
        ids = self.get_db_meta_ids_from_ts(from_ts)
        for id in ids:
            if self.is_stopped():  # force stop
                break

            indexed, errs = self.index_db_by_meta_id(idx, index, id, from_ts)
            n += indexed
            errors.extend(errs)
        return n, errors

    def index_url(
            self,
            idx: str,
            index: BaseIndex,
            url: str,
            type="webpage",
            extra_args: dict = None,
            is_tmp: bool = False,
            replace: bool = None
    ) -> (int, list):
        """
        Index data from external (remote) resource

        :param idx: index name
        :param index: index instance
        :param url: external url to index
        :param type: type of URL (webpage, feed, etc.)
        :param extra_args: extra arguments for loader
        :param is_tmp: True if temporary index
        :param replace: True if force replace old document
        :return: number of indexed documents, errors
        """
        errors = []
        n = 0

        # check if web loader for defined type exists
        if type not in self.loaders["web"]:
            raise ValueError("No web loader for type: {}".format(type))

        try:
            # remove old content from index if already indexed
            loader = self.loaders["web"][type]

            # additional keyword arguments for data loader
            if extra_args is None:
                extra_args = {}

            # override URL if provided in load_data args
            if "url" not in extra_args:
                extra_args["url"] = url

            # get unique external content identifier
            unique_id = self.data_providers[type].get_external_id(extra_args)

            # remove old document from index
            if replace is not None:
                if replace:
                    self.remove_old_external(idx, unique_id, type, force=True)
            else:
                # if auto, only replace if not temporary
                if not is_tmp:
                    self.remove_old_external(idx, unique_id, type)

            self.window.core.idx.log("Loading web documents from: {}".format(unique_id))
            self.window.core.idx.log("Using web loader for type: {}".format(type))

            args = self.data_providers[type].prepare_args(**extra_args)

            # get documents from external resource
            documents = loader.load_data(
                **args
            )

            # append custom metadata
            self.window.core.idx.metadata.append_web_metadata(documents, type, args)

            for d in documents:
                if self.is_stopped():  # force stop
                    break

                self.index_document(index, d)
                doc_id = d.id_  # URL is used as document ID
                if not is_tmp:
                    self.window.core.idx.external.set_indexed(
                        content=unique_id,
                        type=type,
                        idx=idx,
                        doc_id=doc_id,
                    )  # update external index
                self.window.core.idx.log("Inserted web document: {} / {}, id: {}, metadata: {}".format(n+1, len(documents), d.id_, d.metadata))
                n += 1
        except Exception as e:
            errors.append(str(e))
            self.window.core.debug.log(e)
        return n, errors

    def index_urls(
            self,
            idx: str,
            index: BaseIndex,
            urls: list,
            type="webpage",
            extra_args: dict = None,
            is_tmp: bool = False
    ) -> (int, list):
        """
        Index data from URLs

        :param idx: index name
        :param index: index instance
        :param urls: list of urls
        :param type: type of URL (webpage, feed, etc.)
        :param extra_args: extra arguments for loader
        :param is_tmp: True if temporary index
        :return: number of indexed documents, errors
        """
        errors = []
        n = 0

        # check if web loader for defined type exists
        if type not in self.loaders["web"]:
            msg = "No web loader for type: {}".format(type)
            errors.append(msg)
            self.window.core.debug.log(msg)
            return n, errors

        for url in urls:
            if self.is_stopped():  # force stop
                break

            indexed, errs = self.index_url(
                idx=idx,
                index=index,
                url=url,
                type=type,
                extra_args=extra_args,
                is_tmp=is_tmp,
            )
            n += indexed
            errors.extend(errs)
        return n, errors

    def remove_old_meta_id(self, idx: str, id: int = 0, force: bool = False) -> bool:
        """
        Remove old meta id from index

        :param idx: index name
        :param id: ctx meta id
        :param force: force remove
        :return: True if removed, False if not
        """
        # abort if not configured to replace old documents
        if not self.window.core.config.get("llama.idx.replace_old") and not force:
            return False

        store = self.window.core.idx.get_current_store()
        if self.window.core.idx.ctx.exists(store, idx, id):
            doc_id = self.window.core.idx.ctx.get_doc_id(store, idx, id)
            if doc_id:
                self.window.core.idx.log("Removing old document id: {}".format(doc_id))
                try:
                    self.window.core.idx.storage.remove_document(
                        id=idx,
                        doc_id=doc_id,
                    )
                except Exception as e:
                    self.window.core.debug.log(e)
                return True
        return False

    def remove_old_file(self, idx: str, file_id: str, force: bool = False):
        """
        Remove old file from index

        :param idx: index name
        :param file_id: file id
        :param force: force remove
        :return: True if removed, False if not
        """
        # abort if not configured to replace old documents
        if not self.window.core.config.get("llama.idx.replace_old") and not force:
            return False

        store = self.window.core.idx.get_current_store()
        if self.window.core.idx.files.exists(store, idx, file_id):
            doc_id = self.window.core.idx.files.get_doc_id(store, idx, file_id)
            if doc_id:
                self.window.core.idx.log("Removing old document id: {}".format(doc_id))
                try:
                    self.window.core.idx.storage.remove_document(
                        id=idx,
                        doc_id=doc_id,
                    )
                except Exception as e:
                    self.window.core.debug.log(e)
                return True
        return False

    def remove_old_external(self, idx: str, content: str, type: str, force: bool = False):
        """
        Remove old file from index

        :param idx: index name
        :param content: content
        :param type: type
        :param force: force remove
        :return: True if removed, False if not
        """
        # abort if not configured to replace old documents
        if not self.window.core.config.get("llama.idx.replace_old") and not force:
            return False

        store = self.window.core.idx.get_current_store()
        if self.window.core.idx.external.exists(store, idx, content, type):
            doc_id = self.window.core.idx.external.get_doc_id(store, idx, content, type)
            if doc_id:
                self.window.core.idx.log("Removing old document id: {}".format(doc_id))
                try:
                    self.window.core.idx.storage.remove_document(
                        id=idx,
                        doc_id=doc_id,
                    )
                except Exception as e:
                    self.window.core.debug.log(e)
                return True
        return False

    def index_document(self, index: BaseIndex, doc: Document):
        """
        Index document

        :param index: index instance
        :param doc: document
        """
        self.apply_rate_limit()  # apply RPM limit
        try:
            # display embedding model info
            self.window.core.idx.log("Embedding model: {}".format(index.service_context.embed_model.model_name))
        except Exception as e:
            self.window.core.debug.log(e)
        index.insert(document=doc)

    def apply_rate_limit(self):
        """Apply API calls RPM limit"""
        max_per_minute = 60
        if self.window.core.config.has("llama.idx.embeddings.limit.rpm"):
            max_per_minute = int(self.window.core.config.get("llama.idx.embeddings.limit.rpm")) # per minute
        if max_per_minute <= 0:
            return
        interval = datetime.timedelta(minutes=1) / max_per_minute
        now = datetime.datetime.now()
        if self.last_call is not None:
            time_since_last_call = now - self.last_call
            if time_since_last_call < interval:
                sleep_time = (interval - time_since_last_call).total_seconds()
                self.window.core.idx.log("RPM limit: sleep for {} seconds".format(sleep_time))
                time.sleep(sleep_time)
        self.last_call = now

    def stop_enabled(self) -> bool:
        """
        Check if stop on error is enabled

        :return: True if enabled
        """
        return self.window.core.config.get('llama.idx.stop.error')

    def is_stopped(self) -> bool:
        """
        Check if indexing is stopped

        :return: True if stopped
        """
        return self.window.controller.idx.is_stopped()
