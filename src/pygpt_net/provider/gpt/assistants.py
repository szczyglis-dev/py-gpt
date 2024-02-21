#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.21 14:00:00                  #
# ================================================== #

import json
import os

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.ctx import CtxItem
from .worker.assistants import AssistantsWorker
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
        ids = []
        for file_id in self.file_ids:  # append file ids from attachments
            ids.append(file_id)
        if ids:
            additional_args['file_ids'] = ids

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

        # attach to assistant
        if result is not None:
            file_id = result.id
            assistant_file = client.beta.assistants.files.create(
                assistant_id=id,
                file_id=file_id,
            )
            if assistant_file is not None:
                return assistant_file.id

    def file_delete(
            self,
            assistant_id: str,
            file_id: str
    ) -> str:
        """
        Delete file from assistant

        :param assistant_id: assistant ID
        :param file_id: file ID
        :return: file ID
        """
        client = self.window.core.gpt.get_client()
        deleted_file = client.beta.assistants.files.delete(
            assistant_id=assistant_id,
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
        result = client.beta.assistants.create(
            instructions=assistant.instructions,
            description=assistant.description,
            name=assistant.name,
            tools=tools,
            model=assistant.model,
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
        result = client.beta.assistants.update(
            assistant.id,
            instructions=assistant.instructions,
            description=assistant.description,
            name=assistant.name,
            tools=tools,
            model=assistant.model,
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

    def import_api(
            self,
            items: dict,
            order: str = "asc",
            limit: int = 100
    ) -> dict:
        """
        Import assistants from API

        :param items: items
        :param order: order
        :param limit: limit
        :return: items dict
        """
        client = self.window.core.gpt.get_client()
        assistants = client.beta.assistants.list(
            order=order,
            limit=limit,
        )
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

                # append files
                for file_id in remote.file_ids:
                    if not items[id].has_file(file_id):
                        items[id].add_file(file_id)

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
        if assistant.has_tool("retrieval"):
            tools.append({"type": "retrieval"})
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
