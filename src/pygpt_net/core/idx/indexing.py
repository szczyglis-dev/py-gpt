#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 04:00:00                  #
# ================================================== #

import os.path
from pathlib import Path
from sqlalchemy import text
from llama_index.indices.base import BaseIndex
from llama_index import (
    SimpleDirectoryReader,
    download_loader,
)
from llama_index.readers.schema.base import Document
from llama_index.readers import BeautifulSoupWebReader

from pygpt_net.provider.loaders.base import BaseLoader


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
        }  # offline loaders
        self.loader_providers = {}
        self.external_instructions = {}

    def register_loader(self, loader: BaseLoader):
        """
        Register data loader

        :param loader: loader instance
        """
        self.loader_providers[loader.id] = loader
        extensions = loader.extensions  # available extensions
        types = loader.type  # available types
        if "file" in types:
            for ext in extensions:
                self.loaders["file"][ext] = loader.get()  # get reader instance, by extension
        if "web" in types:
            self.loaders["web"][loader.id] = loader.get()  # get reader instance, by id
            if loader.instructions:
                for item in loader.instructions:
                    cmd = list(item.keys())[0]
                    self.external_instructions[cmd] = item[cmd]

    def get_external_instructions(self):
        """
        Get external instructions

        :return: dict of external instructions
        """
        return self.external_instructions

    def get_online_loader(self, ext: str):
        """
        Get online loader by extension

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

    def get_excluded_extensions(self) -> list[str]:
        """
        Get excluded extensions if no loader is available

        :return: list of excluded extensions
        """
        # images
        excluded = ["jpg", "jpeg", "png", "psd", "gif", "bmp", "tiff",
                    "webp", "svg", "ico", "heic", "heif", "avif", "apng"]

        # audio
        excluded += ["mp3", "wav", "flac", "ogg", "m4a", "wma",
                     "aac", "aiff", "alac", "dsd", "pcm", "mpc"]

        # video
        excluded += ["mp4", "mkv", "avi", "mov", "wmv", "flv",
                     "webm", "vob", "ogv", "3gp", "3g2", "m4v", "m2v"]

        # archives
        excluded += ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "lz", "lz4",
                     "zst", "ar", "iso", "nrg", "dmg", "vhd", "vmdk", "vhdx", "vdi",
                     "img", "wim", "swm", "esd", "cab", "rpm", "deb", "pkg", "apk"]

        # binary
        excluded += ["exe", "dll", "so", "dylib", "app", "msi", "dmg", "pkg", "deb", "rpm", "apk", "jar",
                     "war", "ear", "class", "pyc", "whl", "egg", "so", "dylib", "a", "o", "lib", "bin",
                     "elf", "ko", "sys", "drv"]

        # sort and save
        excluded = sorted(excluded)

        return excluded

    def is_excluded(self, ext: str) -> bool:
        """
        Check if extension is excluded

        :param ext: file extension
        :return: True if excluded
        """
        excluded = self.window.core.config.get("llama.idx.excluded_ext")
        if excluded is not None and excluded != "":
            excluded = excluded.replace(" ", "").split(",")
            if ext.lower() in excluded:
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
        # check offline loaders
        if ext in self.loaders:
            return True
        # check online loaders
        if not self.window.core.config.is_compiled() and self.get_online_loader(ext) is not None:
            return True
        if self.is_excluded(ext):
            return False
        return True

    def get_documents(self, path: str) -> list[Document]:
        """
        Get documents from path

        :param path: path to data
        :return: list of documents
        """
        self.log("Reading documents from path: {}".format(path))
        if self.window.core.config.is_compiled():
            self.log("Compiled version detected - online loaders are disabled. "
                     "Use Python version for using online loaders.")

        if os.path.isdir(path):
            reader = SimpleDirectoryReader(
                input_dir=path,
                recursive=True,
                exclude_hidden=False,
            )
            documents = reader.load_data()
        else:
            ext = os.path.splitext(path)[1][1:]  # get extension
            online_loader = self.get_online_loader(ext)  # get online loader if available
            # TODO: in future, add support for online loaders in compiled version
            if online_loader is not None and not self.window.core.config.is_compiled():
                self.log("Using online loader for: {}".format(ext))
                loader = download_loader(online_loader)
                reader = loader()
                documents = reader.load_data(file=Path(path))
            else:  # try offline loaders
                if ext in self.loaders["file"]:
                    self.log("Using offline loader for: {}".format(ext))
                    # download_loader cause problems in compiled version
                    # use offline versions instead
                    reader = self.loaders["file"][ext]
                    documents = reader.load_data(file=Path(path))
                else:
                    if self.is_excluded(ext):
                        self.log("Ignoring excluded extension: {}".format(ext))
                        return []
                    self.log("Using default loader for: {}".format(ext))
                    reader = SimpleDirectoryReader(input_files=[path])
                    documents = reader.load_data()
        return documents

    def read_text_content(self, path: str) -> str:
        """
        Get content from file using loaders

        :param path: path to file
        :return: file content
        """
        docs = self.get_documents(path)
        data = []
        for doc in docs:
            data.append(doc.text)
        return "\n".join(data)

    def index_files(self, idx: str, index: BaseIndex, path: str = None) -> tuple:
        """
        Index all files in directory

        :param idx: index name
        :param index: index instance
        :param path: path to file or directory
        :return: dict with indexed files, errors
        """
        if self.window.core.config.get("llama.idx.recursive"):
            return self.index_files_recursive(idx, index, path)

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
                self.remove_old_file(idx, file_id)

                # index new version of file
                documents = self.get_documents(file)
                for d in documents:
                    index.insert(document=d)
                    indexed[file] = d.id_  # add to index
                    self.log("Inserted document: {}".format(d.id_))
            except Exception as e:
                errors.append(str(e))
                print(e)
                print("Error while indexing file: " + file)
                self.window.core.debug.log(e)
                continue

        return indexed, errors

    def index_files_recursive(self, idx: str, index: BaseIndex, path: str = None) -> tuple:
        """
        Index all files in directory and subdirectories recursively.

        :param idx: index name
        :param index: index instance
        :param path: path to file or directory
        :return: dict with indexed files, errors
        """
        indexed = {}
        errors = []

        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # remove old file from index if exists
                        file_id = self.window.core.idx.files.get_id(path)
                        self.remove_old_file(idx, file_id)

                        # index new version of file
                        documents = self.get_documents(file_path)
                        for d in documents:
                            index.insert(document=d)
                            indexed[file_path] = d.id_  # add to index
                            self.log("Inserted document: {}".format(d.id_))
                    except Exception as e:
                        errors.append(str(e))
                        print(e)
                        print("Error while indexing file: " + file_path)
                        self.window.core.debug.log(e)
                        continue
        elif os.path.isfile(path):
            try:
                # remove old file from index if exists
                file_id = self.window.core.idx.files.get_id(path)
                self.remove_old_file(idx, file_id)

                # index new version of file
                documents = self.get_documents(path)
                for d in documents:
                    index.insert(document=d)
                    indexed[path] = d.id_  # add to index
                    self.log("Inserted document: {}".format(d.id_))
            except Exception as e:
                errors.append(str(e))
                print(e)
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
            'User: ' || ctx_item.input || '; Assistant: ' || ctx_item.output AS text
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
                doc_str = ", ".join([str(entry) for entry in item])
                documents.append(Document(text=doc_str))
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
            'User: ' || input || '; Assistant: ' || output AS text
        FROM ctx_item
        WHERE meta_id = {id}
        """
        # restrict to updated data if from timestamp is given
        if updated_ts > 0:
            query += f" AND (input_ts > {updated_ts} OR output_ts > {updated_ts})"

        with db.connect() as connection:
            result = connection.execute(text(query))
            for item in result.fetchall():
                doc_str = ", ".join([str(entry) for entry in item])
                documents.append(Document(text=doc_str))
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
                self.log("Indexing documents from database by meta id: {}".format(id))
                self.remove_old_meta_id(idx, id)
            elif from_ts > 0:
                self.log("Indexing documents from database by meta id: {} from timestamp: {}".format(id, from_ts))

            # get items from database
            documents = self.get_db_data_by_id(id, from_ts)
            for d in documents:
                index.insert(document=d)
                doc_id = d.id_
                self.log("Inserted DB document: {} / {}".format(n+1, len(documents)))
                self.window.core.ctx.idx.set_meta_as_indexed(id, idx, doc_id)  # update ctx
                n += 1
        except Exception as e:
            errors.append(str(e))
            print(e)
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
        self.log("Indexing documents from database from timestamp: {}".format(from_ts))
        errors = []
        n = 0
        ids = self.get_db_meta_ids_from_ts(from_ts)
        for id in ids:
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
            extra_args: dict = None
    ) -> (int, list):
        """
        Index data from external (remote) resource

        :param idx: index name
        :param index: index instance
        :param url: external url to index
        :param type: type of URL (webpage, feed, etc.)
        :param extra_args: extra arguments for loader
        :return: number of indexed documents, errors
        """
        errors = []
        n = 0

        # check if web loader for defined type exists
        if type not in self.loaders["web"]:
            raise ValueError("No web loader for type: {}".format(type))

        try:
            # remove old content from index if already indexed
            self.remove_old_external(idx, url, type)
            loader = self.loaders["web"][type]

            # additional keyword arguments for data loader
            if extra_args is None:
                extra_args = {}

            extra_args["url"] = url
            loader_args = self.loader_providers[type].prepare_args(**extra_args)

            # get documents from external resource
            documents = loader.load_data(
                **loader_args
            )
            for d in documents:
                index.insert(document=d)
                doc_id = d.id_  # URL is used as document ID
                self.window.core.idx.external.set_indexed(
                    content=url,
                    type=type,
                    idx=idx,
                    doc_id=doc_id,
                )  # update external index
                self.log("Inserted web document: {} / {}".format(n+1, len(documents)))
                n += 1
        except Exception as e:
            errors.append(str(e))
            print(e)
            self.window.core.debug.log(e)
        return n, errors

    def index_urls(
            self,
            idx: str,
            index: BaseIndex,
            urls: list,
            type="webpage",
            extra_args: dict = None
    ) -> (int, list):
        """
        Index data from URLs

        :param idx: index name
        :param index: index instance
        :param urls: list of urls
        :param type: type of URL (webpage, feed, etc.)
        :param extra_args: extra arguments for loader
        :return: number of indexed documents, errors
        """
        errors = []
        n = 0

        # check if web loader for defined type exists
        if type not in self.loaders["web"]:
            msg = "No web loader for type: {}".format(type)
            errors.append(msg)
            print(msg)
            self.window.core.debug.log(msg)
            return n, errors

        for url in urls:
            indexed, errs = self.index_url(
                idx=idx,
                index=index,
                url=url,
                type=type,
                extra_args=extra_args,
            )
            n += indexed
            errors.extend(errs)
        return n, errors

    def remove_old_meta_id(self, idx: str, id: int = 0) -> bool:
        """
        Remove old meta id from index

        :param idx: index name
        :param id: ctx meta id
        :return: True if removed, False if not
        """
        # abort if not configured to replace old documents
        if not self.window.core.config.get("llama.idx.replace_old"):
            return False

        store = self.window.core.idx.get_current_store()
        if self.window.core.idx.ctx.exists(store, idx, id):
            doc_id = self.window.core.idx.ctx.get_doc_id(store, idx, id)
            if doc_id:
                self.log("Removing old document id: {}".format(doc_id))
                self.window.core.idx.storage.remove_document(
                    id=idx,
                    doc_id=doc_id,
                )
                return True
        return False

    def remove_old_file(self, idx: str, file_id: str):
        """
        Remove old file from index

        :param idx: index name
        :param file_id: file id
        :return: True if removed, False if not
        """
        # abort if not configured to replace old documents
        if not self.window.core.config.get("llama.idx.replace_old"):
            return False

        store = self.window.core.idx.get_current_store()
        if self.window.core.idx.files.exists(store, idx, file_id):
            doc_id = self.window.core.idx.files.get_doc_id(store, idx, file_id)
            if doc_id:
                self.log("Removing old document id: {}".format(doc_id))
                self.window.core.idx.storage.remove_document(
                    id=idx,
                    doc_id=doc_id,
                )
                return True
        return False

    def remove_old_external(self, idx: str, content: str, type: str):
        """
        Remove old file from index

        :param idx: index name
        :param content: content
        :param type: type
        :return: True if removed, False if not
        """
        # abort if not configured to replace old documents
        if not self.window.core.config.get("llama.idx.replace_old"):
            return False

        store = self.window.core.idx.get_current_store()
        if self.window.core.idx.external.exists(store, idx, content, type):
            doc_id = self.window.core.idx.external.get_doc_id(store, idx, content, type)
            if doc_id:
                self.log("Removing old document id: {}".format(doc_id))
                self.window.core.idx.storage.remove_document(
                    id=idx,
                    doc_id=doc_id,
                )
                return True
        return False

    def log(self, msg: str):
        """
        Log info message

        :param msg: message
        """
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print("[LLAMA-INDEX] {}".format(msg))
