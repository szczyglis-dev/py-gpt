#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:55:00                  #
# ================================================== #

import os
from typing import Optional, List, Dict

import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM

from pygpt_net.core.types import (
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX, 
    MODE_CHAT,
)
from pygpt_net.item.model import ModelItem
from pygpt_net.utils import parse_args


class BaseLLM:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.name = ""
        self.type = []  # langchain, llama_index, embeddings
        self.description = ""

    def init(
            self,
            window,
            model: ModelItem,
            mode: str,
            sub_mode: str = None
    ):
        """
        Initialize provider

        :param window: window instance
        :param model: model instance
        :param mode: mode (langchain, llama_index)
        :param sub_mode: sub mode (chat, completion)
        """
        options = {}
        if mode == MODE_LANGCHAIN:
            pass
            # options = model.langchain
        elif mode == MODE_LLAMA_INDEX:
            options = model.llama_index
        if 'env' in options:
            for item in options['env']:
                if item['name'] is None or item['name'] == "":
                    continue
                try:
                    os.environ[item['name']] = str(item['value'].format(**window.core.config.all()))
                except Exception as e:
                    pass

    def init_embeddings(
            self,
            window,
            env: Optional[List[Dict]] = None
    ):
        """
        Initialize embeddings provider

        :param window: window instance
        :param env: ENV configuration list
        """
        if env is not None and len(env) > 0:
            for item in env:
                if item['name'] is None or item['name'] == "":
                    continue
                try:
                    os.environ[item['name']] = str(item['value'].format(**window.core.config.all()))
                except Exception as e:
                    pass

    def parse_args(
            self,
            options: dict,
            window = None
    ) -> dict:
        """
        Parse extra args

        :param options: LLM options dict (langchain, llama_index)
        :param window: window instance
        :return: parsed arguments dict
        """
        args = {}
        if 'args' in options:
            if options['args'] is not None:
                args = parse_args(options['args'])
                if window:
                    for key in args:
                        if isinstance(args[key], str):
                            try:
                                args[key] = args[key].format(**window.core.config.all())
                            except Exception as e:
                                pass
        return args

    def get_env_override(
            self,
            window,
            env: Optional[List[Dict]],
            names: List[str],
    ) -> Optional[str]:
        """Return a declared Advanced ENV override without using stale process ENV."""
        wanted = set(names)
        for item in env or []:
            if not isinstance(item, dict) or item.get("name") not in wanted:
                continue
            value = item.get("value")
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    value = value.format(**window.core.config.all())
                except Exception:
                    pass
            value = str(value)
            return value if value else None
        return None

    def get_openai_compatible_env_names(self) -> tuple[List[str], List[str]]:
        """Return common API key/base ENV names accepted by a provider."""
        key_names = ["OPENAI_API_KEY"]
        base_names = ["OPENAI_API_BASE"]
        provider_names = {
            "deepseek_api": (["DEEPSEEK_API_KEY"], ["DEEPSEEK_API_BASE"]),
            "x_ai": (["XAI_API_KEY"], ["XAI_API_BASE"]),
            "perplexity": (["PERPLEXITY_API_KEY", "PPLX_API_KEY"], ["PERPLEXITY_API_BASE"]),
            "open_router": (["OPENROUTER_API_KEY"], ["OPENROUTER_API_BASE"]),
            "huggingface_router": (["HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"], ["HF_INFERENCE_ENDPOINT"]),
            "forge": (["FORGE_API_KEY"], ["FORGE_API_BASE"]),
            "edenai": (["EDENAI_API_KEY"], ["EDENAI_API_BASE"]),
        }
        extra_keys, extra_bases = provider_names.get(self.id, ([], []))
        return [*extra_keys, *key_names], [*extra_bases, *base_names]

    def prepare_openai_compatible_args(
            self,
            window,
            model: ModelItem,
            options: Optional[dict] = None,
    ) -> dict:
        """Resolve LlamaIndex args with normal PyGPT provider defaults.

        ``model.llama_index.args`` remains an override layer. Missing/empty
        model, API key and API base are inherited from the same global/provider
        configuration used by normal Chat, including runtime custom providers
        and per-model custom endpoint/key overrides.
        """
        if options is None:
            options = model.llama_index
        args = self.parse_args(options or {}, window)

        if not args.get("model"):
            args["model"] = model.id

        client_args = window.core.models.prepare_client_args(MODE_CHAT, model)
        key_env_names, base_env_names = self.get_openai_compatible_env_names()
        env = (model.llama_index or {}).get("env", [])
        if not args.get("api_key"):
            api_key = self.get_env_override(window, env, key_env_names)
            if not api_key:
                api_key = client_args.get("api_key")
            if api_key:
                args["api_key"] = api_key
        if not args.get("api_base"):
            api_base = self.get_env_override(window, env, base_env_names)
            if not api_base:
                api_base = client_args.get("base_url")
            if api_base:
                args["api_base"] = api_base
        return args

    def prepare_openai_compatible_embedding_args(
            self,
            window,
            config: Optional[List[Dict]] = None,
    ) -> dict:
        """Resolve embedding overrides against provider-global API settings."""
        args = self.parse_args({"args": config or []}, window)

        model = ModelItem()
        model.provider = self.id
        client_args = window.core.models.prepare_client_args(MODE_CHAT, model)
        key_env_names, base_env_names = self.get_openai_compatible_env_names()
        env = window.core.config.get("llama.idx.embeddings.env", []) or []

        if not args.get("api_key"):
            api_key = self.get_env_override(window, env, key_env_names)
            if not api_key:
                api_key = client_args.get("api_key")
            if api_key:
                args["api_key"] = api_key
        if not args.get("api_base"):
            api_base = self.get_env_override(window, env, base_env_names)
            if not api_base:
                api_base = client_args.get("base_url")
            if api_base:
                args["api_base"] = api_base
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")
        return args

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> any:
        """
        Return LLM provider instance for completion in langchain mode

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> any:
        """
        Return LLM provider instance for chat in langchain mode

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex LLM instance for plain-text completion.

        Providers may override this when their regular LlamaIndex wrapper maps
        ``complete()`` back to a chat endpoint. The default implementation uses
        the same provider object as Chat with Files and the caller invokes its
        ``complete`` / ``stream_complete`` methods directly.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LlamaIndex LLM provider instance
        """
        return self.llama(window=window, model=model, stream=stream)

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama index query and chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def llama_chat_with_files(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
    ) -> LlamaBaseLLM:
        """Return a LlamaIndex LLM with the Chat with Files Computer Use bridge.

        Kept as the provider override point for backward compatibility. New
        callers should use :meth:`llama_with_computer_runtime`.
        """
        return self.llama(window=window, model=model, stream=stream)

    def llama_with_computer_runtime(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
    ) -> LlamaBaseLLM:
        """Return a LlamaIndex LLM bound to the shared Computer Use runtime.

        Existing provider implementations already expose their native Computer
        Use continuation adapters through ``llama_chat_with_files``. Route the
        generic hook through that implementation so Chat with Files and legacy
        agents share one provider-specific code path.
        """
        return self.llama_chat_with_files(
            window=window,
            model=model,
            stream=stream,
            computer_runtime=computer_runtime,
        )

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex LLM instance for Agents v2.

        Providers with native/server-side remote tools can override this method
        and attach them directly to the LLM request. The default implementation
        simply reuses the regular LlamaIndex provider.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :param allow_remote_tools: allow provider-native remote tools
        :return: provider instance
        """
        return self.llama(window=window, model=model, stream=stream)

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
        :return: provider instance
        """
        pass

    def get_openai_agent_provider(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return agent provider instance for OpenAI agents

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: agent provider instance
        """
        pass

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider.

        The default implementation queries the OpenAI-compatible ``/models``
        endpoint and is safe to call when the endpoint is unreachable: it logs
        the failure and returns an empty list instead of raising. Providers
        with a non-OpenAI schema must override this method.

        :param window: window instance
        :return: list of models
        """
        items: List[Dict] = []
        try:
            client = self.get_client(window)
            models_list = client.models.list()
            if models_list.data:
                items.extend(
                    {"id": item.id, "name": item.id} for item in models_list.data
                )
        except Exception as e:
            window.core.debug.log(e)
        return items

    def get_client(self, window):
        """
        Return client for current provider

        :param window: Window instance
        :return: Client instance for the provider
        """
        model = ModelItem()
        model.provider = self.id
        return window.core.api.openai.get_client(
            mode=MODE_CHAT,
            model=model,
        )

    def inject_llamaindex_http_clients(self, args: dict, cfg) -> dict:
        import httpx
        proxy = (cfg.get("api_proxy") or "").strip()  # e.g. "http://user:pass@host:3128"
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
        common_kwargs = dict(timeout=60.0, follow_redirects=True)
        if proxy:
            common_kwargs["proxy"] = proxy  # httpx>=0.28

        args["http_client"] = httpx.Client(**common_kwargs)
        args["async_http_client"] = httpx.AsyncClient(**common_kwargs)
        return args

    def get_embeddings_timeout(self, cfg) -> float:
        """Return the global embeddings request timeout in seconds."""
        value = cfg.get("llama.idx.embeddings.timeout")
        try:
            timeout = float(value)
        except (TypeError, ValueError):
            timeout = 60.0
        return timeout if timeout > 0 else 60.0

    def inject_llamaindex_embedding_http_clients(self, args: dict, cfg) -> dict:
        """Inject HTTP clients using the global embeddings request timeout."""
        import httpx
        proxy = (cfg.get("api_proxy") or "").strip()
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
        common_kwargs = dict(
            timeout=self.get_embeddings_timeout(cfg),
            follow_redirects=True,
        )
        if proxy:
            common_kwargs["proxy"] = proxy  # httpx>=0.28

        if "http_client" not in args:
            args["http_client"] = httpx.Client(**common_kwargs)
        if "async_http_client" not in args:
            args["async_http_client"] = httpx.AsyncClient(**common_kwargs)
        return args
