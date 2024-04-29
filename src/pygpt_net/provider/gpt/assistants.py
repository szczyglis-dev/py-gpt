#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 12:00:00                  #
# ================================================== #

import json
import os

from pygpt_net.item.assistant import AssistantItem, AssistantStoreItem
from pygpt_net.item.ctx import CtxItem

from .worker.assistants import AssistantsWorker, EventHandler
from .worker.importer import Importer


class Assistants:
    def __init__(self, window=None):
        """
        GPT Assistants API Wrapper

        :param window: Window instance
        """
        self.window = window
        self.worker = AssistantsWorker(window)
        self.importer = Importer(window)
        self.file_ids = []  # file ids

    def thread_create(self):
        """
        Create thread

        :return: thread ID
        :rtype: str
        """
        client = self.window.core.gpt.get_client()
        thread = client.beta.threads.create()
        if thread is not None:
            return thread.id

    def thread_delete(self, id: str) -> str:
        """
        Delete thread

        :param id: thread ID
        :return: thread ID
        :rtype: str
        """
        client = self.window.core.gpt.get_client()
        response = client.beta.threads.delete(id)
        if response is not None:
            return response.id

    def msg_send(self, id: str, text: str):
        """
        Send message to thread

        :param id: thread ID
        :param text: message text
        :return: message
        """
        client = self.window.core.gpt.get_client()
        additional_args = {}
        attachments = []
        for file_id in self.file_ids:  # append file ids from attachments
            attachments.append({
                "file_id": file_id,
                "tools": [
                    {
                        "type": "code_interpreter"
                    },{
                        "type": "file_search"
                    },
                ]
            })
        if attachments:
            additional_args['attachments'] = attachments

        message = client.beta.threads.messages.create(
            id,
            role="user",
            content=text,
            **additional_args
        )
        if message is not None:
            return message

    def msg_list(self, thread_id: str) -> list:
        """
        Get messages from thread

        :param thread_id: thread ID
        :return: messages
        """
        client = self.window.core.gpt.get_client()
        thread_messages = client.beta.threads.messages.list(thread_id)
        return thread_messages.data

    def file_info(self, file_id: str):
        """
        Get file info

        :param file_id: file ID
        :return: file info
        """
        client = self.window.core.gpt.get_client()
        return client.files.retrieve(file_id)

    def file_download(
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

    def run_create_stream(
            self,
            signals,
            ctx: CtxItem,
            thread_id: str,
            assistant_id: str,
            instructions=None
    ):
        """
        Create assistant run (stream)

        :param signals: worker signals
        :param ctx: context item
        :param thread_id: tread ID
        :param assistant_id: assistant ID
        :param instructions: instructions
        """
        client = self.window.core.gpt.get_client()
        additional_args = {}
        if instructions is not None and instructions != "":
            additional_args['instructions'] = instructions

        model = self.window.core.config.get('model')
        if model is not None:
            model_id = self.window.core.models.get_id(model)
            additional_args['model'] = model_id

        with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=EventHandler(signals, ctx),
                **additional_args
        ) as stream:
            return stream.get_final_run()

    def run_create(
            self,
            thread_id: str,
            assistant_id: str,
            instructions=None
    ):
        """
        Create assistant run

        :param thread_id: tread ID
        :param assistant_id: assistant ID
        :param instructions: instructions
        :return: Run
        """
        client = self.window.core.gpt.get_client()
        additional_args = {}
        if instructions is not None and instructions != "":
            additional_args['instructions'] = instructions
        model = self.window.core.config.get('model')
        if model is not None:
            model_id = self.window.core.models.get_id(model)
            additional_args['model'] = model_id

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **additional_args
        )
        if run is not None:
            return run

    def run_status(
            self,
            ctx: CtxItem
    ) -> str:
        """
        Get assistant run status

        :param ctx: context item
        :return: run status
        """
        client = self.window.core.gpt.get_client()
        run = client.beta.threads.runs.retrieve(
            thread_id=ctx.thread,
            run_id=ctx.run_id
        )
        if run is not None:
            if run.usage is not None:
                ctx.input_tokens = run.usage["prompt_tokens"]
                ctx.output_tokens = run.usage["completion_tokens"]
                ctx.total_tokens = run.usage["total_tokens"]
            return run.status

    def run_get(
            self,
            ctx: CtxItem
    ) -> str:
        """
        Get assistant run status

        :param ctx: context item
        :return: run
        """
        client = self.window.core.gpt.get_client()
        run = client.beta.threads.runs.retrieve(
            thread_id=ctx.thread,
            run_id=ctx.run_id,
        )
        return run

    def run_stop(
            self,
            ctx: CtxItem
    ) -> str:
        """
        Stop assistant run

        :param ctx: context item
        :return: run status
        """
        client = self.window.core.gpt.get_client()
        run = client.beta.threads.runs.cancel(
            thread_id=ctx.thread,
            run_id=ctx.run_id,
        )
        if run is not None:
            if run.usage is not None:
                ctx.input_tokens = run.usage["prompt_tokens"]
                ctx.output_tokens = run.usage["completion_tokens"]
                ctx.total_tokens = run.usage["total_tokens"]
            return run.status

    def run_submit_tool(
            self,
            ctx: CtxItem,
            outputs: list,
    ):

        client = self.window.core.gpt.get_client()
        return client.beta.threads.runs.submit_tool_outputs(
            thread_id=ctx.thread,
            run_id=ctx.run_id,
            tool_outputs=outputs,
        )

    def file_upload(
            self,
            id: str,
            path: str,
            purpose: str = "assistants"
    ) -> str or None:
        """
        Upload file to assistant

        :param id: assistant ID
        :param path: file path
        :param purpose: file purpose
        :return: file ID or None
        """
        client = self.window.core.gpt.get_client()
        if not os.path.exists(path):
            return None

        result = client.files.create(
            file=open(path, "rb"),
            purpose=purpose,
        )
        if result is not None:
            return result.id

    def file_delete(
            self,
            file_id: str
    ) -> str:
        """
        Delete file from assistant

        :param file_id: file ID
        :return: file ID
        """
        client = self.window.core.gpt.get_client()
        deleted_file = client.files.delete(
            file_id=file_id
        )
        if deleted_file is not None:
            if deleted_file is not None:
                return deleted_file.id

    def file_list(self, assistant_id: str) -> list:
        """
        Get files from assistant

        :param assistant_id: assistant ID
        :return: files list
        """
        client = self.window.core.gpt.get_client()
        assistant_files = client.beta.assistants.files.list(
            assistant_id=assistant_id,
            limit=100
        )
        if assistant_files is not None:
            return assistant_files.data

    def create(self, assistant: AssistantItem) -> AssistantItem:
        """
        Create assistant

        :param assistant: assistant object
        :return: assistant object
        """
        client = self.window.core.gpt.get_client()
        tools = self.get_tools(assistant)
        tool_resources = self.get_tool_resources(assistant)
        result = client.beta.assistants.create(
            instructions=assistant.instructions,
            description=assistant.description,
            name=assistant.name,
            tools=tools,
            model=assistant.model,
            tool_resources=tool_resources,
        )
        if result is not None:
            assistant.id = result.id
            return assistant

    def update(self, assistant: AssistantItem) -> AssistantItem:
        """
        Update assistant

        :param assistant: assistant object
        :return: assistant object
        """
        client = self.window.core.gpt.get_client()
        tools = self.get_tools(assistant)
        tool_resources = self.get_tool_resources(assistant)
        result = client.beta.assistants.update(
            assistant.id,
            instructions=assistant.instructions,
            description=assistant.description,
            name=assistant.name,
            tools=tools,
            model=assistant.model,
            tool_resources=tool_resources,
        )
        if result is not None:
            assistant.id = result.id
            return assistant

    def delete(self, id: str) -> str:
        """
        Delete assistant

        :param id: assistant ID
        :return: assistant ID
        :rtype: str
        """
        client = self.window.core.gpt.get_client()
        response = client.beta.assistants.delete(id)
        if response is not None:
            return response.id

    def get_files(self, id: str, limit: int = 100) -> list:
        """
        Get assistant files

        :param id: assistant ID
        :param limit: limit
        :return: files list
        """
        client = self.window.core.gpt.get_client()
        return client.beta.assistants.files.list(
            assistant_id=id,
            limit=limit,
        )

    def files_get_all_ids(
            self,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
    ) -> list:
        """
        Get all vector store IDs

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
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
            if stores.has_more:
                return self.files_get_all_ids(items, order, limit, stores.last_id)
        return items

    def files_get_ids(self) -> list:
        """
        Get all vector store IDs

        :return: items IDs
        """
        client = self.window.core.gpt.get_client()
        items = []
        stores = client.files.list()
        if stores is not None:
            for remote in stores.data:
                id = remote.id
                if id not in items:
                    items.append(id)
        return items

    def files_truncate(self) -> int:
        """
        Truncate all files

        :return: number of deleted files
        """
        i = 0
        files = self.files_get_ids()
        for file_id in files:
            print("Removing file: " + file_id)
            self.file_delete(file_id)
            i += 1
        return i

    def import_assistants(
            self,
            items: dict,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
    ) -> dict:
        """
        Import assistants from API

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
        args = {
            "order": order,
            "limit": limit,
        }
        if after is not None:
            args['after'] = after
        assistants = client.beta.assistants.list(**args)
        if assistants is not None:
            for remote in assistants.data:
                id = remote.id
                if id not in items:
                    items[id] = AssistantItem()
                items[id].id = id
                items[id].name = remote.name
                items[id].description = remote.description
                items[id].instructions = remote.instructions
                items[id].model = remote.model
                items[id].meta = remote.metadata

                # reset tools
                items[id].clear_tools()
                items[id].vector_store = ""

                # tool resources
                if hasattr(remote.tool_resources, 'file_search') and remote.tool_resources.file_search is not None:
                    if remote.tool_resources.file_search.vector_store_ids:
                        items[id].vector_store = remote.tool_resources.file_search.vector_store_ids[0]

                # append tools
                for tool in remote.tools:
                    if tool.type == "function":
                        # pack params to JSON string
                        params = ''
                        try:
                            params = json.dumps(
                                tool.function.parameters
                            )
                        except:
                            pass
                        items[id].add_function(
                            tool.function.name,
                            params,
                            tool.function.description
                        )
                    else:
                        if tool.type in items[id].tools:
                            items[id].tools[tool.type] = True
            # next page
            if assistants.has_more:
                return self.import_assistants(items, order, limit, assistants.last_id)
        return items

    def import_vector_stores(
            self,
            items: dict,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
    ) -> dict:
        """
        Import vector stores from API

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
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
            # next page
            if stores.has_more:
                return self.import_vector_stores(items, order, limit, stores.last_id)
        return items

    def get_tools(self, assistant: AssistantItem) -> list:
        """
        Get assistant tools

        :param assistant: assistant
        :return: tools list
        """
        tools = []
        if assistant.has_tool("code_interpreter"):
            tools.append({"type": "code_interpreter"})
        # if assistant.has_tool("retrieval"):
            # tools.append({"type": "retrieval"})  # deprecated
        if assistant.has_tool("file_search"):
            tools.append({"type": "file_search"})

        # functions
        if assistant.has_functions():
            functions = assistant.get_functions()
            for function in functions:
                if str(function['name']).strip() == '' or function['name'] is None:
                    continue
                params = json.loads(function['params'])  # unpack JSON from string
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": function['name'],
                            "parameters": params,
                            "description": function['desc'],
                        }
                    }
                )
        return tools

    def get_tool_resources(self, assistant: AssistantItem) -> dict:
        """
        Get assistant tool resources

        :param assistant: assistant
        :return: tool resources dict
        """
        resources = {}
        if assistant.has_tool("file_search"):
            if assistant.vector_store is not None and assistant.vector_store != "":
                resources["file_search"] = {
                    "vector_store_ids": [assistant.vector_store]
                }
        return resources

    def vs_create(self, name: str, expire_days: int = 0):
        """
        Create vector store

        :param name: store name
        :param expire_days: expire days
        :return: vector store
        """
        client = self.window.core.gpt.get_client()
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

    def vs_update(self, id: str, name: str, expire_days: int = 0):
        """
        Update vector store

        :param id: store id
        :param name: store name
        :param expire_days: expire days
        :return: vector store
        """
        client = self.window.core.gpt.get_client()
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

    def vs_get(self, id: str):
        """
        Get vector store by ID

        :param id: store id
        :return: vector store
        """
        client = self.window.core.gpt.get_client()
        vector_store = client.beta.vector_stores.retrieve(
            vector_store_id=id,
        )
        if vector_store is not None:
            return vector_store

    def vs_delete(self, id: str):
        """
        Delete vector store

        :param id: store id
        :return: vector store
        """
        client = self.window.core.gpt.get_client()
        vector_store = client.beta.vector_stores.delete(
            vector_store_id=id,
        )
        if vector_store is not None:
            return vector_store

    def vs_get_all_ids(
            self,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
    ) -> list:
        """
        Get all vector store IDs

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
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
            if stores.has_more:
                return self.vs_get_all_ids(items, order, limit, stores.last_id)
        return items

    def vs_get_all_files_ids(
            self,
            store_id: str,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
    ) -> list:
        """
        Get all vector store files IDs

        :param store_id: store ID
        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
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
            if files.has_more:
                return self.vs_get_all_files_ids(store_id, items, order, limit, files.last_id)
        return items

    def vs_remove_files_from_stores(self) -> int:
        """
        Remove all files from vector stores

        :return: number of deleted files
        """
        stores = self.vs_get_all_ids([])
        i = 0
        for store_id in stores:
            files = self.vs_get_all_files_ids(store_id, [])
            for file_id in files:
                print("Removing file from vector store [{}]:{} ".format(store_id, file_id))
                self.vs_delete_file(store_id, file_id)
                i += 1
        return i

    def vs_truncate_stores(self) -> int:
        """
        Truncate all vector stores

        :return: number of deleted stores
        """
        i = 0
        stores = self.vs_get_all_ids([])
        for store_id in stores:
            print("Removing vector store: " + store_id)
            self.vs_delete(store_id)
            i += 1
        return i


    def vs_add_file(self, store_id: str, file_id: str):
        """
        Add file to vector store

        :param store_id: store id
        :param file_id: file id
        :return: vector store
        """
        client = self.window.core.gpt.get_client()
        vector_store_file = client.beta.vector_stores.files.create(
            vector_store_id=store_id,
            file_id=file_id,
        )
        if vector_store_file is not None:
            return vector_store_file

    def vs_delete_file(self, store_id: str, file_id: str):
        """
        Delete file from vector store

        :param store_id: store id
        :param file_id: file id
        :return: vector store
        """
        client = self.window.core.gpt.get_client()
        vector_store_file = client.beta.vector_stores.files.delete(
            vector_store_id=store_id,
            file_id=file_id,
        )
        if vector_store_file is not None:
            return vector_store_file

    def vs_import_all_files(self) -> int:
        """
        Import all vector store files

        :return: result
        """
        store_ids = self.vs_get_all_ids([])
        sum = 0
        for store_id in store_ids:
            items = []
            items = self.vs_import_store_files(store_id, items)
            sum += len(items)
        return sum

    def vs_import_store_files(
            self,
            store_id: str,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
    ) -> list:
        """
        Get all vector store files IDs

        :param store_id: store ID
        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
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
                    # add remote file to DB
                    data = self.file_info(remote.id)
                    self.window.core.assistants.files.insert(store_id, data)
                    print("Imported file ID {} to store {}".format(remote.id, store_id))

            if files.has_more:
                return self.vs_import_store_files(store_id, items, order, limit, files.last_id)
        return items