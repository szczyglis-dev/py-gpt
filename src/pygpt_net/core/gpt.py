#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 02:00:00                  #
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
    def __init__(self, window=None):
        """
        GPT Wrapper

        :param window: Window instance
        """
        self.window = window
        self.ai_name = None
        self.user_name = None
        self.system_prompt = None
        self.input_tokens = 0
        self.attachments = {}
        self.thread_id = None  # assistant thread id
        self.assistant_id = None  # assistant id
        self.file_ids = []  # file ids

    def init(self):
        pass

    def get_client(self):
        """
        Return OpenAI client

        :return: OpenAI client
        :rtype: OpenAI
        """
        return OpenAI(
            api_key=self.window.config.get('api_key'),
            organization=self.window.config.get('organization_key'),
        )

    def completion(self, prompt, max_tokens, stream_mode=False):
        """
        Call OpenAI API for completion

        :param prompt: prompt (user message)
        :param max_tokens: max output tokens
        :param stream_mode: stream mode
        :return: response or stream chunks
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
            model=self.window.config.get('model'),
            max_tokens=int(max_tokens),
            temperature=self.window.config.get('temperature'),
            top_p=self.window.config.get('top_p'),
            frequency_penalty=self.window.config.get('frequency_penalty'),
            presence_penalty=self.window.config.get('presence_penalty'),
            stop=stop,
            stream=stream_mode,
        )
        return response

    def chat(self, prompt, max_tokens, stream_mode=False):
        """
        Call OpenAI API for chat

        :param prompt: prompt (user message)
        :param max_tokens: max output tokens
        :param stream_mode: stream mode
        :return: response or stream chunks
        """
        client = self.get_client()

        # build chat messages
        messages = self.build_chat_messages(prompt)
        response = client.chat.completions.create(
            messages=messages,
            model=self.window.config.get('model'),
            max_tokens=int(max_tokens),
            temperature=self.window.config.get('temperature'),
            top_p=self.window.config.get('top_p'),
            frequency_penalty=self.window.config.get('frequency_penalty'),
            presence_penalty=self.window.config.get('presence_penalty'),
            stop=None,
            stream=stream_mode,
        )
        return response

    def vision(self, prompt, max_tokens, stream_mode=False):
        """
        Call OpenAI API for chat with vision

        :param prompt: prompt (user message)
        :param max_tokens: max output tokens
        :param stream_mode: stream mode
        :return: response or stream chunks
        """
        client = self.get_client()

        # build chat messages
        messages = self.build_chat_messages(prompt)
        response = client.chat.completions.create(
            messages=messages,
            model=self.window.config.get('model'),
            max_tokens=int(max_tokens),
            stream=stream_mode,
        )
        return response

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def build_chat_messages(self, prompt, system_prompt=None):
        """
        Build chat messages dict

        :param prompt: prompt
        :param system_prompt: system prompt (optional)
        :return: messages dictionary
        """
        messages = []

        # tokens config
        model = self.window.config.get('model')
        mode = self.window.config.get('mode')
        used_tokens = self.count_used_tokens(prompt)
        max_tokens = self.window.config.get('max_total_tokens')
        model_ctx = self.window.config.get_model_ctx(model)
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
        if self.window.config.get('use_context'):
            items = self.window.context.get_prompt_items(model, used_tokens, max_tokens)
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
        Build vision content

        :param text: text prompt
        :param append_attachments: append attachments
        :return: Dictionary with content
        :rtype: dict
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
        Build completion string

        :param prompt: prompt (current)
        :return: message string (parsed with context)
        :rtype: str
        """
        message = ""

        # tokens config
        model = self.window.config.get('model')
        used_tokens = self.count_used_tokens(prompt)
        max_tokens = self.window.config.get('max_total_tokens')
        model_ctx = self.window.config.get_model_ctx(model)
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        # input tokens: reset
        self.reset_tokens()

        if self.system_prompt is not None and self.system_prompt != "":
            message += self.system_prompt

        if self.window.config.get('use_context'):
            items = self.window.context.get_prompt_items(model, used_tokens, max_tokens)
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
        Count used tokens

        :param input_text: input text
        :return: used tokens
        :rtype: int
        """
        model = self.window.config.get('model')
        mode = self.window.config.get('mode')
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
        tokens += self.window.config.get('context_threshold')  # context threshold (reserved for next output)
        tokens += num_tokens_extra(model)  # extra tokens (required for output)
        return tokens

    def quick_call(self, prompt, sys_prompt, append_context=False, max_tokens=500, model="gpt-3.5-turbo-1106", temp=0.0):
        """
        Call OpenAI API with custom prompt

        :param prompt: user input (prompt)
        :param sys_prompt: system input (prompt)
        :param append_context: append context (memory)
        :param max_tokens: max output tokens
        :param model: model name
        :param temp: temperature
        :return: response text
        :rtype: str
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
        Create thread

        :return: thread ID
        :rtype: str
        """
        client = self.get_client()
        thread = client.beta.threads.create()
        if thread is not None:
            return thread.id

    def assistant_thread_delete(self, id):
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

    def assistant_msg_send(self, id, text):
        """
        Send message to thread

        :param id: thread ID
        :param text: message text
        :return: message
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
        Get messages from thread

        :param thread_id: thread ID
        :return: messages
        :rtype: list
        """
        client = self.get_client()
        thread_messages = client.beta.threads.messages.list(thread_id)
        return thread_messages.data

    def assistant_file_info(self, file_id):
        """
        Get file info

        :param file_id: file ID
        :return: file info
        """
        client = self.get_client()
        return client.files.retrieve(file_id)

    def assistant_file_download(self, file_id, path):
        """
        Download file

        :param file_id: file ID
        :param path: path to save file
        """
        client = self.get_client()
        content = client.files.retrieve_content(file_id)
        with open(path, 'wb',) as f:
            f.write(content.encode())
            f.close()

    def assistant_run_create(self, thread_id, assistant_id, instructions=None):
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
        if self.window.config.get('model') is not None:
            additional_args['model'] = self.window.config.get('model')

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            **additional_args
        )
        if run is not None:
            return run

    def assistant_run_status(self, thread_id, run_id):
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

    def assistant_file_upload(self, id, path, purpose="assistants"):
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

    def assistant_file_delete(self, assistant_id, file_id):
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

    def assistant_file_list(self, assistant_id):
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

    def assistant_create(self, assistant):
        """
        Create assistant

        :param assistant: assistant object
        :return: assistant object
        :rtype: Assistant
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
        Update assistant

        :param assistant: assistant object
        :return: assistant object
        :rtype: Assistant
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
        Delete assistant

        :param id: assistant ID
        :return: assistant ID
        :rtype: str
        """
        client = self.get_client()
        response = client.beta.assistants.delete(id)
        if response is not None:
            return response.id

    def assistant_get_files(self, id, limit=100):
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

    def assistant_import(self, items, order="asc", limit=100):
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

    def assistant_get_tools(self, assistant):
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
                tools.append({"type": "function", "function": {"name": function['name'], "parameters": params, "description": function['desc']}})
        return tools

    def call(self, prompt, ctx=None, stream_mode=False):
        """
        Call OpenAI API

        :param prompt: user input (prompt)
        :param ctx: context item (memory)
        :param stream_mode: stream mode (default: False)
        :return: context item (memory)
        :rtype: ContextItem
        """
        # prepare max tokens
        mode = self.window.config.get('mode')
        model_tokens = self.window.config.get_model_tokens(self.window.config.get('model'))
        max_tokens = self.window.config.get('max_output_tokens')
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
            self.window.context.add(ctx)
            return ctx  # if assistant then return here

        # async mode (stream)
        if stream_mode:
            # store context (memory)
            if ctx is None:
                ctx = ContextItem(self.window.config.get('mode'))
                ctx.set_input(prompt, self.user_name)

            ctx.stream = response
            ctx.set_output("", self.ai_name)
            ctx.input_tokens = self.input_tokens  # from global tokens calculation
            self.window.context.add(ctx)
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
            ctx = ContextItem(self.window.config.get('mode'))
            ctx.set_input(prompt, self.user_name)

        ctx.set_output(output, self.ai_name)
        ctx.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)
        self.window.context.add(ctx)

        return ctx

    def stop(self):
        """Stop OpenAI API"""
        pass

    def prepare_ctx_name(self, ctx):
        """
        Summarize conversation begin

        :param ctx: context item (memory)
        :return: response text
        :rtype: str
        """
        # default values
        model = 'gpt-3.5-turbo-1106'
        sys_prompt = "You are an expert in conversation summarization"
        text = "Summarize topic of this conversation in one sentence. Use best keywords to describe it. " \
               "Summary must be in the same language as the conversation and it will be used for conversation title " \
               "so it must be EXTREMELY SHORT and concise - use maximum 5 words: \n\n"
        text += "User: " + str(ctx.input) + "\nAI Assistant: " + str(ctx.output)

        # custom values
        if self.window.config.get('ctx.auto_summary.system') is not None and self.window.config.get('ctx.auto_summary.system') != "":
            sys_prompt = self.window.config.get('ctx.auto_summary.system')
        if self.window.config.get('ctx.auto_summary.prompt') is not None and self.window.config.get('ctx.auto_summary.prompt') != "":
            text = self.window.config.get('ctx.auto_summary.prompt').replace("{input}", str(ctx.input)).replace("{output}", str(ctx.output))
        if self.window.config.get('ctx.auto_summary.model') is not None and self.window.config.get('ctx.auto_summary.model') != "":
            model = self.window.config.get('ctx.auto_summary.model')

        # call OpenAI API
        response = self.quick_call(text, sys_prompt, False, 500, model)
        if response is not None:
            return response

    def clear(self):
        """Clear context (memory)"""
        self.window.context.clear()

    def extract_urls(self, text):
        """
        Extract urls from text

        :param text: text
        :return: list of urls
        :rtype: list
        """
        return re.findall(r'(https?://\S+)', text)

    def is_image(self, path):
        """
        Check if url is image

        :param path: url
        :return: true if image
        :rtype: bool
        """
        return path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))

    def encode_image(self, image_path):
        """
        Encode image to base64
        
        :param image_path: path to image
        :return: base64 encoded image
        :rtype: str
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
