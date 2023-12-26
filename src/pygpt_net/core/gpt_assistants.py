#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import json
import os

from openai import OpenAI
from pygpt_net.item.assistant import AssistantItem


class GptAssistants:
    def __init__(self, window=None):
        """
        GPT Assistants API Wrapper

        :param window: Window instance
        """
        self.window = window
        self.file_ids = []  # file ids

    def get_client(self):
        """
        Return OpenAI client

        :return: OpenAI client
        :rtype: OpenAI
        """
        return OpenAI(
            api_key=self.window.core.config.get('api_key'),
            organization=self.window.core.config.get('organization_key'),
        )

    def thread_create(self):
        """
        Create thread

        :return: thread ID
        :rtype: str
        """
        client = self.get_client()
        thread = client.beta.threads.create()
        if thread is not None:
            return thread.id

    def thread_delete(self, id):
        """
        Delete thread

        :param id: thread ID
        :return: thread ID
        :rtype: str
        """
        client = self.get_client()
        response = client.beta.threads.delete(id)
        if response is not None:
            return response.id

    def msg_send(self, id, text):
        """
        Send message to thread

        :param id: thread ID
        :param text: message text
        :return: message
        """
        client = self.get_client()
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

    def msg_list(self, thread_id):
        """
        Get messages from thread

        :param thread_id: thread ID
        :return: messages
        :rtype: list
        """
        client = self.get_client()
        thread_messages = client.beta.threads.messages.list(thread_id)
        return thread_messages.data

    def file_info(self, file_id):
        """
        Get file info

        :param file_id: file ID
        :return: file info
        """
        client = self.get_client()
        return client.files.retrieve(file_id)

    def file_download(self, file_id, path):
        """
        Download file

        :param file_id: file ID
        :param path: path to save file
        """
        client = self.get_client()
        content = client.files.retrieve_content(file_id)
        with open(path, 'wb', ) as f:
            f.write(content.encode())
            f.close()

    def run_create(self, thread_id, assistant_id, instructions=None):
        """
        Create assistant run

        :param thread_id: tread ID
        :param assistant_id: assistant ID
        :param instructions: instructions
        :return: Run
        """
        client = self.get_client()
        additional_args = {}
        if instructions is not None and instructions != "":
            additional_args['instructions'] = instructions
        if self.window.core.config.get('model') is not None:
            additional_args['model'] = self.window.core.config.get('model')

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **additional_args
        )
        if run is not None:
            return run

    def run_status(self, thread_id, run_id):
        """
        Get assistant run status

        :param thread_id: thread ID
        :param run_id: Run ID
        :return: Run status
        """
        client = self.get_client()
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        if run is not None:
            return run.status

    def file_upload(self, id, path, purpose="assistants"):
        """
        Upload file to assistant

        :param id: assistant ID
        :param path: file path
        :param purpose: file purpose
        :return: file ID
        :rtype: str
        """
        client = self.get_client()

        if not os.path.exists(path):
            return None

        # upload file
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

    def file_delete(self, assistant_id, file_id):
        """
        Delete file from assistant

        :param assistant_id: assistant ID
        :param file_id: file ID
        :return: file ID
        :rtype: str
        """
        client = self.get_client()
        deleted_file = client.beta.assistants.files.delete(
            assistant_id=assistant_id,
            file_id=file_id
        )
        if deleted_file is not None:
            if deleted_file is not None:
                return deleted_file.id

    def file_list(self, assistant_id):
        """
        Get files from assistant

        :param assistant_id: assistant ID
        :return: files list
        :rtype: list
        """
        client = self.get_client()
        assistant_files = client.beta.assistants.files.list(
            assistant_id=assistant_id,
            limit=100
        )
        if assistant_files is not None:
            return assistant_files.data

    def create(self, assistant):
        """
        Create assistant

        :param assistant: assistant object
        :return: assistant object
        :rtype: Assistant
        """
        client = self.get_client()
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

    def update(self, assistant):
        """
        Update assistant

        :param assistant: assistant object
        :return: assistant object
        :rtype: Assistant
        """
        client = self.get_client()
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

    def delete(self, id):
        """
        Delete assistant

        :param id: assistant ID
        :return: assistant ID
        :rtype: str
        """
        client = self.get_client()
        response = client.beta.assistants.delete(id)
        if response is not None:
            return response.id

    def get_files(self, id, limit=100):
        """
        Get assistant files

        :param id: assistant ID
        :param limit: limit
        :return: files list
        :rtype: list
        """
        client = self.get_client()
        return client.beta.assistants.files.list(
            assistant_id=id,
            limit=limit,
        )

    def import_assistants(self, items, order="asc", limit=100):
        """
        Import assistants from API

        :param items: items
        :param order: order
        :param limit: limit
        :return: items dict
        :rtype: dict
        """
        client = self.get_client()
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

                # check if assistant tool is bool
                if isinstance(items[id].tools['function'], bool):
                    items[id].tools['function'] = []

                # append files
                for file_id in remote.file_ids:
                    if not items[id].has_file(file_id):
                        items[id].add_file(file_id)
                for tool in remote.tools:
                    if tool.type == "function":
                        # pack params to JSON string
                        params = ''
                        try:
                            params = json.dumps(tool.function.parameters)
                        except:
                            pass
                        items[id].add_function(tool.function.name, params, tool.function.description)
                    else:
                        items[id].tools[tool.type] = True
        return items

    def get_tools(self, assistant):
        """
        Get assistant tools

        :param assistant: assistant
        :return: tools list
        :rtype: list
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
                tools.append({"type": "function", "function": {"name": function['name'], "parameters": params,
                                                               "description": function['desc']}})
        return tools
