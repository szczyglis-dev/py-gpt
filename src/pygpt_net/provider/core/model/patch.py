#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:18:00
# ================================================== #

import copy
import re

from packaging.version import parse as parse_version, Version

from pygpt_net.provider.core.model.compat import supports_future_computer_mode
from pygpt_net.core.types.reasoning import (
    LEGACY_REASONING_SUFFIXES,
    get_provider_efforts,
    legacy_key_parts,
)

from pygpt_net.core.types import (
    MODE_RESEARCH,
    MODE_CHAT,
    MODE_AGENT_V2,
    MODE_AGENT_OPENAI,
    MODE_COMPUTER,
    MODE_EXPERT,
    MODE_COMPLETION,
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
                    "gpt-5.6-sol",
                    "gpt-5.6-luna",
                    "gpt-5.6-terra",
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

                # Add GPT-6 Astra. Reasoning effort is selected at runtime,
                # so the catalog contains one item for the API model ID.
                key = "gpt-6-astra"
                base_model = from_base(key)
                if base_model and not any(
                        str(getattr(model, "id", "") or "") == base_model.id
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
                    if supports_future_computer_mode("openai", model_id) \
                            and not model.has_mode(MODE_COMPUTER):
                        model.add_mode(MODE_COMPUTER)
                        updated = True

                # Google Computer Use models supported by the Generate Content API.
                # Normalize the optional ``models/`` prefix so imported/custom user
                # model IDs are migrated as well. Gemini 3.8 Flash is included for
                # user-defined models even though it is not yet in the bundled catalog.
                for model in data.values():
                    model_id = str(getattr(model, "id", "") or "").lower()
                    if supports_future_computer_mode("google", model_id) \
                            and not model.has_mode(MODE_COMPUTER):
                        model.add_mode(MODE_COMPUTER)
                        updated = True

                # Anthropic Computer Use support mirrors the model families handled
                # by provider/api/anthropic/computer.py. Prefix matching also covers
                # dated API IDs and user models stored under custom keys.
                for model in data.values():
                    model_id = str(getattr(model, "id", "") or "").lower()
                    if supports_future_computer_mode("anthropic", model_id) \
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
                # Reasoning effort is selected at runtime from one catalog item.
                key = "gpt-5.3-codex"
                base_model = from_base(key)
                if base_model and not any(
                        str(getattr(model, "id", "") or "") == base_model.id
                        for model in data.values()
                ):
                    data[key] = base_model
                    updated = True

            # <  2.8.14 <--- add GPT Image 2.5 models and LlamaIndex completion modes
            if old < parse_version("2.8.14"):
                print("Migrating models from < 2.8.14...")

                # OpenAI exposes GPT Image 2.5 as Flare and Sunburst. Add both
                # to existing model catalogs, but preserve each user's current
                # image-mode/default choices. New installations get the defaults
                # declared in the bundled models.json instead.
                for key in (
                        "gpt-image-2.5-flare",
                        "gpt-image-2.5-sunburst",
                ):
                    if key in data:
                        continue
                    base_model = from_base(key)
                    if not base_model:
                        continue
                    base_model.default = False
                    data[key] = base_model
                    updated = True

                # Completion mode for text/chat models is handled through the
                # provider's LlamaIndex completion interface. For OpenAI this
                # maps chat models to Chat Completions and keeps instruct-only
                # models on the legacy Completions endpoint.
                for model in data.values():
                    if not getattr(model, "llama_index", None):
                        continue
                    if not model.has_mode(MODE_CHAT):
                        continue
                    if "text" not in (getattr(model, "input", None) or []):
                        continue
                    if "text" not in (getattr(model, "output", None) or []):
                        continue
                    if not model.has_mode(MODE_COMPLETION):
                        model.add_mode(MODE_COMPLETION)
                        updated = True

            # < 2.8.17 <--- runtime reasoning effort; merge legacy variants
            if old < parse_version("2.8.17"):
                print("Migrating models from < 2.8.17...")

                base_by_identity = {}
                for base_key, base_model in base_data.items():
                    identity = (
                        str(getattr(base_model, "provider", "") or ""),
                        str(getattr(base_model, "id", "") or ""),
                    )
                    base_by_identity[identity] = (base_key, base_model)

                # Profiles that skipped one of the intermediate catalog patches
                # still need the canonical replacement models.
                for key in (
                        "gpt-5.3-codex",
                        "gpt-5.6-luna",
                        "gpt-5.6-sol",
                        "gpt-5.6-terra",
                        "gpt-6-astra",
                        "o3-mini",
                ):
                    base_model = from_base(key)
                    if base_model is None:
                        continue
                    identity = (
                        str(getattr(base_model, "provider", "") or ""),
                        str(getattr(base_model, "id", "") or ""),
                    )
                    if not any(
                            (str(getattr(model, "provider", "") or ""),
                             str(getattr(model, "id", "") or "")) == identity
                            for model in data.values()
                    ):
                        data[key] = copy.deepcopy(base_model)
                        updated = True

                # Find historical effort variants. The old catalog encoded the
                # level both in the list key and in extra.reasoning_effort.
                variant_groups = {}
                identity_counts = {}
                for _key, _model in data.items():
                    _identity = (
                        str(getattr(_model, "provider", "") or ""),
                        str(getattr(_model, "id", "") or ""),
                    )
                    identity_counts[_identity] = identity_counts.get(_identity, 0) + 1

                for key, model in list(data.items()):
                    extra = getattr(model, "extra", None) or {}
                    base_key, suffix_effort = legacy_key_parts(key)
                    extra_effort = str(extra.get("reasoning_effort", "") or "").lower()
                    identity = (
                        str(getattr(model, "provider", "") or ""),
                        str(getattr(model, "id", "") or ""),
                    )
                    # Old PyGPT variants had a suffixed catalog key but the same
                    # unsuffixed provider model ID and/or extra.reasoning_effort.
                    # Do not rename a legitimate custom model whose real ID itself
                    # happens to end in "-high"/"-low".
                    suffix_variant = (
                        suffix_effort in LEGACY_REASONING_SUFFIXES
                        and (
                            str(getattr(model, "id", "") or "") != str(key)
                            or identity_counts.get(identity, 0) > 1
                            or identity in base_by_identity
                        )
                    )
                    is_variant = (
                        suffix_variant
                        or extra_effort in LEGACY_REASONING_SUFFIXES
                    )
                    if not is_variant:
                        continue
                    variant_groups.setdefault(identity, set()).add(key)
                    if base_key and base_key in data:
                        base_candidate = data[base_key]
                        base_identity = (
                            str(getattr(base_candidate, "provider", "") or ""),
                            str(getattr(base_candidate, "id", "") or ""),
                        )
                        if base_identity == identity:
                            variant_groups[identity].add(base_key)

                key_map = {}
                selected_key = self.window.core.config.get("model")

                def _merge_list(items, attr):
                    merged = []
                    for item in items:
                        for value in (getattr(item, attr, None) or []):
                            if value not in merged:
                                merged.append(value)
                    return merged

                def _unique_target_key(preferred, identity, member_keys):
                    """Avoid overwriting an unrelated custom model on key collision."""
                    if preferred not in data or preferred in member_keys:
                        return preferred
                    existing = data[preferred]
                    existing_identity = (
                        str(getattr(existing, "provider", "") or ""),
                        str(getattr(existing, "id", "") or ""),
                    )
                    if existing_identity == identity:
                        return preferred

                    provider = re.sub(r"[^a-z0-9_-]+", "-", str(identity[0] or "model").lower()).strip("-")
                    candidate_base = f"{preferred}-{provider or 'model'}"
                    candidate = candidate_base
                    counter = 2
                    while candidate in data and candidate not in member_keys:
                        occupied = data[candidate]
                        occupied_identity = (
                            str(getattr(occupied, "provider", "") or ""),
                            str(getattr(occupied, "id", "") or ""),
                        )
                        if occupied_identity == identity:
                            return candidate
                        candidate = f"{candidate_base}-{counter}"
                        counter += 1
                    return candidate

                for identity, member_keys in variant_groups.items():
                    members = [data[k] for k in member_keys if k in data]
                    if not members:
                        continue

                    base_entry = base_by_identity.get(identity)
                    if base_entry is not None:
                        preferred_key, base_model = base_entry
                    else:
                        base_model = None
                        trimmed = [legacy_key_parts(k)[0] for k in member_keys]
                        trimmed = [k for k in trimmed if k]
                        preferred_key = sorted(trimmed)[0] if trimmed else sorted(member_keys)[0]
                    target_key = _unique_target_key(preferred_key, identity, member_keys)

                    # Prefer an already canonical item, then the currently active
                    # variant, then high/medium/low/xhigh for deterministic merging.
                    rep_key = target_key if target_key in member_keys and target_key in data else None
                    if rep_key is None and selected_key in member_keys:
                        rep_key = selected_key
                    if rep_key is None:
                        rank = {"high": 0, "medium": 1, "low": 2, "xhigh": 3}
                        rep_key = min(
                            member_keys,
                            key=lambda k: (rank.get(legacy_key_parts(k)[1], 9), str(k)),
                        )
                    representative = copy.deepcopy(data[rep_key])

                    representative.mode = _merge_list(members, "mode")
                    representative.input = _merge_list(members, "input")
                    representative.output = _merge_list(members, "output")
                    representative.default = any(bool(getattr(m, "default", False)) for m in members)
                    representative.imported = any(bool(getattr(m, "imported", False)) for m in members)
                    representative.tool_calls = any(bool(getattr(m, "tool_calls", False)) for m in members)
                    representative.is_hidden = all(bool(getattr(m, "is_hidden", False)) for m in members)

                    if getattr(representative, "name", None):
                        representative.name = re.sub(
                            r"\s*\((?:low|medium|high|xhigh)\)\s*$",
                            "",
                            str(representative.name),
                            flags=re.IGNORECASE,
                        )
                    if base_model is not None:
                        representative.id = base_model.id
                        representative.reasoning_effort = bool(base_model.reasoning_effort)
                    else:
                        representative.reasoning_effort = bool(
                            get_provider_efforts(getattr(representative, "provider", ""))
                        )

                    extra = dict(getattr(representative, "extra", None) or {})
                    extra.pop("reasoning_effort", None)
                    representative.extra = extra

                    for old_key in list(member_keys):
                        if old_key in data:
                            del data[old_key]
                        key_map[old_key] = target_key
                    data[target_key] = representative
                    updated = True

                # Remove the obsolete per-model API parameter from every model,
                # and mark supported user/custom entries from the new base catalog.
                for model in data.values():
                    extra = dict(getattr(model, "extra", None) or {})
                    if "reasoning_effort" in extra:
                        del extra["reasoning_effort"]
                        model.extra = extra
                        updated = True

                    identity = (
                        str(getattr(model, "provider", "") or ""),
                        str(getattr(model, "id", "") or ""),
                    )
                    base_entry = base_by_identity.get(identity)
                    if base_entry is not None:
                        enabled = bool(base_entry[1].reasoning_effort)
                        if bool(getattr(model, "reasoning_effort", False)) != enabled:
                            model.reasoning_effort = enabled
                            updated = True

                # Rewrite global/current model references for merged user keys.
                # Contexts and presets are intentionally not rewritten: runtime
                # restoration resolves their legacy suffixes on demand.
                cfg = self.window.core.config
                cfg_changed = False

                def _mapped_ref(value):
                    # Only rewrite keys that were actually merged. Bundled legacy
                    # references are normalized by the config patch which runs
                    # before the model patch; this avoids touching legitimate
                    # custom model IDs that merely end in an effort-like suffix.
                    return key_map.get(value, value)

                current = cfg.get("model")
                mapped = _mapped_ref(current)
                if mapped != current:
                    cfg.set("model", mapped)
                    cfg_changed = True

                current_models = cfg.get("current_model")
                if isinstance(current_models, dict):
                    for mode_key, value in list(current_models.items()):
                        mapped = _mapped_ref(value)
                        if mapped != value:
                            current_models[mode_key] = mapped
                            cfg_changed = True

                if cfg_changed:
                    cfg.save()

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
