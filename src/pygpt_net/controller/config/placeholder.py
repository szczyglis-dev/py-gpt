#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

from typing import Dict, Any, List

from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
)
from pygpt_net.utils import trans


class Placeholder:
    def __init__(self, window=None):
        """
        Configuration placeholder options controller

        :param window: Window instance
        """
        self.window = window

    def apply(self, option: Dict[str, Any]):
        """
        Apply placeholders to option

        :param option: Option dict
        """
        if option['type'] == 'dict' and 'keys' in option:
            for key in option['keys']:
                item = option['keys'][key]
                if type(item) is dict:
                    if "type" in item:
                        if item["type"] == "combo":
                            if "use" in item and item["use"] is not None:
                                params = {}
                                if "use_params" in item and type(item["use_params"]) is dict:
                                    params = item["use_params"]
                                item["keys"] = self.apply_by_id(item["use"], params)
        elif option['type'] == 'cmd' and 'params_keys' in option:
            for key in option['params_keys']:
                item = option['params_keys'][key]
                if type(item) is dict:
                    if "type" in item:
                        if item["type"] == "combo":
                            if "use" in item and item["use"] is not None:
                                params = {}
                                if "use_params" in item and type(item["use_params"]) is dict:
                                    params = item["use_params"]
                                item["keys"] = self.apply_by_id(item["use"], params)
        elif option['type'] == 'combo':
            if "use" in option and option["use"] is not None:
                params = {}
                if "use_params" in option and type(option["use_params"]) is dict:
                    params = option["use_params"]
                option["keys"] = self.apply_by_id(option["use"], params)
        elif option['type'] == 'bool_list':
            if "use" in option and option["use"] is not None:
                params = {}
                if "use_params" in option and type(option["use_params"]) is dict:
                    params = option["use_params"]
                option["keys"] = self.apply_by_id(option["use"], params)

    def apply_by_id(self, id: str, params: dict = None) -> List[Dict[str, str]]:
        """
        Apply placeholders by id

        :param id: Placeholder options id
        :param params: Additional parameters for specific placeholders
        """
        if params is None:
            params = {}
        if id == "presets":
            return self.get_presets(params)
        elif id == "modes":
            return self.get_modes(params)
        elif id == "models":
            return self.get_models(params)
        elif id == "multimodal":
            return self.get_multimodal(params)
        elif id == "langchain_providers":
            return self.get_langchain_providers()
        elif id == "llama_index_providers":
            return self.get_llama_index_providers()
        elif id == "llm_providers":
            return self.get_llm_providers()
        elif id == "embeddings_providers":
            return self.get_embeddings_providers()
        elif id == "llama_index_loaders":
            return self.get_llama_index_loaders()
        elif id == "llama_index_loaders_file":
            return self.get_llama_index_loaders(type="file")
        elif id == "llama_index_loaders_web":
            return self.get_llama_index_loaders(type="web")
        elif id == "llama_index_chat_modes":
            return self.get_llama_index_chat_modes()
        elif id == "vector_storage":
            return self.get_vector_storage()
        elif id == "var_types":
            return self.get_var_types()
        elif id == "agent_modes":
            return self.get_agent_modes()
        elif id == "agent_provider":
            return self.get_agent_providers()
        elif id == "syntax_styles":
            return self.get_syntax_styles()
        elif id == "styles":
            return self.get_styles()
        elif id == "idx":
            return self.get_idx(params)
        elif id == "keys":
            return self.get_keys()
        elif id == "keys_modifiers":
            return self.get_modifiers()
        elif id == "access_actions":
            return self.get_access_actions()
        elif id == "speech_synthesis_actions":
            return self.get_speech_synthesis_actions()
        elif id == "voice_control_actions":
            return self.get_voice_control_actions()
        elif id == "audio_input_devices":
            return self.get_audio_input_devices()
        elif id == "audio_tts_whisper_voices":
            return self.get_audio_tts_whisper_voices()
        else:
            return []

    def get_audio_tts_whisper_voices(self) -> List[Dict[str, str]]:
        """
        Get audio TTS whisper voices list

        :return: placeholders list
        """
        voices = self.window.core.audio.whisper.get_voices()
        data = []
        for voice in voices:
            data.append({voice: voice})
        return data

    def get_audio_input_devices(self) -> List[Dict[str, str]]:
        """
        Get audio input devices list

        :return: placeholders list
        """
        devices = self.window.core.audio.get_input_devices()
        data = []
        for device in devices:
            data.append({str(device[0]): device[1]})
        return data

    def get_langchain_providers(self) -> List[Dict[str, str]]:
        """
        Get Langchain LLM provider placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices(MODE_LANGCHAIN)
        data = []
        for id in choices:
            data.append({id: choices[id]})
        return data

    def get_llama_index_providers(self) -> List[Dict[str, str]]:
        """
        Get Llama-index LLM provider placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices(MODE_LLAMA_INDEX)
        data = []
        for id in choices:
            data.append({id: choices[id]})
        return data

    def get_llm_providers(self) -> List[Dict[str, str]]:
        """
        Get all LLM provider placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices()
        data = []
        for id in choices:
            data.append({id: choices[id]})
        return data

    def get_embeddings_providers(self) -> List[Dict[str, str]]:
        """
        Get embeddings placeholders list

        :return: placeholders list
        """
        choices = self.window.core.llm.get_choices("embeddings")
        data = []
        for id in choices:
            data.append({id: choices[id]})
        return data

    def get_agent_providers(self) -> List[Dict[str, str]]:
        """
        Get Llama-index agent provider placeholders list

        :return: placeholders list
        """
        ids = self.window.core.agents.provider.get_providers()
        data = []
        for id in ids:
            data.append({id: id})
        return data

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
        choices = self.window.controller.idx.common.get_loaders_choices() # list
        for choice in choices:
            if type == "all":
                data.append(choice)
            elif type == "file":
                key = list(choice.keys())[0]
                if key.startswith("file_"):
                    data.append(choice)
            elif type == "web":
                key = list(choice.keys())[0]
                if key.startswith("web_"):
                    data.append(choice)
        return data

    def get_vector_storage(self) -> List[Dict[str, str]]:
        """
        Get vector storage placeholders list

        :return: placeholders list
        """
        ids = self.window.core.idx.storage.get_ids()
        data = []
        for id in ids:
            data.append({id: id})
        return data

    def get_var_types(self) -> List[Dict[str, str]]:
        """
        Get langchain placeholders list

        :return: placeholders list
        """
        types = ["str", "int", "float", "bool", "dict", "list", "None"]
        data = []
        for type in types:
            data.append({type: type})
        return data

    def get_presets(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get presets placeholders list

        :param params: Additional parameters for specific placeholders
        :return: Presets placeholders list
        """
        if params is None:
            params = {}
        presets = self.window.core.presets.get_all()
        data = []
        data.append({'_': '---'})
        for id in presets:
            if id.startswith("current."):  # ignore "current" preset
                continue
            data.append({id: id})  # TODO: name
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
        data = []
        for id in modes:
            name = trans("mode." + id)
            data.append({id: name})
        return data

    def get_multimodal(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get multimodal placeholders list

        :param params: Additional parameters for specific placeholders
        :return: multimodal placeholders list
        """
        if params is None:
            params = {}
        modes = self.window.core.models.get_multimodal_list()
        data = []
        for id in modes:
            name = trans("multimodal." + id)
            data.append({id: name})
        return data

    def get_models(self, params: dict = None) -> List[Dict[str, str]]:
        """
        Get models placeholders list

        :param params: Additional parameters for specific placeholders
        :return: Models placeholders list
        """
        if params is None:
            params = {}
        models = self.window.core.models.get_all()
        data = []
        for id in models:
            model = models[id]
            allowed = True
            if "mode" in params and type(params["mode"]) is list:
                for mode in params["mode"]:
                    if mode not in model.mode:
                        allowed = False
                        break
            if not allowed:
                continue

            suffix = ""
            if model.provider == "ollama":
                suffix = " (Ollama)"
            name = model.name + suffix
            data.append({id: name})
        return data

    def get_agent_modes(self) -> List[Dict[str, str]]:
        """
        Get agent/expert modes placeholders list

        :return: Models placeholders list
        """
        modes = self.window.core.agents.legacy.get_allowed_modes()
        data = []
        for id in modes:
            name = trans(f"mode.{id}")
            data.append({id: name})
        return data

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
        data = []
        for id in styles:
            data.append({id: id})
        return data

    def get_styles(self) -> List[Dict[str, str]]:
        """
        Get styles list

        :return: placeholders list
        """
        styles = self.window.controller.theme.common.get_styles_list()
        styles.sort()
        data = []
        for id in styles:
            name = id
            data.append({id: name})
        return data

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

    def get_access_actions(self) -> List[Dict[str, str]]:
        """
        Get access actions list

        :return: app actions list
        """
        choices = self.window.core.access.actions.get_access_choices()
        translated_choices = []
        for choice in choices:
            for key, value in choice.items():
                translated_choices.append({key: trans(value)})
        # sort by translated values
        translated_choices.sort(key=lambda x: list(x.values())[0])
        return translated_choices

    def get_speech_synthesis_actions(self) -> List[Dict[str, str]]:
        """
        Get speech actions list

        :return: app actions list
        """
        choices = self.window.core.access.actions.get_speech_synthesis_choices()
        translated_choices = []
        for choice in choices:
            for key, value in choice.items():
                translated_choices.append({key: trans(value)})
        # sort by translated values
        translated_choices.sort(key=lambda x: list(x.values())[0])
        return translated_choices

    def get_voice_control_actions(self) -> List[Dict[str, str]]:
        """
        Get voice control actions list

        :return: app actions list
        """
        choices = self.window.core.access.actions.get_voice_control_choices()
        translated_choices = []
        for choice in choices:
            for key, value in choice.items():
                translated_choices.append({key: trans(value)})
        # sort by translated values
        translated_choices.sort(key=lambda x: list(x.values())[0])
        return translated_choices


