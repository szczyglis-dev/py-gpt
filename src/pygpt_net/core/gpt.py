#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 19:00:00                  #
# ================================================== #
import base64
import json
import os
import re
import uuid
from uuid import uuid4

from openai import OpenAI
from .tokens import num_tokens_prompt, num_tokens_extra, num_tokens_from_messages, num_tokens_completion, \
    num_tokens_only
from .context import ContextItem
from .assistants import AssistantItem


class Gpt:
    def __init__(self, config, context):
        """
        GPT Wrapper

        :param config: Config object
        """
        self.config = config
        self.context = context

        self.ai_name = None
        self.user_name = None
        self.system_prompt = None
        self.input_tokens = 0
        self.attachments = {}
        self.thread_id = None  # assistant thread id
        self.assistant_id = None  # assistant id
        self.file_ids = []  # file ids

        if not self.config.initialized:
            self.config.init()

    def init(self):
        pass

    def get_client(self):
        """
        Returns OpenAI client
        :return: OpenAI client
        """
        return OpenAI(
            api_key=self.config.get('api_key'),
            organization=self.config.get('organization_key'),
        )

    def completion(self, prompt, max_tokens, stream_mode=False):
        """
        Calls OpenAI API for completion

        :param prompt: Prompt (user message)
        :param max_tokens: Max output tokens
        :param stream_mode: Stream mode
        :return: Response dict or stream chunks
        """
        # build prompt message
        message = self.build_completion(prompt)

        # prepare stop word if user_name is set
        stop = None
        if self.user_name is not None and self.user_name != '':
            stop = [self.user_name + ':']

        client = self.get_client()
        response = client.completions.create(
            prompt=message,
            model=self.config.get('model'),
            max_tokens=int(max_tokens),
            temperature=self.config.get('temperature'),
            top_p=self.config.get('top_p'),
            frequency_penalty=self.config.get('frequency_penalty'),
            presence_penalty=self.config.get('presence_penalty'),
            stop=stop,
            stream=stream_mode,
        )
        return response

    def chat(self, prompt, max_tokens, stream_mode=False):
        """
        Call OpenAI API for chat

        :param prompt: Prompt (user message)
        :param max_tokens: Max output tokens
        :param stream_mode: Stream mode
        :return: Response dict or stream chunks
        """
        client = self.get_client()

        # build chat messages
        messages = self.build_chat_messages(prompt)
        response = client.chat.completions.create(
            messages=messages,
            model=self.config.get('model'),
            max_tokens=int(max_tokens),
            temperature=self.config.get('temperature'),
            top_p=self.config.get('top_p'),
            frequency_penalty=self.config.get('frequency_penalty'),
            presence_penalty=self.config.get('presence_penalty'),
            stop=None,
            stream=stream_mode,
        )
        return response

    def vision(self, prompt, max_tokens, stream_mode=False):
        """
        Call OpenAI API for chat with vision

        :param prompt: Prompt (user message)
        :param max_tokens: Max output tokens
        :param stream_mode: Stream mode
        :return: Response dict or stream chunks
        """
        client = self.get_client()

        # build chat messages
        messages = self.build_chat_messages(prompt)
        response = client.chat.completions.create(
            messages=messages,
            model=self.config.get('model'),
            max_tokens=int(max_tokens),
            stream=stream_mode,
        )
        return response

    def reset_tokens(self):
        """Resets input tokens counter"""
        self.input_tokens = 0

    def build_chat_messages(self, prompt, system_prompt=None):
        """
        Builds chat messages dict

        :param prompt: Prompt
        :param system_prompt: System prompt (optional)
        :return: Messages dict
        """
        messages = []

        # tokens config
        model = self.config.get('model')
        mode = self.config.get('mode')
        used_tokens = self.count_used_tokens(prompt)
        max_tokens = self.config.get('max_total_tokens')
        model_ctx = self.config.get_model_ctx(model)
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        # names
        ai_name = "assistant"  # default
        user_name = "user"  # default
        if self.user_name is not None and self.user_name != "":
            user_name = self.user_name
        if self.ai_name is not None and self.ai_name != "":
            ai_name = self.ai_name

        # input tokens: reset
        self.reset_tokens()

        # append initial (system) message
        if system_prompt is not None and system_prompt != "":
            messages.append({"role": "system", "content": system_prompt})
        else:
            if self.system_prompt is not None and self.system_prompt != "":
                messages.append({"role": "system", "content": self.system_prompt})

        # append messages from context (memory)
        if self.config.get('use_context'):
            items = self.context.get_prompt_items(model, used_tokens, max_tokens)
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    if mode == "chat":
                        messages.append({"role": "system", "name": user_name, "content": item.input})
                    elif mode == "vision":
                        content = self.build_vision_content(item.input)
                        messages.append({"role": "user", "content": content})

                # output
                if item.output is not None and item.output != "":
                    if mode == "chat":
                        messages.append({"role": "system", "name": ai_name, "content": item.output})
                    elif mode == "vision":
                        content = self.build_vision_content(item.output)
                        messages.append({"role": "assistant", "content": content})

        # append current prompt
        if mode == "chat":
            messages.append({"role": "user", "content": str(prompt)})
        elif mode == "vision":
            content = self.build_vision_content(prompt, append_attachments=True)
            messages.append({"role": "user", "content": content})

        # input tokens: update
        self.input_tokens += num_tokens_from_messages(messages, model)

        return messages

    def build_vision_content(self, text, append_attachments=False):
        """
        Builds vision content

        :param text: Text
        :param append_attachments: Append attachments
        :return: Content dict
        """
        content = [{"type": "text", "text": str(text)}]

        # extract URLs from prompt
        urls = self.extract_urls(text)
        if len(urls) > 0:
            for url in urls:
                content.append({"type": "image_url", "image_url": {"url": url}})

        # local images
        if append_attachments:
            for uuid in self.attachments:
                attachment = self.attachments[uuid]
                if os.path.exists(attachment.path):
                    # check if it's an image
                    if self.is_image(attachment.path):
                        base64_image = self.encode_image(attachment.path)
                        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})

        return content

    def build_completion(self, prompt):
        """
        Builds completion string

        :param prompt: Prompt (current)
        :return: Message string (parsed with context)
        """
        message = ""

        # tokens config
        model = self.config.get('model')
        used_tokens = self.count_used_tokens(prompt)
        max_tokens = self.config.get('max_total_tokens')
        model_ctx = self.config.get_model_ctx(model)
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        # input tokens: reset
        self.reset_tokens()

        if self.system_prompt is not None and self.system_prompt != "":
            message += self.system_prompt

        if self.config.get('use_context'):
            items = self.context.get_prompt_items(model, used_tokens, max_tokens)
            for item in items:
                if item.input_name is not None \
                        and item.output_name is not None \
                        and item.input_name != "" \
                        and item.output_name != "":
                    if item.input is not None and item.input != "":
                        message += "\n" + item.input_name + ": " + item.input
                    if item.output is not None and item.output != "":
                        message += "\n" + item.output_name + ": " + item.output
                else:
                    if item.input is not None and item.input != "":
                        message += "\n" + item.input
                    if item.output is not None and item.output != "":
                        message += "\n" + item.output

        # append names
        if self.user_name is not None \
                and self.ai_name is not None \
                and self.user_name != "" \
                and self.ai_name != "":
            message += "\n" + self.user_name + ": " + str(prompt)
            message += "\n" + self.ai_name + ":"
        else:
            message += "\n" + str(prompt)

        # input tokens: update
        self.input_tokens += num_tokens_completion(message, model)

        return message

    def count_used_tokens(self, input_text):
        """
        Counts used tokens

        :param input_text: Input text
        :return: Used tokens
        """
        model = self.config.get('model')
        mode = self.config.get('mode')
        tokens = 0
        if mode == "chat" or mode == "vision":
            tokens += num_tokens_prompt(self.system_prompt, "", model)  # init (system) prompt
            tokens += num_tokens_only("system", model)
            tokens += num_tokens_prompt(input_text, "", model)  # current input
            tokens += num_tokens_only("user", model)
        else:
            # rest of modes
            tokens += num_tokens_only(self.system_prompt, model)  # init (system) prompt
            tokens += num_tokens_only(input_text, model)  # current input
        tokens += self.config.get('context_threshold')  # context threshold (reserved for next output)
        tokens += num_tokens_extra(model)  # extra tokens (required for output)
        return tokens

    def quick_call(self, prompt, sys_prompt, append_context=False, max_tokens=500, model="gpt-3.5-turbo-1106", temp=0.0):
        """
        Calls OpenAI API with custom prompt

        :param prompt: User input (prompt)
        :param sys_prompt: System input (prompt)
        :param append_context: Append context (memory)
        :param max_tokens: Max output tokens
        :param model: GPT model
        :return: Response text
        """
        client = self.get_client()

        if append_context:
            messages = self.build_chat_messages(prompt, sys_prompt)
        else:
            messages = []
            messages.append({"role": "system", "content": sys_prompt})
            messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temp,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=None,
            )
            return response.choices[0].message.content
        except Exception as e:
            print("Error in custom call: " + str(e))

    def assistant_thread_create(self):
        """
        Creates thread
        :return: Thread ID
        """
        client = self.get_client()
        thread = client.beta.threads.create()
        if thread is not None:
            return thread.id

    def assistant_thread_delete(self, id):
        """
        Deletes thread

        :param id: Thread ID
        :return: Thread ID
        """
        client = self.get_client()
        response = client.beta.threads.delete(id)
        if response is not None:
            return response.id

    def assistant_msg_send(self, id, text):
        """
        Sends message to thread

        :param id: Thread ID
        :param text: Message text
        :return: Message
        """
        client = self.get_client()
        additional_args = {}
        ids = []
        for file_id in self.file_ids:
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

    def assistant_msg_list(self, thread_id):
        """
        Gets messages from thread

        :param thread_id: Thread ID
        :return: Messages
        """
        client = self.get_client()
        thread_messages = client.beta.threads.messages.list(thread_id)
        return thread_messages.data

    def assistant_file_info(self, file_id):
        """
        Gets file info

        :param file_id: File ID
        :return: File info
        """
        client = self.get_client()
        return client.files.retrieve(file_id)

    def assistant_file_download(self, file_id, path):
        """
        Downloads file

        :param file_id: File ID
        :param path: Path
        """
        client = self.get_client()
        content = client.files.retrieve_content(file_id)
        with open(path, 'wb',) as f:
            f.write(content.encode())
            f.close()

    def assistant_run_create(self, thread_id, assistant_id, instructions=None):
        """
        Creates assistant run

        :param thread_id: Thread ID
        :param assistant_id: Assistant ID
        :param instructions: Instructions
        :return: Run
        """
        client = self.get_client()
        additional_args = {}
        if instructions is not None and instructions != "":
            additional_args['instructions'] = instructions
        if self.config.get('model') is not None:
            additional_args['model'] = self.config.get('model')

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **additional_args
        )
        if run is not None:
            return run

    def assistant_run_status(self, thread_id, run_id):
        """
        Gets assistant run status

        :param thread_id: Thread ID
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

    def assistant_file_upload(self, id, path, purpose="assistants"):
        """
        Uploads file to assistant

        :param id: Assistant ID
        :param path: File path
        :param purpose: File purpose
        :return: File ID
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

    def assistant_file_delete(self, assistant_id, file_id):
        """
        Deletes file from assistant

        :param assistant_id: Assistant ID
        :param file_id: File ID
        :return: File ID
        """
        client = self.get_client()
        deleted_file = client.beta.assistants.files.delete(
            assistant_id=assistant_id,
            file_id=file_id
        )
        if deleted_file is not None:
            if deleted_file is not None:
                return deleted_file.id

    def assistant_file_list(self, assistant_id):
        """
        Get files from assistant

        :param assistant_id: Assistant ID
        :return: Files list
        """
        client = self.get_client()
        assistant_files = client.beta.assistants.files.list(
            assistant_id=assistant_id,
            limit=100
        )
        if assistant_files is not None:
            return assistant_files.data

    def assistant_create(self, assistant):
        """
        Creates assistant

        :param assistant: Assistant object
        :return: Assistant object
        """
        client = self.get_client()
        tools = self.assistant_get_tools(assistant)
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

    def assistant_update(self, assistant):
        """
        Updates assistant

        :param assistant: Assistant object
        :return: Assistant object
        """
        client = self.get_client()
        tools = self.assistant_get_tools(assistant)
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

    def assistant_delete(self, id):
        """
        Deletes assistant

        :param id: Assistant ID
        :return: Assistant ID
        """
        client = self.get_client()
        response = client.beta.assistants.delete(id)
        if response is not None:
            return response.id

    def assistant_get_files(self, id, limit=100):
        """
        Gets assistant files

        :param id: Assistant ID
        :param limit: Limit
        :return: Files list
        """
        client = self.get_client()
        return client.beta.assistants.files.list(
            assistant_id=id,
            limit=limit,
        )

    def assistant_import(self, items, order="asc", limit=100):
        """
        Imports assistants from API

        :param items: Items
        :param order: Order
        :param limit: Limit
        :return: Items
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

    def assistant_get_tools(self, assistant):
        """
        Gets assistant tools

        :param assistant: Assistant
        :return: Tools list
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
                tools.append({"type": "function", "function": {"name": function['name'], "parameters": params, "description": function['desc']}})
        return tools

    def call(self, prompt, ctx=None, stream_mode=False):
        """
        Calls OpenAI API

        :param prompt: User input (prompt)
        :param ctx: Context item (memory)
        :param stream_mode: Stream mode (default: False)
        :return: Context item (memory)
        """
        # prepare max tokens
        mode = self.config.get('mode')
        model_tokens = self.config.get_model_tokens(self.config.get('model'))
        max_tokens = self.config.get('max_output_tokens')
        if max_tokens > model_tokens:
            max_tokens = model_tokens

        # minimum 1 token is required
        if max_tokens < 1:
            max_tokens = 1

        # get response
        response = None
        if mode == "completion":
            response = self.completion(prompt, max_tokens, stream_mode)
        elif mode == "chat":
            response = self.chat(prompt, max_tokens, stream_mode)
        elif mode == "vision":
            response = self.vision(prompt, max_tokens, stream_mode)
        elif mode == "assistant":
            response = self.assistant_msg_send(self.thread_id, prompt)
            if response is not None:
                ctx.msg_id = response.id
                run = self.assistant_run_create(self.thread_id, self.assistant_id, self.system_prompt)
                if run is not None:
                    ctx.run_id = run.id
            self.context.add(ctx)
            return ctx  # if assistant then return here

        # async mode (stream)
        if stream_mode:
            # store context (memory)
            if ctx is None:
                ctx = ContextItem(self.config.get('mode'))
                ctx.set_input(prompt, self.user_name)

            ctx.stream = response
            ctx.set_output("", self.ai_name)
            ctx.input_tokens = self.input_tokens  # from global tokens calculation
            self.context.add(ctx)
            return ctx

        if response is None:
            return None

        # check for errors
        if "error" in response:
            print("Error: " + str(response["error"]))
            return None

        # get output
        output = ""
        if mode == "completion":
            output = response.choices[0].text.strip()
        elif mode == "chat" or mode == "vision":
            output = response.choices[0].message.content.strip()

        # store context (memory)
        if ctx is None:
            ctx = ContextItem(self.config.get('mode'))
            ctx.set_input(prompt, self.user_name)

        ctx.set_output(output, self.ai_name)
        ctx.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)
        self.context.add(ctx)

        return ctx

    def stop(self):
        """Stops OpenAI API"""
        pass

    def prepare_ctx_name(self, ctx):
        """Summarizes conversation begin"""
        # default values
        model = 'gpt-3.5-turbo-1106'
        sys_prompt = "You are an expert in conversation summarization"
        text = "Summarize topic of this conversation in one sentence. Use best keywords to describe it. " \
               "Summary must be in the same language as the conversation and it will be used for conversation title " \
               "so it must be EXTREMELY SHORT and concise - use maximum 5 words: \n\n"
        text += "User: " + str(ctx.input) + "\nAI Assistant: " + str(ctx.output)

        # custom values
        if self.config.get('ctx.auto_summary.system') is not None and self.config.get('ctx.auto_summary.system') != "":
            sys_prompt = self.config.get('ctx.auto_summary.system')
        if self.config.get('ctx.auto_summary.prompt') is not None and self.config.get('ctx.auto_summary.prompt') != "":
            text = self.config.get('ctx.auto_summary.prompt').replace("{input}", str(ctx.input)).replace("{output}", str(ctx.output))
        if self.config.get('ctx.auto_summary.model') is not None and self.config.get('ctx.auto_summary.model') != "":
            model = self.config.get('ctx.auto_summary.model')

        # call OpenAI API
        response = self.quick_call(text, sys_prompt, False, 500, model)
        if response is not None:
            return response

    def clear(self):
        """Clears context (memory)"""
        self.context.clear()

    def extract_urls(self, text):
        """Extracts urls from text"""
        return re.findall(r'(https?://\S+)', text)

    def is_image(self, path):
        """Checks if url is image"""
        return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))

    def encode_image(self, image_path):
        """
        Encodes image to base64
        :param image_path:
        :return: base64 encoded image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
