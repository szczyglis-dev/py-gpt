#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 16:00:00                  #
# ================================================== #

import json

from pygpt_net.item.assistant import AssistantItem
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

    def get_client(self):
        """
        Get OpenAI client

        :return: OpenAI client
        """
        return self.window.core.gpt.get_client()

    def log(self, msg: str, callback: callable = None):
        """
        Log message

        :param msg: message to log
        :param callback: callback log function
        """
        if callback is not None:
            callback(msg)
        else:
            print(msg)

    def create(self, assistant: AssistantItem) -> AssistantItem:
        """
        Create assistant

        :param assistant: assistant object
        :return: assistant object
        """
        client = self.get_client()
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
        client = self.get_client()
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
        Delete assistant by ID

        :param id: assistant ID
        :return: assistant ID
        """
        client = self.get_client()
        response = client.beta.assistants.delete(id)
        if response is not None:
            return response.id

    def thread_create(self) -> str:
        """
        Create thread and return thread ID

        :return: thread ID
        """
        client = self.get_client()
        thread = client.beta.threads.create()
        if thread is not None:
            return thread.id

    def thread_delete(self, id: str) -> str:
        """
        Delete thread by thread ID

        :param id: thread ID
        :return: thread ID
        """
        client = self.get_client()
        response = client.beta.threads.delete(id)
        if response is not None:
            return response.id

    def msg_list(self, thread_id: str) -> list:
        """
        Get messages from thread

        :param thread_id: thread ID
        :return: messages data list
        """
        client = self.get_client()
        thread_messages = client.beta.threads.messages.list(thread_id)
        return thread_messages.data

    def msg_send(self, id: str, text: str, file_ids: list = None):
        """
        Send message to thread

        :param id: thread ID
        :param text: message text
        :param file_ids: uploaded files IDs
        :return: message
        """
        client = self.get_client()
        additional_args = {}
        attachments = []
        for file_id in file_ids:  # append file ids from attachments
            attachments.append({
                "file_id": file_id,
                "tools": [
                    {
                        "type": "code_interpreter"
                    }, {
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

    def get_tools(self, assistant: AssistantItem) -> list:
        """
        Get assistant tools

        :param assistant: assistant item
        :return: tools list
        """
        tools = []
        if assistant.has_tool("code_interpreter"):
            tools.append({"type": "code_interpreter"})
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

        :param assistant: assistant item
        :return: tool resources dict
        """
        resources = {}
        if assistant.has_tool("file_search"):
            if assistant.vector_store is not None and assistant.vector_store != "":
                resources["file_search"] = {
                    "vector_store_ids": [assistant.vector_store]
                }
        return resources

    def run_create(
            self,
            thread_id: str,
            assistant_id: str,
            model: str = None,
            instructions: str = None
    ):
        """
        Create assistant run

        :param thread_id: thread ID
        :param assistant_id: assistant ID
        :param model: model
        :param instructions: instructions
        :return: Run
        """
        client = self.get_client()
        args = {}
        if instructions is not None and instructions != "":
            args['instructions'] = instructions
        if model is not None:
            args['model'] = model

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **args
        )
        if run is not None:
            return run

    def run_create_stream(
            self,
            signals,
            ctx: CtxItem,
            thread_id: str,
            assistant_id: str,
            model: str = None,
            instructions: str = None
    ):
        """
        Create assistant run (stream)

        :param signals: worker signals (callbacks)
        :param ctx: context item
        :param thread_id: thread ID
        :param assistant_id: assistant ID
        :param model: model
        :param instructions: instructions
        :return: Run (final)
        """
        client = self.get_client()
        additional_args = {}
        if instructions is not None and instructions != "":
            additional_args['instructions'] = instructions
        if model is not None:
            additional_args['model'] = model

        with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                event_handler=EventHandler(signals, ctx),
                **additional_args
        ) as stream:
            return stream.get_final_run()

    def run_status(
            self,
            ctx: CtxItem
    ) -> str:
        """
        Get assistant run status

        :param ctx: context item
        :return: run status
        """
        client = self.get_client()
        run = client.beta.threads.runs.retrieve(
            thread_id=ctx.thread,
            run_id=ctx.run_id,
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
        client = self.get_client()
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
        client = self.get_client()
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
        """
        Submit assistant run tool outputs

        :param ctx: context item
        :param outputs: outputs
        :return: run
        """
        # tool output must be string
        for output in outputs:
            if type(output["output"]) is dict or type(output["output"]) is list:
                output["output"] = json.dumps(output["output"])
        client = self.get_client()
        return client.beta.threads.runs.submit_tool_outputs(
            thread_id=ctx.thread,
            run_id=ctx.run_id,
            tool_outputs=outputs,
        )

    def import_all(
            self,
            items: dict,
            order: str = "asc",
            limit: int = 100,
            after: str = None,
            callback: callable = None
    ) -> dict:
        """
        Import assistants from API (all, paginated)

        :param items: items
        :param order: order
        :param limit: limit
        :param after: next page after ID
        :param callback: callback log function
        :return: items dict
        """
        client = self.get_client()
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
                if (hasattr(remote.tool_resources, 'file_search')
                        and remote.tool_resources.file_search is not None):
                    # get vector store ID
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

                self.log("Imported assistant: " + remote.id, callback)

            # next page
            if assistants.has_more:
                return self.import_all(
                    items,
                    order,
                    limit,
                    assistants.last_id,
                    callback,
                )
        return items