#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import os
from typing import Optional, List

from pygpt_net.item.assistant import AssistantStoreItem


class Store:
    def __init__(self, window=None):
        """
        GPT vector stores API Wrapper

        :param window: Window instance
        """
        self.window = window

    def get_client(self):
        """
        Get OpenAI client

        :return: OpenAI client
        """
        return self.window.core.gpt.get_client()

    def log(
            self,
            msg: str,
            callback: Optional[callable] = None
    ):
        """
        Log message

        :param msg: message to log
        :param callback: callback log function
        """
        if callback is not None:
            callback(msg)
        else:
            print(msg)

    def get_file(self, file_id: str):
        """
        Get file info

        :param file_id: file ID
        :return: file info
        """
        client = self.get_client()
        return client.files.retrieve(file_id)

    def upload(
            self,
            path: str,
            purpose: str = "assistants"
    ) -> Optional[str]:
        """
        Upload file to assistant

        :param path: file path
        :param purpose: file purpose
        :return: file ID or None
        """
        client = self.get_client()
        if not os.path.exists(path):
            return None

        result = client.files.create(
            file=open(path, "rb"),
            purpose=purpose,
        )
        if result is not None:
            return result.id

    def download(
            self,
            file_id: str,
            path: str
    ):
        """
        Download file

        :param file_id: file ID
        :param path: path to save file
        """
        client = self.window.core.gpt.get_client()
        content = client.files.content(file_id)
        data = content.read()
        with open(path, 'wb', ) as f:
            f.write(data)
            
    def get_files_ids_all(
            self,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
    ) -> list:
        """
        Get all vector store IDs

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: files IDs (all, paginated)
        """
        client = self.get_client()
        args = {
            "order": order,
            "limit": limit,
        }
        if after is not None:
            args['after'] = after
        stores = client.files.list(**args)
        if stores is not None:
            for remote in stores.data:
                id = remote.id
                if id not in items:
                    items.append(id)
            # next page
            if stores.has_more:
                return self.get_files_ids_all(
                    items,
                    order,
                    limit,
                    stores.last_id,
                )
        return items

    def get_files_ids(self) -> List[str]:
        """
        Get all files IDs

        :return: files IDs
        """
        client = self.get_client()
        items = []
        stores = client.files.list()
        if stores is not None:
            for remote in stores.data:
                id = remote.id
                if id not in items:
                    items.append(id)
        return items

    def remove_files(
            self,
            callback: Optional[callable] = None
    ) -> int:
        """
        Remove all files

        :param callback: callback function
        :return: number of deleted files
        """
        num = 0
        files = self.get_files_ids()
        for file_id in files:
            self.log("Removing file: " + file_id, callback)
            try:
                self.delete_file(file_id)
                num += 1
            except Exception as e:
                msg = "Error removing file {}: {}".format(file_id, str(e))
                self.log(msg, callback)
        return num

    def remove_store_files(
            self,
            store_id: str,
            callback: Optional[callable] = None
    ) -> int:
        """
        Remove all files from store

        :param store_id: store ID
        :param callback: callback function
        :return: number of deleted files
        """
        num = 0
        files = self.get_store_files_ids(store_id, [])
        for file_id in files:
            self.log("Removing file: " + file_id, callback)
            try:
                self.delete_store_file(store_id, file_id)
                num += 1
            except Exception as e:
                msg = "Error removing file {}: {}".format(file_id, str(e))
                self.log(msg, callback)
        return num

    def import_stores(
            self,
            items: dict,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
            callback: Optional[callable] = None
    ) -> dict:
        """
        Import vector stores from API

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :param callback: callback function
        :return: vector stores objects
        """
        client = self.get_client()
        args = {
            "order": order,
            "limit": limit,
        }
        if after is not None:
            args['after'] = after
        stores = client.beta.vector_stores.list(**args)
        if stores is not None:
            for remote in stores.data:
                id = remote.id
                if id not in items:
                    items[id] = AssistantStoreItem()
                tmp_name = remote.name
                if tmp_name is None:
                    items[id].is_thread = True  # tmp store for thread
                    tmp_name = ""
                items[id].id = id
                items[id].name = tmp_name
                items[id].file_ids = []
                items[id].status = self.window.core.assistants.store.parse_status(remote)
                self.window.core.assistants.store.append_status(items[id], items[id].status)
                self.log("Imported vector store: " + id, callback)
            # next page
            if stores.has_more:
                return self.import_stores(
                    items,
                    order,
                    limit,
                    stores.last_id,
                    callback,
                )
        return items

    def create_store(
            self,
            name: str,
            expire_days: int = 0
    ):
        """
        Create vector store

        :param name: store name
        :param expire_days: expire days
        :return: vector store object
        """
        client = self.get_client()
        expires_after = {
            "anchor": "last_active_at",
            "days": expire_days,
        }
        if expire_days <= 0:
            expires_after = None
        vector_store = client.beta.vector_stores.create(
            name=name,
            expires_after=expires_after,
        )
        if vector_store is not None:
            return vector_store

    def update_store(
            self,
            id: str,
            name: str,
            expire_days: int = 0
    ):
        """
        Update vector store

        :param id: store id
        :param name: store name
        :param expire_days: expire days
        :return: vector store object
        """
        client = self.get_client()
        expires_after = {
            "anchor": "last_active_at",
            "days": expire_days,
        }
        if expire_days <= 0:
            expires_after = None
        vector_store = client.beta.vector_stores.update(
            vector_store_id=id,
            name=name,
            expires_after=expires_after,
        )
        if vector_store is not None:
            return vector_store

    def get_store(self, id: str):
        """
        Get vector store by ID

        :param id: store id
        :return: vector store
        """
        client = self.get_client()
        vector_store = client.beta.vector_stores.retrieve(
            vector_store_id=id,
        )
        if vector_store is not None:
            return vector_store

    def remove_store(self, id: str):
        """
        Delete vector store by ID

        :param id: store id
        :return: vector store object
        """
        client = self.get_client()
        vector_store = client.beta.vector_stores.delete(
            vector_store_id=id,
        )
        if vector_store is not None:
            return vector_store

    def get_stores_ids(
            self,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
    ) -> list:
        """
        Get all vector stores IDs

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: IDs dict (all, paginated)
        """
        client = self.get_client()
        args = {
            "order": order,
            "limit": limit,
        }
        if after is not None:
            args['after'] = after
        stores = client.beta.vector_stores.list(**args)
        if stores is not None:
            for remote in stores.data:
                id = remote.id
                if id not in items:
                    items.append(id)
            # next page
            if stores.has_more:
                return self.get_stores_ids(
                    items,
                    order,
                    limit,
                    stores.last_id,
                )
        return items

    def get_store_files_ids(
            self,
            store_id: str,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
    ) -> list:
        """
        Get all vector store files IDs

        :param store_id: store ID
        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: IDs dict  (all, paginated)
        """
        client = self.get_client()
        args = {
            "vector_store_id": store_id,
            "order": order,
            "limit": limit,
        }
        if after is not None:
            args['after'] = after
        files = client.beta.vector_stores.files.list(**args)
        if files is not None:
            for remote in files.data:
                id = remote.id
                if id not in items:
                    items.append(id)
            # next page
            if files.has_more:
                return self.get_store_files_ids(
                    store_id,
                    items,
                    order,
                    limit,
                    files.last_id,
                )
        return items

    def remove_from_stores(self) -> int:
        """
        Remove all files from vector stores

        :return: number of deleted files
        """
        stores = self.get_stores_ids([])
        num = 0
        for store_id in stores:
            files = self.get_store_files_ids(store_id, [])
            for file_id in files:
                self.log("Removing file from vector store [{}]:{} ".format(store_id, file_id))
                self.delete_store_file(store_id, file_id)
                num += 1
        return num

    def remove_from_store(self, store_id: str) -> int:
        """
        Remove all files from vector store

        :param store_id: store ID
        :return: number of deleted files
        """
        files = self.get_store_files_ids(store_id, [])
        num = 0
        for file_id in files:
            self.log("Removing file from vector store [{}]:{} ".format(store_id, file_id))
            self.delete_store_file(store_id, file_id)
            num += 1
        return num

    def remove_all(
            self,
            callback: Optional[callable] = None
    ) -> int:
        """
        Remove all vector stores

        :param callback: callback function
        :return: number of deleted stores
        """
        num = 0
        stores = self.get_stores_ids([])
        for store_id in stores:
            self.log("Removing vector store: " + store_id, callback)
            try:
                self.remove_store(store_id)
                num += 1
            except Exception as e:
                msg = "Error removing vector store {}: {}".format(store_id, str(e))
                self.log(msg, callback)
        return num

    def add_file(
            self,
            store_id: str,
            file_id: str
    ):
        """
        Add file to vector store

        :param store_id: store id
        :param file_id: file id
        :return: vector store file
        """
        client = self.get_client()
        vector_store_file = client.beta.vector_stores.files.create(
            vector_store_id=store_id,
            file_id=file_id,
        )
        if vector_store_file is not None:
            return vector_store_file

    def delete_file(
            self,
            file_id: str
    ) -> str:
        """
        Delete file from assistant

        :param file_id: file ID
        :return: file ID
        """
        client = self.get_client()
        deleted_file = client.files.delete(
            file_id=file_id
        )
        if deleted_file is not None:
            if deleted_file is not None:
                return deleted_file.id

    def delete_store_file(
            self,
            store_id: str,
            file_id: str
    ):
        """
        Delete file from vector store

        :param store_id: store id
        :param file_id: file id
        :return: vector store file
        """
        client = self.get_client()
        vector_store_file = client.beta.vector_stores.files.delete(
            vector_store_id=store_id,
            file_id=file_id,
        )
        if vector_store_file is not None:
            return vector_store_file

    def import_stores_files(
            self,
            callback: Optional[callable] = None
    ) -> int:
        """
        Import all vector stores files

        :param callback: callback function
        :return: num of imported files
        """
        store_ids = self.get_stores_ids([])
        num = 0
        for store_id in store_ids:
            items = []
            try:
                items = self.import_store_files(
                    store_id,
                    items,
                    callback=callback,
                )
            except Exception as e:
                msg = "Error importing store {} files list: {}".format(store_id, str(e))
                self.log(msg, callback)
            num += len(items)
        return num

    def import_store_files(
            self,
            store_id: str,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
            callback: Optional[callable] = None
    ) -> list:
        """
        Import and get all vector store files IDs

        :param store_id: store ID
        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :param callback: callback function
        :return: imported IDs dict
        """
        client = self.get_client()
        args = {
            "vector_store_id": store_id,
            "order": order,
            "limit": limit,
        }
        if after is not None:
            args['after'] = after
        files = client.beta.vector_stores.files.list(**args)
        if files is not None:
            for remote in files.data:
                try:
                    id = remote.id
                    if id not in items:
                        items.append(id)
                        data = self.get_file(remote.id)
                        self.window.core.assistants.files.insert(store_id, data)  # add remote file to DB
                        msg = "Imported file ID {} to store {}".format(remote.id, store_id)
                        self.log(msg, callback)
                except Exception as e:
                    msg = "Error importing file {} to store {}: {}".format(remote.id, store_id, str(e))
                    self.log(msg, callback)
            # next page
            if files.has_more:
                return self.import_store_files(
                    store_id,
                    items,
                    order,
                    limit,
                    files.last_id,
                    callback,
                )
        return items
