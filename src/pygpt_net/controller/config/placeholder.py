#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.26 19:00:00                  #
# ================================================== #

from typing import Dict, Any, List

from pygpt_net.core.types import (
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    AGENT_TYPE_OPENAI,
    AGENT_TYPE_LLAMA,
)
from pygpt_net.utils import trans


class Placeholder:
    def __init__(self, window=None):
        """
        Configuration placeholder options controller

        :param window: Window instance
        """
        self.window = window
        self._apply_handlers = {
            "presets": lambda p: self.get_presets(p),
            "modes": lambda p: self.get_modes(p),
            "models": lambda p: self.get_models(p),
            "languages": lambda p: self.get_languages(),
            "multimodal": lambda p: self.get_multimodal(p),
            "langchain_providers": lambda p: self.get_langchain_providers(),
            "llama_index_providers": lambda p: self.get_llama_index_providers(),
            "llm_providers": lambda p: self.get_llm_providers(),
            "embeddings_providers": lambda p: self.get_embeddings_providers(),
            "llama_index_loaders": lambda p: self.get_llama_index_loaders(),
            "llama_index_loaders_file": lambda p: self.get_llama_index_loaders(type="file"),
            "llama_index_loaders_web": lambda p: self.get_llama_index_loaders(type="web"),
            "llama_index_chat_modes": lambda p: self.get_llama_index_chat_modes(),
            "vector_storage": lambda p: self.get_vector_storage(),
            "var_types": lambda p: self.get_var_types(),
            "agent_modes": lambda p: self.get_agent_modes(),
            "agent_provider": lambda p: self.get_agent_providers(),
            "agent_provider_llama": lambda p: self.get_agent_providers_llama(),
            "agent_provider_openai": lambda p: self.get_agent_providers_openai(),
            "remote_tools_openai": lambda p: self.get_remote_tools_openai(),
            "syntax_styles": lambda p: self.get_syntax_styles(),
            "styles": lambda p: self.get_styles(),
            "idx": lambda p: self.get_idx(p),
            "keys": lambda p: self.get_keys(),
            "keys_modifiers": lambda p: self.get_modifiers(),
            "access_actions": lambda p: self.get_access_actions(),
            "speech_synthesis_actions": lambda p: self.get_speech_synthesis_actions(),
            "voice_control_actions": lambda p: self.get_voice_control_actions(),
            "audio_input_devices": lambda p: self.get_audio_input_devices(),
            "audio_output_devices": lambda p: self.get_audio_output_devices(),
            "audio_input_backend": lambda p: self.get_audio_input_backend(),
            "audio_output_backend": lambda p: self.get_audio_output_backend(),
            "audio_tts_whisper_voices": lambda p: self.get_audio_tts_whisper_voices(),
        }

    def _apply_combo_if_needed(self, item: Any):
        if isinstance(item, dict) and item.get("type") == "combo":
            use = item.get("use")
            if use is not None:
                params = item.get("use_params")
                if not isinstance(params, dict):
                    params = {}
                item["keys"] = self.apply_by_id(use, params)

    def _apply_suboptions(self, mapping: Dict[str, Any]):
        for item in mapping.values():
            self._apply_combo_if_needed(item)

    def apply(self, option: Dict[str, Any]):
        """
        Apply placeholders to option

        :param option: Option dict
        """
        t = option["type"]
        if t == "dict" and "keys" in option:
            self._apply_suboptions(option["keys"])
        elif t == "cmd" and "params_keys" in option:
            self._apply_suboptions(option["params_keys"])
        elif t in ("combo", "bool_list"):
            use = option.get("use")
            if use is not None:
                params = option.get("use_params")
                if not isinstance(params, dict):
                    params = {}
                option["keys"] = self.apply_by_id(use, params)

    def apply_by_id(self, id: str, params: dict = None) -> List[Dict[str, str]]:
        """
        Apply placeholders by id

        :param id: Placeholder options id
        :param params: Additional parameters for specific placeholders
        """
        if params is None:
            params = {}
        handler = self._apply_handlers.get(id)
        return handler(params) if handler else []

    def get_audio_tts_whisper_voices(self) -> List[Dict[str, str]]:
        """
        Get audio TTS whisper voices list

        :return: placeholders list
        """
        voices = self.window.core.audio.whisper.get_voices()
        return [{v: v} for v in voices]

    def get_audio_input_devices(self) -> List[Dict[str, str]]:
        """
        Get audio input devices list

        :return: placeholders list
        """
        devices = self.window.core.audio.get_input_devices()
        return [{str(did): name} for did, name in devices]

    def get_audio_output_devices(self) -> List[Dict[str, str]]:
        """
        Get audio output devices list

        :return: placeholders list
        """
        devices = self.window.core.audio.get_output_devices()
        return [{str(did): name} for did, name in devices]

    def get_audio_input_backend(self) -> List[Dict[str, str]]:
        """
        Get audio input backends list

        :return: placeholders list
        """
        items = self.window.core.audio.get_input_backends()
        return [{str(i): name} for i, name in items]

    def get_audio_output_backend(self) -> List[Dict[str, str]]:
        """
        Get audio output backends list

        :return: placeholders list
        """
        items = self.window.core.audio.get_output_backends()
        return [{str(i): name} for i, name in items]

    def get_langchain_providers(self) -> List[Dict[str, str]]:
        """
        Get Langchain LLM provider placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices(MODE_LANGCHAIN)
        return [{k: v} for k, v in choices.items()]

    def get_llama_index_providers(self) -> List[Dict[str, str]]:
        """
        Get Llama-index LLM provider placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices(MODE_LLAMA_INDEX)
        return [{k: v} for k, v in choices.items()]

    def get_llm_providers(self) -> List[Dict[str, str]]:
        """
        Get all LLM provider placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices()
        return [{k: v} for k, v in choices.items()]

    def get_embeddings_providers(self) -> List[Dict[str, str]]:
        """
        Get embeddings placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices("embeddings")
        return [{k: v} for k, v in choices.items()]

    def get_agent_providers(self) -> List[Dict[str, str]]:
        """
        Get all agent provider placeholders list

        :return: placeholders list
        """
        return self.window.core.agents.provider.get_choices()

    def get_agent_providers_llama(self) -> List[Dict[str, str]]:
        """
        Get Llama-index agent provider placeholders list

        :return: placeholders list
        """
        return self.window.core.agents.provider.get_choices(AGENT_TYPE_LLAMA)

    def get_agent_providers_openai(self) -> List[Dict[str, str]]:
        """
        Get OpenAI agent provider placeholders list

        :return: placeholders list
        """
        return self.window.core.agents.provider.get_choices(AGENT_TYPE_OPENAI)

    def get_remote_tools_openai(self) -> List[Dict[str, str]]:
        """
        Get OpenAI remote tools placeholders list

        :return: placeholders list
        """
        return self.window.core.openai.remote_tools.get_choices()

    def get_llama_index_chat_modes(self) -> List[Dict[str, str]]:
        """
        Get llama chat modes list

        :return: placeholders list
        """
        return [
            {"best": "best"},
            {"condense_question": "condense_question"},
            {"context": "context (default)"},
            {"condense_plus_context": "condense_plus_context"},
            {"simple": "simple (no query engine)"},
            {"react": "react"},
            {"openai": "openai"},
        ]

    def get_llama_index_loaders(self, type: str = "all") -> List[Dict[str, str]]:
        """
        Get data loaders placeholders list

        :param type: data type
        :return: placeholders list
        """
        data = []
        choices = self.window.controller.idx.common.get_loaders_choices()
        for choice in choices:
            if type == "all":
                data.append(choice)
            elif type == "file":
                key = next(iter(choice))
                if key.startswith("file_"):
                    data.append(choice)
            elif type == "web":
                key = next(iter(choice))
                if key.startswith("web_"):
                    data.append(choice)
        return data

    def get_vector_storage(self) -> List[Dict[str, str]]:
        """
        Get vector storage placeholders list

        :return: placeholders list
        """
        ids = self.window.core.idx.storage.get_ids()
        return [{i: i} for i in ids]

    def get_var_types(self) -> List[Dict[str, str]]:
        """
        Get langchain placeholders list

        :return: placeholders list
        """
        types = ["str", "int", "float", "bool", "dict", "list", "None"]
        return [{t: t} for t in types]

    def get_presets(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get presets placeholders list

        :param params: Additional parameters for specific placeholders
        :return: Presets placeholders list
        """
        if params is None:
            params = {}
        presets = self.window.core.presets.get_all()
        data = [{'_': '---'}]
        data.extend([{pid: pid} for pid in presets if not str(pid).startswith("current.")])
        return data

    def get_modes(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get modes placeholders list

        :param params: Additional parameters for specific placeholders
        :return: Modes placeholders list
        """
        if params is None:
            params = {}
        modes = self.window.core.modes.get_all()
        return [{mid: trans("mode." + mid)} for mid in modes]

    def get_multimodal(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get multimodal placeholders list

        :param params: Additional parameters for specific placeholders
        :return: multimodal placeholders list
        """
        if params is None:
            params = {}
        modes = self.window.core.models.get_multimodal_list()
        return [{mid: trans("multimodal." + mid)} for mid in modes]

    def get_models(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get models placeholders list (+ provider separators)

        :param params: Additional parameters for specific placeholders
        :return: Models placeholders list
        """
        if params is None:
            params = {}
        models = self.window.core.models.get_all()
        items: Dict[str, str] = {}
        for mid, model in models.items():
            allowed = True
            if isinstance(params.get("mode"), list):
                for m in params["mode"]:
                    if m not in model.mode:
                        allowed = False
                        break
            if allowed:
                items[mid] = model.name

        data: List[Dict[str, str]] = []
        if "allow_empty" in params and params["allow_empty"] is True:
            data.append({'_': '---'})
        providers = self.window.core.llm.get_choices()
        if not providers:
            for mid, name in sorted(items.items(), key=lambda kv: kv[1].lower()):
                data.append({mid: name})
            return data

        for provider, provider_label in providers.items():
            provider_items = [(k, v) for k, v in items.items() if models[k].provider == provider]
            if provider_items:
                data.append({f"separator::{provider}": provider_label})
                data.extend([{k: v} for k, v in provider_items])
        return data

    def get_agent_modes(self) -> List[Dict[str, str]]:
        """
        Get agent/expert modes placeholders list

        :return: Models placeholders list
        """
        modes = self.window.core.agents.legacy.get_allowed_modes()
        return [{mid: trans(f"mode.{mid}")} for mid in modes]

    def get_languages(self) -> List[Dict[str, str]]:
        """
        Get world languages list

        :return: Languages placeholders list
        """
        return self.window.core.text.get_language_choices()

    def get_idx(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get indexes placeholders list

        :param params: Additional parameters for specific placeholders
        :return: Indexes placeholders list
        """
        if params is None:
            params = {}
        indexes = self.window.core.idx.get_idx_ids()
        data = []
        if "none" not in params or params["none"] is True:
            data.append({'_': '---'})
        for item in indexes:
            for k, v in item.items():
                data.append({k: v})
        return data

    def get_syntax_styles(self) -> List[Dict[str, str]]:
        """
        Get highlighter styles list

        :return: placeholders list
        """
        styles = self.window.controller.chat.render.web_renderer.body.highlight.get_styles()
        styles.sort()
        return [{sid: sid} for sid in styles]

    def get_styles(self) -> List[Dict[str, str]]:
        """
        Get styles list

        :return: placeholders list
        """
        styles = self.window.controller.theme.common.get_styles_list()
        styles.sort()
        return [{sid: sid} for sid in styles]

    def get_keys(self) -> List[Dict[str, str]]:
        """
        Get keys

        :return: keys
        """
        return self.window.core.access.shortcuts.get_keys_choices()

    def get_modifiers(self) -> List[Dict[str, str]]:
        """
        Get modifiers

        :return: keys
        """
        return self.window.core.access.shortcuts.get_modifiers_choices()

    def _translate_sort_choices(self, choices: List[Dict[str, str]]) -> List[Dict[str, str]]:
        items = [(k, trans(v)) for choice in choices for k, v in choice.items()]
        items.sort(key=lambda x: x[1])
        return [{k: v} for k, v in items]

    def get_access_actions(self) -> List[Dict[str, str]]:
        """
        Get access actions list

        :return: app actions list
        """
        choices = self.window.core.access.actions.get_access_choices()
        return self._translate_sort_choices(choices)

    def get_speech_synthesis_actions(self) -> List[Dict[str, str]]:
        """
        Get speech actions list

        :return: app actions list
        """
        choices = self.window.core.access.actions.get_speech_synthesis_choices()
        return self._translate_sort_choices(choices)

    def get_voice_control_actions(self) -> List[Dict[str, str]]:
        """
        Get voice control actions list

        :return: app actions list
        """
        choices = self.window.core.access.actions.get_voice_control_choices()
        return self._translate_sort_choices(choices)