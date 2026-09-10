#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 19:22:00
# ================================================== #

from packaging.version import parse as parse_version, Version

from pygpt_net.core.types import (
    MODE_RESEARCH,
    MODE_CHAT,
    MODE_AGENT_V2,
    MODE_AGENT_OPENAI,
    MODE_COMPUTER,
    MODE_EXPERT
)

# old patches moved here
from .patches.patch_before_2_6_42 import Patch as PatchBefore2_6_42

class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: True if migrated
        """
        data = self.window.core.models.items
        base_data = self.window.core.models.get_base()
        from_base = self.window.core.models.from_base
        updated = False

        # get version of models config
        current = self.window.core.models.get_version()
        old = parse_version(current)

        # check if models file is older than current app version
        if old < version:

            # --------------------------------------------
            # previous patches for versions before 2.6.42
            if old < parse_version("2.6.42"):
                patcher = PatchBefore2_6_42(self.window)
                data, updated = patcher.execute(version)
            # --------------------------------------------

            # <  2.6.66 <--- add models
            if old < parse_version("2.6.66"):
                print("Migrating models from < 2.6.66...")
                models_to_add = [
                    "claude-opus-4-5",
                    "claude-sonnet-4-5",
                    "gemini-3-flash-preview",
                    "gemini-3-pro-image-preview",
                    "gemini-3-pro-preview",
                    "gpt-5.2-low",
                    "gpt-5.2-medium",
                    "gpt-5.2-high",
                    "gpt-image-1.5",
                    "nano-banana-pro-preview",
                    "sora-2",
                    "veo-3.1-fast-generate-preview",
                    "veo-3.1-generate-preview"
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
                updated = True

            # <  2.6.67 <--- add missing image input
            if old < parse_version("2.6.67"):
                print("Migrating models from < 2.6.67...")
                models_to_update = [
                    "claude-opus-4-5",
                    "claude-sonnet-4-5",
                    "gemini-3-flash-preview",
                    "gemini-3-pro-image-preview",
                    "gemini-3-pro-preview",
                    "gpt-5.2-low",
                    "gpt-5.2-medium",
                    "gpt-5.2-high",
                    "gpt-image-1.5",
                    "nano-banana-pro-preview",
                    "sora-2",
                    "veo-3.1-fast-generate-preview",
                    "veo-3.1-generate-preview"
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if not m.is_image_input():
                            m.input.append("image")
                updated = True

            # <  2.7.5 <--- add: gemini-2.5-computer-use-preview-10-2025
            if old < parse_version("2.7.5"):
                print("Migrating models from < 2.7.5...")
                models_to_add = [
                    "gemini-2.5-computer-use-preview-10-2025",
                    "deep-research-pro-preview-12-2025"
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
                updated = True

            # <  2.7.7 <--- add missing image input
            if old < parse_version("2.7.7"):
                print("Migrating models from < 2.7.7...")
                models_to_add = [
                    "grok-4-1-fast-non-reasoning",
                    "grok-4-1-fast-reasoning",
                    "grok-4-fast-non-reasoning",
                    "grok-4-fast-reasoning"
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model

                models_to_update = [
                    "grok-4"
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if not m.is_image_input():
                            m.input.append("image")
                updated = True

            # <  2.7.8 <--- add missing image input
            if old < parse_version("2.7.8"):
                print("Migrating models from < 2.7.8...")
                models_to_update = [
                    "grok-4"
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if not m.is_image_input():
                            m.input.append("image")
                updated = True

            # <  2.7.9 <--- add missing audio input
            if old < parse_version("2.7.9"):
                print("Migrating models from < 2.7.9...")
                models_to_update = [
                    "grok-4",
                    "grok-4-fast-non-reasoning",
                    "grok-4-fast-reasoning",
                    "grok-4-1-fast-non-reasoning",
                    "grok-4-1-fast-reasoning",
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if not m.is_audio_input():
                            m.input.append("audio")
                        if not m.is_audio_output():
                            m.output.append("audio")
                        if not m.has_mode("audio"):
                            m.mode.append("audio")
                models_to_remove = [
                    "gemini-2.5-flash-preview-native-audio-dialog",
                ]
                for model in models_to_remove:
                    if model in data:
                        del data[model]
                models_to_add = [
                    "gemini-2.5-flash-native-audio-latest",
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
                updated = True

            # <  2.7.12 <--- add imagine models
            if old < parse_version("2.7.12"):
                print("Migrating models from < 2.7.12...")
                models_to_add = [
                    "grok-imagine-image",
                    "grok-imagine-video",
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
                updated = True

            # <  2.8.0 <--- refresh API model catalog
            if old < parse_version("2.8.0"):
                print("Migrating models from < 2.8.0...")

                # Models retired/removed by their API providers.
                models_to_remove = [
                    "chatgpt-4o-latest",
                    "codex-mini-latest",
                    "computer-use-preview",
                    "dall-e-2",
                    "dall-e-3",
                    "gpt-3.5-turbo-16k",
                    "gpt-4-32k",
                    "gpt-4-vision-preview",
                    "gpt-4o-realtime-preview",
                    "o1-mini",
                    "o1-preview",
                    "claude-3-5-sonnet-20240620",
                    "claude-3-7-sonnet-latest",
                    "claude-3-opus-latest",
                    "claude-opus-4-0",
                    "claude-sonnet-4-0",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro",
                    "gemini-2.0-flash-exp",
                    "gemini-2.5-flash-image-preview",
                    "gemini-3-pro-image-preview",
                    "gemini-3-pro-preview",
                    "imagen-3.0-generate-002",
                    "veo-3.0-fast-generate-preview",
                    "veo-3.0-generate-preview",
                    "grok-3",
                    "grok-3-fast",
                    "grok-4",
                    "grok-4-1-fast-non-reasoning",
                    "grok-4-1-fast-reasoning",
                    "grok-4-fast-non-reasoning",
                    "grok-4-fast-reasoning",
                    "deepseek_api_chat",
                    "deepseek_api_reasoner",
                    "r1-1776",
                    "sonar-reasoning",
                ]
                for model in models_to_remove:
                    if model in data:
                        del data[model]

                # New current models introduced in the 2.8.0 base catalog.
                models_to_add = [
                    "claude-fable-5",
                    "claude-haiku-4-5",
                    "claude-opus-5",
                    "claude-sonnet-5",
                    "deep-research-max-preview-04-2026",
                    "deep-research-preview-04-2026",
                    "deepseek_api_v4_flash",
                    "deepseek_api_v4_pro",
                    "gemini-2.5-flash-image",
                    "gemini-3-pro-image",
                    "gemini-3.1-flash-image",
                    "gemini-3.1-flash-lite-image",
                    "gemini-3.1-flash-live-preview",
                    "gemini-3.1-flash-tts-preview",
                    "gemini-3.1-pro-preview",
                    "gemini-3.5-flash",
                    "gemini-3.5-flash-lite",
                    "gemini-3.6-flash",
                    "gpt-5.6-sol-high",
                    "gpt-5.6-sol-low",
                    "gpt-5.6-sol-medium",
                    "gpt-5.6-luna-high",
                    "gpt-5.6-luna-low",
                    "gpt-5.6-luna-medium",
                    "gpt-5.6-terra-high",
                    "gpt-5.6-terra-low",
                    "gpt-5.6-terra-medium",
                    "gpt-image-2",
                    "gpt-realtime-2.1",
                    "gpt-realtime-2.1-mini",
                    "grok-4.3-latest",
                    "grok-4.5-latest",
                    "grok-imagine-image-quality-latest",
                    "grok-imagine-video-1.5",
                    "veo-3.1-lite-generate-preview",
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model

                # Refresh technical capability metadata for models that remain active.
                # Preserve user-facing flags/name while taking limits/modalities/modes from base.
                models_to_update = [
                    "gpt-image-1",
                    "gpt-image-1.5",
                    "claude-sonnet-4-5",
                    "gemini-3-flash-preview",
                    "gemini-2.5-computer-use-preview-10-2025",
                    "gemini-2.5-flash-native-audio-latest",
                    "deep-research-pro-preview-12-2025",
                    "imagen-4.0-generate-001",
                    "nano-banana-pro-preview",
                    "veo-3.1-fast-generate-preview",
                    "veo-3.1-generate-preview",
                    "grok-2-image-1212",
                    "grok-imagine-image",
                    "grok-imagine-video",
                ]
                for model in models_to_update:
                    if model in data:
                        current_model = data[model]
                        base_model = from_base(model)
                        if base_model:
                            base_model.default = current_model.default
                            base_model.imported = current_model.imported
                            base_model.name = current_model.name
                            data[model] = base_model

                updated = True


            # <  2.8.2 <--- add missing audio input
            if old < parse_version("2.8.2"):
                print("Migrating models from < 2.8.2...")
                models_to_update = [
                    "grok-4.5-latest",
                    "grok-4.3-latest",
                    "grok-4.5",
                    "grok-4.3",
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if not m.is_audio_input():
                            m.input.append("audio")
                        if not m.is_audio_output():
                            m.output.append("audio")
                        if not m.has_mode("audio"):
                            m.mode.append("audio")

                models_to_update = [
                    "gemini-3.5-flash",
                    "gemini-3.5-flash-lite",
                    "gemini-3.6-flash",
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if m.has_mode("computer"):
                            m.mode.remove("computer")

                models_to_remove = [
                    "gemini-3.1-flash-tts-preview",
                ]
                for model in models_to_remove:
                    if model in data:
                        del data[model]
                models_to_add = [
                    "computer-use-preview",
                    "gemini-3.7-flash",
                    "gemini-pro-latest",
                    "gemini-flash-latest",
                    "grok-4.6",
                    "sora-2-pro",
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
                updated = True

            # <  2.8.5 <--- remove deprecated Assistants mode and add current Ollama models
            if old < parse_version("2.8.5"):
                print("Migrating models from < 2.8.5...")

                # Assistants mode is no longer selectable. Keep the legacy implementation
                # in the codebase, but remove the mode capability from user models.
                for model in data.values():
                    if model.has_mode("assistant"):
                        model.remove_mode("assistant")
                        updated = True

                ollama_models_to_add = [
                    "SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M",
                    "deepseek-r1:8b",
                    "gemma4:e4b",
                    "llama4:scout",
                    "mistral-small3.2:latest",
                    "nemotron-3.5-lightning:30b",
                    "qwen3.5:9b",
                    "qwen3.6:27b",
                ]

                for key in ollama_models_to_add:
                    base_model = from_base(key)
                    if not base_model:
                        continue

                    existing_model = None
                    for current_model in data.values():
                        if current_model.id == base_model.id:
                            existing_model = current_model
                            break

                    if existing_model is None:
                        if key not in data:
                            data[key] = base_model
                            updated = True
                        continue

                    for input_type in base_model.input:
                        if input_type not in existing_model.input:
                            existing_model.input.append(input_type)
                            updated = True

                    if base_model.tool_calls and not existing_model.tool_calls:
                        existing_model.tool_calls = True
                        updated = True

            # <  2.8.10 <--- add Agents v2 capability to Chat models
            if old < parse_version("2.8.10"):
                print("Migrating models from < 2.8.10...")
                for model in data.values():
                    if model.has_mode(MODE_CHAT) and not model.has_mode(MODE_AGENT_V2):
                        model.add_mode(MODE_AGENT_V2)
                        updated = True

            # <  2.8.12 <--- refresh Computer Use models and add new API models
            if old < parse_version("2.8.12"):
                print("Migrating models from < 2.8.12...")

                # Add GPT-6 Astra
                for key in (
                        "gpt-6-astra-low",
                        "gpt-6-astra-medium",
                        "gpt-6-astra-high",
                ):
                    base_model = from_base(key)
                    if not base_model:
                        continue
                    base_effort = str(
                        (getattr(base_model, "extra", None) or {}).get("reasoning_effort", "")
                    )
                    if not any(
                            str(getattr(model, "id", "") or "") == base_model.id
                            and str(
                                (getattr(model, "extra", None) or {}).get("reasoning_effort", "")
                            ) == base_effort
                            for model in data.values()
                    ):
                        data[key] = base_model
                        updated = True

                # Add Claude Fable 5.1
                key = "claude-fable-5-1"
                base_model = from_base(key)
                if base_model and not any(
                        str(getattr(model, "id", "") or "") == base_model.id
                        for model in data.values()
                ):
                    data[key] = base_model
                    updated = True

                # Sonar API does not accept custom/native tool definitions.
                # Match by API model ID so renamed/custom user keys are migrated too.
                sonar_models = {
                    "sonar",
                    "sonar-pro",
                    "sonar-reasoning-pro",
                    "sonar-deep-research",
                }
                for model in data.values():
                    model_id = str(getattr(model, "id", "") or "")
                    if model_id in sonar_models and model.tool_calls:
                        model.tool_calls = False
                        updated = True

                # GA Computer Use is supported by every GPT-5.6 family variant
                # and GPT-6 Astra. Match by API model ID so custom user keys and
                # all reasoning variants are migrated as well.
                for model in data.values():
                    model_id = str(getattr(model, "id", "") or "")
                    if (model_id.startswith("gpt-5.6-") or model_id == "gpt-6-astra") \
                            and not model.has_mode(MODE_COMPUTER):
                        model.add_mode(MODE_COMPUTER)
                        updated = True

                # Google Computer Use models supported by the Generate Content API.
                # Normalize the optional ``models/`` prefix so imported/custom user
                # model IDs are migrated as well. Gemini 3.8 Flash is included for
                # user-defined models even though it is not yet in the bundled catalog.
                google_computer_models = {
                    "gemini-3.8-flash",
                    "gemini-3.7-flash",
                    "gemini-3.5-flash-lite",
                    "gemini-3.5-flash",
                    "gemini-3-flash-preview",
                    "gemini-2.5-computer-use-preview-10-2025",
                }
                for model in data.values():
                    model_id = str(getattr(model, "id", "") or "").lower()
                    if model_id.startswith("models/"):
                        model_id = model_id[7:]
                    if model_id in google_computer_models and not model.has_mode(MODE_COMPUTER):
                        model.add_mode(MODE_COMPUTER)
                        updated = True

                # Anthropic Computer Use support mirrors the model families handled
                # by provider/api/anthropic/computer.py. Prefix matching also covers
                # dated API IDs and user models stored under custom keys.
                anthropic_computer_prefixes = (
                    "claude-fable-5",
                    "claude-mythos-5",
                    "claude-opus-5",
                    "claude-sonnet-5",
                    "claude-opus-4-8",
                    "claude-opus-4-7",
                    "claude-opus-4-6",
                    "claude-sonnet-4-6",
                    "claude-opus-4-5",
                    "claude-sonnet-4-5",
                    "claude-haiku-4-5",
                )
                for model in data.values():
                    model_id = str(getattr(model, "id", "") or "").lower()
                    if any(model_id.startswith(prefix) for prefix in anthropic_computer_prefixes) \
                            and not model.has_mode(MODE_COMPUTER):
                        model.add_mode(MODE_COMPUTER)
                        updated = True

                deprecated_openai_prefixes = (
                    "computer-use-preview",
                    "o3-deep-research",
                    "o4-mini-deep-research",
                )
                for key in list(data.keys()):
                    model = data.get(key)
                    model_id = str(getattr(model, "id", "") or "")
                    if str(key).startswith(deprecated_openai_prefixes) \
                            or model_id.startswith(deprecated_openai_prefixes):
                        del data[key]
                        updated = True

            # <  2.8.13 <--- add latest GPT Codex model
            if old < parse_version("2.8.13"):
                print("Migrating models from < 2.8.13...")

                # GPT-5.3-Codex is the current dedicated Codex API model.
                # Add all supported reasoning-effort variants from the base catalog.
                for key in (
                        "gpt-5.3-codex-low",
                        "gpt-5.3-codex-medium",
                        "gpt-5.3-codex-high",
                        "gpt-5.3-codex-xhigh",
                ):
                    base_model = from_base(key)
                    if not base_model:
                        continue
                    base_effort = str(
                        (getattr(base_model, "extra", None) or {}).get("reasoning_effort", "")
                    )
                    if not any(
                            str(getattr(model, "id", "") or "") == base_model.id
                            and str(
                                (getattr(model, "extra", None) or {}).get("reasoning_effort", "")
                            ) == base_effort
                            for model in data.values()
                    ):
                        data[key] = base_model
                        updated = True

        # update file
        if updated:
            # fix empty/broken data
            for key in list(data.keys()):
                if not data[key]:
                    del data[key]
            data = dict(sorted(data.items()))
            self.window.core.models.items = data
            self.window.core.models.save()

            # also patch any missing models, only if models file is older than 2.5.84
            if old < parse_version("2.5.84"):
                self.window.core.models.patch_missing()

        return updated
