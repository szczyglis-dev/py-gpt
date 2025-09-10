#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 09:00:00                  #
# ================================================== #

import base64
import json
import time
from typing import Optional, Dict, Any, List, Tuple

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_VISION,
    MODE_AUDIO,
    MODE_RESEARCH,
    MODE_AGENT,
    MODE_AGENT_OPENAI,
    MODE_AGENT_LLAMA,
    MODE_EXPERT,
    MODE_COMPUTER,
    OPENAI_DISABLE_TOOLS,
)
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.preset import PresetItem


class Responses:

    # Responses API modes
    RESPONSES_ALLOWED_MODES = [
        MODE_CHAT,
        MODE_RESEARCH,
        MODE_AGENT,
        MODE_AGENT_LLAMA,
        MODE_AGENT_OPENAI,
        MODE_EXPERT,
        MODE_COMPUTER,
    ]

    def __init__(self, window=None):
        """
        Responses API wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0
        self.audio_prev_id = None
        self.audio_prev_expires_ts = None
        self.prev_response_id = None
        self.prev_internal_response_id = None
        self.instruction = None
        self.mcp_tools = None

    def send(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ):
        """
        Call OpenAI API for chat

        :param context: Bridge context
        :param extra: Extra arguments
        :return: response or stream chunks
        """
        prompt = context.prompt
        stream = context.stream
        max_tokens = int(context.max_tokens or 0)
        system_prompt = context.system_prompt
        mode = context.mode
        model = context.model
        functions = context.external_functions
        attachments = context.attachments
        multimodal_ctx = context.multimodal_ctx
        is_expert_call = context.is_expert_call
        preset = context.preset

        ctx = context.ctx
        if ctx is None:
            ctx = CtxItem()  # create empty context
        user_name = ctx.input_name  # from ctx
        ai_name = ctx.output_name  # from ctx

        client = self.window.core.api.openai.get_client(mode, model)

        # build chat messages
        messages = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            history=context.history,
            attachments=attachments,
            ai_name=ai_name,
            user_name=user_name,
            multimodal_ctx=multimodal_ctx,
            is_expert_call=is_expert_call,  # use separated previous response ID for expert calls
        )

        msg_tokens = self.window.core.tokens.from_messages(
            messages,
            model.id,
        )
        # check if max tokens not exceeded
        if max_tokens > 0 and model.ctx > 0:
            if msg_tokens + int(max_tokens) > model.ctx:
                max_tokens = model.ctx - msg_tokens - 1
                if max_tokens < 0:
                    max_tokens = 0

        # extra API kwargs
        response_kwargs = {}

        # tools / functions
        tools = self.window.core.api.openai.tools.prepare_responses_api(model, functions)

        # extra arguments, o3 only
        if model.extra and "reasoning_effort" in model.extra:
            response_kwargs['reasoning'] = {}
            response_kwargs['reasoning']['effort'] = model.extra["reasoning_effort"]

        # append remote tools
        tools = self.window.core.api.openai.remote_tools.append_to_tools(
            mode=mode,
            model=model,
            stream=stream,
            is_expert_call= is_expert_call,
            tools= tools,
            preset=preset,
        )

        # tool calls are not supported for some models
        if model.id in OPENAI_DISABLE_TOOLS:
            tools = []  # force disable

        if len(tools) > 0:
            response_kwargs['tools'] = tools

        # attach previous response ID if available
        if is_expert_call:
            # expert call, use previous response ID from context
            if self.prev_internal_response_id:
                response_kwargs['previous_response_id'] = self.prev_internal_response_id
                self.prev_internal_response_id = None  # reset after use
        else:
            if self.prev_response_id:
                response_kwargs['previous_response_id'] = self.prev_response_id
                self.prev_response_id = None  # reset after use

        if system_prompt:
            response_kwargs['instructions'] = system_prompt

        # http://platform.openai.com/docs/guides/tools-computer-use
        if mode == MODE_COMPUTER or model.id.startswith("computer-use"):
            response_kwargs['truncation'] = "auto"
            response_kwargs['reasoning'] = {
                "summary": "concise",
            }

        response = client.responses.create(
            input=messages,
            model=model.id,
            stream=stream,
            **response_kwargs,
        )

        # store previous response ID
        if not stream and response:
            ctx.msg_id = response.id

        return response

    def build(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            ai_name: Optional[str] = None,
            user_name: Optional[str] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
            is_expert_call: bool = False,
    ) -> list:
        """
        Build list of chat messages

        :param prompt: user prompt
        :param system_prompt: system prompt
        :param history: history
        :param model: model item
        :param attachments: attachments
        :param ai_name: AI name
        :param user_name: username
        :param multimodal_ctx: Multimodal context
        :param is_expert_call: if True then expert call, use previous response ID from context
        :return: messages list
        """
        messages = []
        if is_expert_call:
            self.prev_internal_response_id = None
        else:
            self.prev_response_id = None

        is_tool_output = False  # reset

        # tokens config
        mode = MODE_CHAT
        tool_call_native_enabled = self.window.core.config.get('func_call.native', False)
        allowed_system = True
        if (model.id is not None
                and model.id in ["o1-mini", "o1-preview"]):
            allowed_system = False

        used_tokens = self.window.core.tokens.from_user(
            prompt,
            system_prompt,
        )  # threshold and extra included
        max_ctx_tokens = self.window.core.config.get('max_total_tokens')  # max context window

        # fit to max model tokens
        if max_ctx_tokens > model.ctx > 0:
            max_ctx_tokens = model.ctx

        # input tokens: reset
        self.reset_tokens()

        # append system prompt
        if allowed_system:
            pass
            '''
            if system_prompt is not None and system_prompt != "":
                messages.append({"role": "developer", "content": system_prompt})
            '''

        # append messages from context (memory)
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                mode,
                used_tokens,
                max_ctx_tokens,
            )

            has_response_id_in_last_item = False
            if items and len(items) > 0:
                last_item = items[-1]
                if last_item and last_item.msg_id:
                    has_response_id_in_last_item = True

            for item in items:
                # input
                if item.final_input is not None and item.final_input != "":
                    if not has_response_id_in_last_item:
                        messages.append({
                            "role": "user",
                            "content": item.final_input,
                        })

                # output
                if item.final_output is not None and item.final_output != "":
                    if not has_response_id_in_last_item:
                        msg = {
                            "role": "assistant",
                            "content": item.final_output,
                        }
                    else:
                        msg = {}
                    # append previous audio ID
                    if MODE_AUDIO in model.mode:
                        if item.audio_id:
                            # at first check expires_at - expired audio throws error in API
                            current_timestamp = time.time()
                            audio_timestamp = int(item.audio_expires_ts) if item.audio_expires_ts else 0
                            if audio_timestamp and audio_timestamp > current_timestamp:
                                msg["audio"] = {
                                    "id": item.audio_id
                                }
                        elif self.audio_prev_id:
                            current_timestamp = time.time()
                            audio_timestamp = int(self.audio_prev_expires_ts) if self.audio_prev_expires_ts else 0
                            if audio_timestamp and audio_timestamp > current_timestamp:
                                msg["audio"] = {
                                    "id": self.audio_prev_id
                                }

                    if msg:
                        messages.append(msg)

                    # ---- tool output ----
                    is_tool_output = False  # reset tool output flag
                    is_last_item = item == items[-1] if items else False

                    # MCP approval request
                    if is_last_item and tool_call_native_enabled and item.extra and isinstance(item.extra, dict):
                        if "mcp_approval_request" in item.extra and isinstance(item.extra["mcp_approval_request"], dict):
                            mcp_approval_request = item.extra["mcp_approval_request"]
                            if "id" in mcp_approval_request:
                                msg = {
                                    "type": "mcp_approval_response",
                                    "approval_request_id": mcp_approval_request["id"],
                                    "approve": True
                                }
                                messages.append(msg)

                    # tool calls
                    if is_last_item and tool_call_native_enabled and item.extra and isinstance(item.extra, dict):
                        if "tool_calls" in item.extra and isinstance(item.extra["tool_calls"], list):
                            for tool_call in item.extra["tool_calls"]:
                                output_type = "function_call_output"
                                if "type" in tool_call and tool_call["type"] == "function":
                                    output_type = "function_call_output"
                                elif "type" in tool_call and tool_call["type"] == "computer_call":
                                    output_type = "computer_call"

                                if "function" in tool_call:
                                    if "call_id" not in tool_call or "name" not in tool_call["function"]:
                                        continue

                                    if output_type == "function_call_output":
                                        if tool_call["call_id"] and tool_call["function"]["name"]:
                                            if "tool_output" in item.extra and isinstance(item.extra["tool_output"], list):
                                                for tool_output in item.extra["tool_output"]:
                                                    if ("cmd" in tool_output
                                                            and tool_output["cmd"] == tool_call["function"]["name"]):
                                                        msg = {
                                                            "type": "function_call_output",
                                                            "call_id": tool_call["call_id"],
                                                            "output": str(tool_output),
                                                        }
                                                        is_tool_output = True
                                                        messages.append(msg)
                                                        break
                                                    elif "result" in tool_output:
                                                        # if result is present, append it as function call output
                                                        msg = {
                                                            "type": "function_call_output",
                                                            "call_id": tool_call["call_id"],
                                                            "output": str(tool_output["result"]),
                                                        }
                                                        is_tool_output = True
                                                        messages.append(msg)
                                                        break

                                    # computer call output
                                    elif output_type == "computer_call":
                                        base64img = self.window.core.api.openai.vision.get_attachment(attachments)
                                        if base64img and "call_id" in tool_call:
                                            if tool_call["call_id"]:
                                                # tool output
                                                msg = {
                                                    "call_id": tool_call["call_id"],
                                                    "type": "computer_call_output",
                                                    "output": {
                                                        "type": "input_image",
                                                        "image_url": f"data:image/png;base64,{base64img}"
                                                    },
                                                }
                                                # safety checks
                                                if "pending_safety_checks" in item.extra and isinstance(
                                                        item.extra["pending_safety_checks"], list):
                                                    safety_checks = []
                                                    for check in item.extra["pending_safety_checks"]:
                                                        safety_checks.append({
                                                            "id": check["id"],
                                                            "code": check["code"],
                                                            "message": check["message"],
                                                        })
                                                    if safety_checks:
                                                        msg["acknowledged_safety_checks"] = safety_checks
                                                is_tool_output = True
                                                messages = [msg]  # replace messages with tool output
                                                break

                    # --- previous message ID ---
                    if (item.msg_id and is_last_item
                            and ((item.cmds is None or len(item.cmds) == 0) or is_tool_output)):  # if no cmds before or tool output
                        if is_expert_call:
                            self.prev_internal_response_id = item.msg_id
                        else:
                            self.prev_response_id = item.msg_id  # previous response ID to use in current input

        # use vision and audio if available in current model
        if not is_tool_output:  # append current prompt only if not tool output
            content = str(prompt)
            if (model.is_image_input()
                    and mode != MODE_COMPUTER
                    and not model.id.startswith("computer-use")):
                content = self.window.core.api.openai.vision.build_content(
                    content=content,
                    attachments=attachments,
                    responses_api=True,
                )
            if model.is_audio_input():
                content = self.window.core.api.openai.audio.build_content(
                    content=content,
                    multimodal_ctx=multimodal_ctx,
                )

            # append current prompt
            messages.append({
                "role": "user",
                "content": content,
            })

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(
            messages,
            model.id,
        )

        return messages

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Get input tokens counter

        :return: input tokens
        """
        return self.input_tokens

    def unpack_response(self, mode: str, response, ctx: CtxItem):
        """
        Unpack response from OpenAI API and set context

        :param mode: str - mode of the response (chat, vision, audio)
        :param response: OpenAI API response object
        :param ctx: CtxItem - context item to set the response data
        """
        output = ""
        force_func_call = False  # force function call flag

        if mode in [
            MODE_CHAT,
            # MODE_VISION,
            MODE_RESEARCH,
            MODE_COMPUTER,
        ]:
            if response.output_text:
                output = response.output_text
            if response.output:
                ctx.tool_calls = self.window.core.command.unpack_tool_calls_responses(
                    response.output,
                )

        ctx.output = output.strip() if output else ""
        ctx.msg_id = response.id
        ctx.set_tokens(
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        files = []
        tool_calls = []

        # image generation
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        if image_data:
            img_path = self.window.core.image.gen_unique_path(ctx)
            image_base64 = image_data[0]
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(image_base64))
            if not isinstance(ctx.images, list):
                ctx.images = []
            ctx.images += [img_path]

        for output in response.output:
            # code interpreter call
            if output.type == "code_interpreter_call":
                code_response = ("\n\n**Code interpreter**\n```python\n"
                                 + output.code
                                 + "\n\n```\n-----------\n"
                                 + response.output_text.strip())
                ctx.output = code_response
            elif output.type == "message":
                if output.content:
                    for content in output.content:
                        if content.annotations:
                            for annotation in content.annotations:
                                # url citation
                                if annotation.type == "url_citation":
                                    if ctx.urls is None:
                                        ctx.urls = []
                                    ctx.urls.append(annotation.url)
                                # container file citation
                                elif annotation.type == "container_file_citation":
                                    container_id = annotation.container_id
                                    file_id = annotation.file_id
                                    files.append({
                                        "container_id": container_id,
                                        "file_id": file_id,
                                    })

            # computer use
            elif output.type == "computer_call":
                id = output.id
                call_id = output.call_id
                action = output.action
                tool_calls, is_call = self.window.core.api.openai.computer.handle_action(
                    id=id,
                    call_id=call_id,
                    action=action,
                    tool_calls=tool_calls,
                )
                if output.pending_safety_checks:
                    ctx.extra["pending_safety_checks"] = []
                    for item in output.pending_safety_checks:
                        check = {
                            "id": item.id,
                            "code": item.code,
                            "message": item.message,
                        }
                        ctx.extra["pending_safety_checks"].append(check)
                if is_call:
                    force_func_call = True  # force function call for computer use

            elif output.type == "reasoning":
                if ctx.output == "":
                    for summary in output.summary:
                        if summary.type == "summary_text":
                            ctx.output += summary.text + "\n"

            # MCP: list tools
            elif output.type == "mcp_list_tools":
                tools = output.tools
                self.mcp_tools = tools  # store MCP tools for later use
                ctx.meta.extra = {
                    "mcp_tools": tools,
                }
                self.window.core.ctx.save(ctx.meta.id)

            # MCP: tool call
            elif output.type == "mcp_call":
                call = {
                    "id": output.id,
                    "type": "mcp_call",
                    "approval_request_id": output.approval_request_id,
                    "arguments": output.arguments,
                    "error": output.error,
                    "name": output.name,
                    "output": output.output,
                    "server_label": output.server_label,
                }
                ctx.extra["mcp_call"] = call

            # MCP: approval request
            elif output.type == "mcp_approval_request":
                call = {
                    "id": output.id,
                    "type": "mcp_call",
                    "arguments": output.arguments,
                    "name": output.name,
                    "server_label": output.server_label,
                }
                ctx.extra["mcp_approval_request"] = call

        # computer use tool calls (other functions are handled before)
        if tool_calls:
            ctx.force_call = force_func_call
            self.window.core.debug.info("[chat] Tool calls found, unpacking...")
            self.window.core.command.unpack_tool_calls_chunks(ctx, tool_calls)

        # if files from container are found, download them and append to ctx
        if files:
            self.window.core.debug.info("[chat] Container files found, downloading...")
            try:
                self.window.core.api.openai.container.download_files(ctx, files)
            except Exception as e:
                self.window.core.debug.error(f"[chat] Error downloading container files: {e}")


    def unpack_agent_response(self, result, ctx: CtxItem) -> Tuple[str, str]:
        """
        Unpack agent response and set context

        :param result: Agent response result
        :param ctx: CtxItem - context item to set the response data
        :return: Final output string, response ID
        """
        files = []
        final_output = result.final_output
        response_id = result.last_response_id

        for item in result.new_items:
            if (
                    item.type == "tool_call_item"
                    and item.raw_item.type == "image_generation_call"
                    and (img_result := item.raw_item.result)
            ):
                img_path = self.window.core.image.gen_unique_path(ctx)
                with open(img_path, "wb") as f:
                    f.write(base64.b64decode(img_result))
                if not isinstance(ctx.images, list):
                    ctx.images = []
                ctx.images += [img_path]
            elif (
                    item.type == "tool_call_item"
                    and item.raw_item.type == "code_interpreter_call"
            ):
                code_response = ("\n\n**Code interpreter**\n```python\n"
                                 + item.raw_item.code
                                 + "\n\n```\n-----------\n"
                                 + final_output.strip())
                final_output = code_response
            elif (
                    item.type == "message_output_item"
                    and item.raw_item.type == "message"
                    and item.raw_item.content
            ):
                for content in item.raw_item.content:
                    if content.annotations:
                        for annotation in content.annotations:
                            # url citation
                            if annotation.type == "url_citation":
                                if ctx.urls is None:
                                    ctx.urls = []
                                ctx.urls.append(annotation.url)
                            # container file citation
                            elif annotation.type == "container_file_citation":
                                container_id = annotation.container_id
                                file_id = annotation.file_id
                                files.append({
                                    "container_id": container_id,
                                    "file_id": file_id,
                                })

        # if files from container are found, download them and append to ctx
        if files:
            self.window.core.debug.info("[chat] Container files found, downloading...")
            try:
                self.window.core.api.openai.container.download_files(ctx, files)
            except Exception as e:
                self.window.core.debug.error(f"[chat] Error downloading container files: {e}")

        return final_output, response_id

    def is_enabled(
            self,
            model: ModelItem,
            mode: str,
            parent_mode: str = None,
            is_expert_call: bool = False,
            preset: Optional[PresetItem] = None,
    ) -> bool:
        """
        Check if responses API is allowed for the given model and mode

        :param model:
        :param mode:
        :param parent_mode:
        :param is_expert_call:
        :param preset: PresetItem, used for expert calls
        :return: True if responses API is allowed, False otherwise
        """
        if mode == MODE_COMPUTER:
            return True  # required, even if agent plugin active

        allowed = False  # default is not to use responses API
        if model is not None:
            if model.is_gpt():
                if model.id.startswith("computer-use"):
                    return True

                # check mode
                if (mode in self.RESPONSES_ALLOWED_MODES
                        and parent_mode in self.RESPONSES_ALLOWED_MODES
                        and self.window.core.config.get('api_use_responses', False)):
                    allowed = True  # use responses API for chat mode, only OpenAI models

                    # agents
                    if self.window.controller.agent.legacy.enabled():
                        if not self.window.core.config.get('agent.api_use_responses', False):
                            allowed = False

                    # experts
                    if self.window.controller.agent.experts.enabled():
                        if not self.window.core.config.get('experts.api_use_responses', False):
                            allowed = False

                    # expert instance call
                    if is_expert_call:
                        if self.window.core.config.get('experts.internal.api_use_responses', False):
                            allowed = True
                        else:
                            allowed = False
                            if preset:
                                # check if any remote tools enabled
                                if len(preset.remote_tools) > 0:
                                    allowed = True  # force enable
        return allowed

