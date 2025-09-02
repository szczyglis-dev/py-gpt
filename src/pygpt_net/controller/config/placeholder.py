#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 16:00:00                  #
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
            "access_actions": lambda p: self.get_access_actions(),
            "agent_modes": lambda p: self.get_agent_modes(),
            "agent_provider": lambda p: self.get_agent_providers(),
            "agent_provider_llama": lambda p: self.get_agent_providers_llama(),
            "agent_provider_openai": lambda p: self.get_agent_providers_openai(),
            "audio_input_backend": lambda p: self.get_audio_input_backend(),
            "audio_input_devices": lambda p: self.get_audio_input_devices(),
            "audio_output_backend": lambda p: self.get_audio_output_backend(),
            "audio_output_devices": lambda p: self.get_audio_output_devices(),
            "audio_tts_whisper_voices": lambda p: self.get_audio_tts_whisper_voices(),
            "camera_devices": lambda p: self.get_camera_devices(),
            "embeddings_providers": lambda p: self.get_embeddings_providers(),
            "idx": lambda p: self.get_idx(p),
            "keys": lambda p: self.get_keys(),
            "keys_modifiers": lambda p: self.get_modifiers(),
            "langchain_providers": lambda p: self.get_langchain_providers(),
            "languages": lambda p: self.get_languages(),
            "llama_index_chat_modes": lambda p: self.get_llama_index_chat_modes(),
            "llama_index_loaders": lambda p: self.get_llama_index_loaders(),
            "llama_index_loaders_file": lambda p: self.get_llama_index_loaders(type="file"),
            "llama_index_loaders_web": lambda p: self.get_llama_index_loaders(type="web"),
            "llama_index_providers": lambda p: self.get_llama_index_providers(),
            "llm_providers": lambda p: self.get_llm_providers(),
            "models": lambda p: self.get_models(p),
            "modes": lambda p: self.get_modes(p),
            "multimodal": lambda p: self.get_multimodal(p),
            "presets": lambda p: self.get_presets(p),
            "remote_tools_openai": lambda p: self.get_remote_tools_openai(),
            "speech_synthesis_actions": lambda p: self.get_speech_synthesis_actions(),
            "styles": lambda p: self.get_styles(),
            "syntax_styles": lambda p: self.get_syntax_styles(),
            "vector_storage": lambda p: self.get_vector_storage(),
            "var_types": lambda p: self.get_var_types(),
            "voice_control_actions": lambda p: self.get_voice_control_actions(),
        }

    def _apply_combo_if_needed(self, item: Any):
        """
        Apply combo keys if needed

        :param item: item to check
        """
        if isinstance(item, dict) and item.get("type") == "combo":
            use = item.get("use")
            if use is not None:
                params = item.get("use_params")
                if not isinstance(params, dict):
                    params = {}
                item["keys"] = self.apply_by_id(use, params)

    def _apply_suboptions(self, mapping: Dict[str, Any]):
        """
        Apply placeholders to suboptions in mapping

        :param mapping: Suboptions mapping
        """
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
        :return: Filled placeholder list
        """
        if params is None:
            params = {}
        handler = self._apply_handlers.get(id)
        return handler(params) if handler else []

    def get_audio_tts_whisper_voices(self) -> List[Dict[str, str]]:
        """
        Get audio TTS whisper voices list

        :return: Filled placeholder list
        """
        voices = self.window.core.audio.whisper.get_voices()
        return [{v: v} for v in voices]

    def get_audio_input_devices(self) -> List[Dict[str, str]]:
        """
        Get audio input devices list

        :return: Filled placeholder list
        """
        devices = self.window.core.audio.get_input_devices()
        return [{str(did): name} for did, name in devices]

    def get_camera_devices(self) -> List[Dict[str, str]]:
        """
        Get camera devices list

        :return: Filled placeholder list
        """
        return self.window.core.camera.get_devices()

    def get_audio_output_devices(self) -> List[Dict[str, str]]:
        """
        Get audio output devices list

        :return: Filled placeholder list
        """
        devices = self.window.core.audio.get_output_devices()
        return [{str(did): name} for did, name in devices]

    def get_audio_input_backend(self) -> List[Dict[str, str]]:
        """
        Get audio input backends list

        :return: Filled placeholder list
        """
        items = self.window.core.audio.get_input_backends()
        return [{str(i): name} for i, name in items]

    def get_audio_output_backend(self) -> List[Dict[str, str]]:
        """
        Get audio output backends list

        :return: Filled placeholder list
        """
        items = self.window.core.audio.get_output_backends()
        return [{str(i): name} for i, name in items]

    def get_langchain_providers(self) -> List[Dict[str, str]]:
        """
        Get Langchain LLM providers list

        :return: Filled placeholder list
        """
        choices = self.window.core.llm.get_choices(MODE_LANGCHAIN)
        return [{k: v} for k, v in choices.items()]

    def get_llama_index_providers(self) -> List[Dict[str, str]]:
        """
        Get Llama-index LLM providers list

        :return: Filled placeholder list
        """
        choices = self.window.core.llm.get_choices(MODE_LLAMA_INDEX)
        return [{k: v} for k, v in choices.items()]

    def get_llm_providers(self) -> List[Dict[str, str]]:
        """
        Get all LLM provider placeholders list

        :return: Filled placeholder list
        """
        choices = self.window.core.llm.get_choices()
        return [{k: v} for k, v in choices.items()]

    def get_embeddings_providers(self) -> List[Dict[str, str]]:
        """
        Get embedding providers list

        :return: Filled placeholder list
        """
        choices = self.window.core.llm.get_choices("embeddings")
        return [{k: v} for k, v in choices.items()]

    def get_agent_providers(self) -> List[Dict[str, str]]:
        """
        Get all agent providers list

        :return: Filled placeholder list
        """
        return self.window.core.agents.provider.get_choices()

    def get_agent_providers_llama(self) -> List[Dict[str, str]]:
        """
        Get Llama-index agent provider list

        :return: Filled placeholder list
        """
        return self.window.core.agents.provider.get_choices(AGENT_TYPE_LLAMA)

    def get_agent_providers_openai(self) -> List[Dict[str, str]]:
        """
        Get OpenAI agent provider list

        :return: Filled placeholder list
        """
        return self.window.core.agents.provider.get_choices(AGENT_TYPE_OPENAI)

    def get_remote_tools_openai(self) -> List[Dict[str, str]]:
        """
        Get OpenAI remote tools list

        :return: Filled placeholder list
        """
        return self.window.core.api.openai.remote_tools.get_choices()

    def get_llama_index_chat_modes(self) -> List[Dict[str, str]]:
        """
        Get llama chat modes list

        :return: Filled placeholder list
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
        Get data loaders list

        :param type: data type
        :return: Filled placeholder list
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
        Get vector storage list

        :return: Filled placeholder list
        """
        ids = self.window.core.idx.storage.get_ids()
        return [{i: i} for i in ids]

    def get_var_types(self) -> List[Dict[str, str]]:
        """
        Get var types list

        :return: Filled placeholder list
        """
        types = ["str", "int", "float", "bool", "dict", "list", "None"]
        return [{t: t} for t in types]

    def get_presets(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get presets list

        :param params: Additional parameters for specific placeholders
        :return: Filled placeholder list
        """
        if params is None:
            params = {}
        presets = self.window.core.presets.get_all()
        data = [{'_': '---'}]
        data.extend([{pid: pid} for pid in presets if not str(pid).startswith("current.")])
        return data

    def get_modes(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get modes list

        :param params: Additional parameters for specific placeholders
        :return: Filled placeholder list
        """
        if params is None:
            params = {}
        modes = self.window.core.modes.get_all()
        return [{mid: trans("mode." + mid)} for mid in modes]

    def get_multimodal(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get multimodal options list

        :param params: Additional parameters for specific placeholders
        :return: Filled placeholder list
        """
        if params is None:
            params = {}
        modes = self.window.core.models.get_multimodal_list()
        return [{mid: trans("multimodal." + mid)} for mid in modes]

    def get_models(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get models list (+ provider separators)

        :param params: Additional parameters for specific placeholders
        :return: Filled placeholder list
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
        Get agent/expert modes list

        :return: Filled placeholder list
        """
        modes = self.window.core.agents.legacy.get_allowed_modes()
        return [{mid: trans(f"mode.{mid}")} for mid in modes]

    def get_languages(self) -> List[Dict[str, str]]:
        """
        Get world languages list

        :return: Filled placeholder list
        """
        return self.window.core.text.get_language_choices()

    def get_idx(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get indexes (LlamaIndex) list

        :param params: Additional parameters for specific placeholders
        :return: Filled placeholder list
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
        Get code syntax highlighter styles list

        :return: Filled placeholder list
        """
        styles = self.window.controller.chat.render.web_renderer.body.highlight.get_styles()
        styles.sort()
        return [{sid: sid} for sid in styles]

    def get_styles(self) -> List[Dict[str, str]]:
        """
        Get styles list (blocks, chatgpt, etc.)

        :return: Filled placeholder list
        """
        styles = self.window.controller.theme.common.get_styles_list()
        styles.sort()
        return [{sid: sid} for sid in styles]

    def get_keys(self) -> List[Dict[str, str]]:
        """
        Get keyboard keys list

        :return: Filled placeholder list
        """
        return self.window.core.access.shortcuts.get_keys_choices()

    def get_modifiers(self) -> List[Dict[str, str]]:
        """
        Get modifiers

        :return: Filled placeholder list
        """
        return self.window.core.access.shortcuts.get_modifiers_choices()

    def _translate_sort_choices(self, choices: List[Dict[str, str]]) -> List[Dict[str, str]]:
        items = [(k, trans(v)) for choice in choices for k, v in choice.items()]
        items.sort(key=lambda x: x[1])
        return [{k: v} for k, v in items]

    def get_access_actions(self) -> List[Dict[str, str]]:
        """
        Get access actions list

        :return: Filled placeholder list
        """
        choices = self.window.core.access.actions.get_access_choices()
        return self._translate_sort_choices(choices)

    def get_speech_synthesis_actions(self) -> List[Dict[str, str]]:
        """
        Get speech actions list

        :return: Filled placeholder list
        """
        choices = self.window.core.access.actions.get_speech_synthesis_choices()
        return self._translate_sort_choices(choices)

    def get_voice_control_actions(self) -> List[Dict[str, str]]:
        """
        Get voice control actions list

        :return: Filled placeholder list
        """
        choices = self.window.core.access.actions.get_voice_control_choices()
        return self._translate_sort_choices(choices)