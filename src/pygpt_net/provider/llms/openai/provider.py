#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 11:45:00                  #
# ================================================== #

from __future__ import annotations

from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
    from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM

# from langchain_openai import OpenAI
# from langchain_openai import ChatOpenAI


from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODE_CHAT,
    MODE_AGENT_V2,
    MODE_COMPUTER,
    MODE_EMBEDDINGS,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.core.model.compat import is_openai_reasoning_model_id


class OpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OpenAILLM, self).__init__(*args, **kwargs)
        self.id = "openai"
        self.name = "OpenAI"
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        return {
            "settings": {
                "api_key": {
                    "type": "str",
                    "default": "",
                    "secret": True,
                    "urls": {"API Keys": "https://platform.openai.com/account/api-keys"},
                },
                "api_base": {
                    "type": "str",
                    "default": "https://api.openai.com/v1",
                },
                "extra": {
                    "organization": {
                        "type": "str",
                        "default": "",
                        "label": "settings.organization_key",
                        "desc": "settings.organization_key.desc",
                        "use_locale": True,
                        "secret": True,
                    },
                    "responses_api": {
                        "type": "bool",
                        "default": True,
                        "label": "settings.api_use_responses",
                        "desc": "settings.api_use_responses.desc",
                        "use_locale": True,
                        "advanced": True,
                    },
                    "responses_api_llama": {
                        "type": "bool",
                        "default": True,
                        "label": "settings.api_use_responses_llama",
                        "desc": "settings.api_use_responses_llama.desc",
                        "use_locale": True,
                        "advanced": True,
                    },
                },
            },
            "remote_tools": {
                "web_search": {
                    "unsupported_prefixes": ['gpt-3.5-', 'gpt-4-', 'o1', 'o3'],
                    "unsupported_models": ['gpt-4', 'codex-mini-latest'],
                    "type": "bool",
                    "label": "settings.remote_tools.web_search",
                    "default": True,
                    "desc": "settings.remote_tools.web_search.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.web_search",
                    "tool": True,
                    "choice_label": "remote_tool.openai.web_search",
                },
                "image": {
                    "type": "bool",
                    "label": "settings.remote_tools.image",
                    "default": False,
                    "desc": "settings.remote_tools.image.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.image",
                    "tool": True,
                    "choice_label": "remote_tool.openai.image",
                },
                "code_interpreter": {
                    "type": "bool",
                    "label": "settings.remote_tools.code_interpreter",
                    "default": False,
                    "desc": "settings.remote_tools.code_interpreter.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.code_interpreter",
                    "tool": True,
                    "choice_label": "remote_tool.openai.code_interpreter",
                },
                "mcp": {
                    "type": "bool",
                    "label": "settings.remote_tools.mcp",
                    "default": False,
                    "desc": "settings.remote_tools.mcp.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.mcp",
                    "tool": True,
                    "choice_label": "remote_tool.openai.mcp",
                },
                "mcp.args": {
                    "type": "textarea",
                    "label": "settings.remote_tools.mcp.args",
                    "urls": {
                        "OpenAI Docs": "https://platform.openai.com/docs/guides/tools-remote-mcp",
                    },
                    "default": "{\n    \"type\": \"mcp\",\n    \"server_label\": \"deepwiki\",\n    \"server_url\": \"https://mcp.deepwiki.com/mcp\",\n    \"require_approval\": \"never\",\n    \"allowed_tools\": [\"ask_question\"]\n}",
                    "desc": "settings.remote_tools.mcp.args.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.mcp.args",
                },
                "file_search": {
                    "type": "bool",
                    "label": "settings.remote_tools.file_search",
                    "default": False,
                    "desc": "settings.remote_tools.file_search.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.file_search",
                    "tool": True,
                    "choice_label": "remote_tool.openai.file_search",
                },
                "file_search.args": {
                    "type": "text",
                    "label": "settings.remote_tools.file_search.args",
                    "urls": {
                        "OpenAI Docs": "https://platform.openai.com/docs/guides/tools-file-search",
                    },
                    "default": "",
                    "desc": "settings.remote_tools.file_search.args.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.file_search.args",
                },
                "computer_use": {
                    "type": "bool",
                    "label": "settings.remote_tools.computer_use",
                    "urls": {
                        "OpenAI Docs": "https://developers.openai.com/api/docs/guides/tools-computer-use",
                    },
                    "default": False,
                    "desc": "settings.remote_tools.computer_use.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.computer_use",
                    "tool": True,
                    "choice_label": "remote_tool.openai.computer_use",
                },
            },
        }

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for completion

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance

        args = self.parse_args(model.langchain)
        if "model" not in args:
            args["model"] = model.id
        return OpenAI(**args)
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance

        args = self.parse_args(model.langchain)
        return ChatOpenAI(**args)
        """
        pass

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """Return an OpenAI LlamaIndex adapter for PyGPT Completion mode.

        LlamaIndex exposes ``complete`` / ``stream_complete`` for both legacy
        completion models and chat models. ``OpenAILike`` is used deliberately
        here so newly released OpenAI model IDs do not depend on LlamaIndex's
        hard-coded OpenAI model registry.
        """
        from llama_index.llms.openai_like import OpenAILike

        class OpenAICompletion(OpenAILike):
            """Normalize Chat Completions kwargs for OpenAI reasoning models."""

            @staticmethod
            def _is_reasoning_model(model_id: str) -> bool:
                return is_openai_reasoning_model_id(model_id)

            def _get_model_kwargs(self, **kwargs):
                params = super()._get_model_kwargs(**kwargs)
                if not self._is_reasoning_model(self.model):
                    return params

                # Reasoning models do not share the classic sampling surface.
                # Keep Completion mode compatible with current Chat Completions
                # models and avoid parameters rejected by newer GPT/o-series IDs.
                for key in (
                        "temperature",
                        "top_p",
                        "presence_penalty",
                        "frequency_penalty",
                        "stop",
                ):
                    params.pop(key, None)

                if "max_tokens" in params:
                    params.setdefault("max_completion_tokens", params["max_tokens"])
                    params.pop("max_tokens", None)
                return params

        args = self.prepare_openai_compatible_args(window, model)
        model_id = str(args.get("model") or model.id or "").strip()
        if model_id.startswith("text-davinci"):
            # Preserve PyGPT's historical compatibility fallback.
            model_id = "gpt-3.5-turbo-instruct"
        if not model_id:
            raise ValueError("Model name is required for OpenAI completion.")
        args["model"] = model_id

        organization = str(self.get_config("organization", "") or "").strip()
        if organization:
            headers = dict(args.get("default_headers") or {})
            headers.setdefault("OpenAI-Organization", organization)
            args["default_headers"] = headers

        if "context_window" not in args:
            ctx_size = int(getattr(model, "ctx", 0) or 0)
            if ctx_size > 0:
                args["context_window"] = ctx_size

        # A model configured for Chat in PyGPT uses /v1/chat/completions even
        # though the UI mode is Completion. OpenAI's legacy instruct model is
        # completion-only and must always use /v1/completions. Force this value
        # instead of using setdefault(), because old/user LlamaIndex overrides or
        # runtime mode normalization may otherwise leave is_chat_model=True.
        if model_id == "gpt-3.5-turbo-instruct":
            args["is_chat_model"] = False
            args["is_function_calling_model"] = False
        else:
            args.setdefault("is_chat_model", model.has_mode(MODE_CHAT))
            args.setdefault("is_function_calling_model", False)

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAICompletion")
        return OpenAICompletion(**args)

    @staticmethod
    def _merge_additional_kwargs(args: dict, **values) -> None:
        """Merge provider request fields forwarded by LlamaIndex."""
        extra = dict(args.get("additional_kwargs") or {})
        extra.update({key: value for key, value in values.items() if value is not None})
        args["additional_kwargs"] = extra

    def _append_chat_reasoning_effort(self, window, model: ModelItem, args: dict) -> None:
        effort = window.core.models.get_reasoning_effort(model)
        if effort:
            self._merge_additional_kwargs(args, reasoning_effort=effort)

    def _append_responses_reasoning_effort(self, window, model: ModelItem, args: dict) -> None:
        effort = window.core.models.get_reasoning_effort(model)
        if effort:
            self._merge_additional_kwargs(args, reasoning={"effort": effort})

    @staticmethod
    def _append_responses_source_include(args: dict, tools: list) -> None:
        """Request the complete hosted Web Search source list when available."""
        web_types = {
            "web_search",
            "web_search_preview",
            "web_search_2025_08_26",
            "web_search_preview_2025_03_11",
        }
        if not any(
                isinstance(tool, dict) and tool.get("type") in web_types
                for tool in tools or []
        ):
            return
        include_value = args.get("include")
        if isinstance(include_value, list):
            include = list(include_value)
        elif include_value:
            include = [include_value]
        else:
            include = []
        source_field = "web_search_call.action.sources"
        if source_field not in include:
            include.append(source_field)
        args["include"] = include

    def _append_responses_remote_tools(
            self,
            window,
            model: ModelItem,
            stream: bool,
            mode: str,
            args: dict,
    ) -> list:
        """Attach provider-native Responses tools and their artifact includes."""
        tools = window.core.api.openai.remote_tools.append_to_tools(
            mode=mode,
            model=model,
            stream=stream,
            is_expert_call=False,
            tools=[],
            preset=None,
        )
        if tools:
            args["built_in_tools"] = tools
            self._append_responses_source_include(args, tools)
        return tools

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.openai import OpenAI as LlamaOpenAI
        from .responses_agent import AgentOpenAIResponses
        args = self.prepare_openai_compatible_args(window, model)
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        mode = window.core.config.get("mode")
        # dont' use Responses in agent modes
        if self.get_config("responses_api_llama", False) and mode == MODE_LLAMA_INDEX:
            self._append_responses_remote_tools(
                window=window,
                model=model,
                stream=stream,
                mode=MODE_LLAMA_INDEX,
                args=args,
            )
            self._append_responses_reasoning_effort(window, model, args)
            # Use the shared PyGPT Responses adapter here too. Besides Computer
            # Use it buffers provider source/citation URLs so Chat with Files can
            # persist them even when LlamaIndex chat/query engines hide raw metadata.
            self.log_llama_create(window, model, args, "AgentOpenAIResponses")
            llm = AgentOpenAIResponses(**args)
            return window.core.context_manager.configure_llm_for_rolling_context(llm)
        else:
            self._append_chat_reasoning_effort(window, model, args)
            self.log_llama_create(window, model, args, "llama_index.llms.openai.OpenAI")
        return LlamaOpenAI(**args)

    def llama_chat_with_files(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
            force_computer_use: bool = False,
    ) -> LlamaBaseLLM:
        """Use the shared provider continuation adapter when Computer Use is active."""
        tools = window.core.api.openai.remote_tools.append_to_tools(
            mode=MODE_COMPUTER if force_computer_use else MODE_LLAMA_INDEX,
            model=model,
            stream=stream,
            is_expert_call=False,
            tools=[],
            preset=None,
        )
        if any(isinstance(tool, dict) and tool.get("type") == "computer" for tool in tools):
            llm = self.llama_agent(
                window=window,
                model=model,
                stream=stream,
                allow_remote_tools=True,
                force_computer_use=force_computer_use,
            )
            binder = getattr(llm, "bind_computer_runtime", None)
            if callable(binder):
                binder(computer_runtime)
            return llm
        return self.llama(window=window, model=model, stream=stream)

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True,
            force_computer_use: bool = False,
    ) -> LlamaBaseLLM:
        """
        Return OpenAI LLM for Agents v2.

        Provider-native remote tools are attached directly to OpenAI Responses,
        exactly through the same PyGPT remote-tools builder used by normal Chat.
        Local FunctionAgent tools are merged by LlamaIndex at request time.
        """
        from .responses_agent import AgentOpenAIResponses

        args = self.prepare_openai_compatible_args(window, model)
        args = self.inject_llamaindex_http_clients(args, window.core.config)

        # Agents v2 always uses OpenAI Responses for the native OpenAI provider.
        # FunctionAgent always exposes local function tools (for example
        # shared_context/delegate_task), even when all provider-native remote tools
        # are disabled. Falling back to Chat Completions in that case breaks newer
        # reasoning models (e.g. GPT-5.6), which reject function tools together
        # with reasoning_effort on /v1/chat/completions. Responses supports both
        # local function calling and provider-native tools on one stable path.
        if allow_remote_tools:
            self._append_responses_remote_tools(
                window=window,
                model=model,
                stream=stream,
                mode=MODE_COMPUTER if force_computer_use else MODE_AGENT_V2,
                args=args,
            )

        self._append_responses_reasoning_effort(window, model, args)
        self.log_llama_create(window, model, args, "AgentOpenAIResponses")
        llm = AgentOpenAIResponses(**args)
        return window.core.context_manager.configure_llm_for_rolling_context(llm)

    def llama_multimodal(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaMultiModalLLM:
        """
        Return multimodal LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        """
        Return provider instance for embeddings

        :param window: window instance
        :param config: config keyword arguments list
        :return: Embedding provider instance
        """
        from llama_index.embeddings.openai import OpenAIEmbedding
        args = self.prepare_openai_compatible_embedding_args(window, config)
        args = self.inject_llamaindex_embedding_http_clients(args, window.core.config)
        return OpenAIEmbedding(**args)
