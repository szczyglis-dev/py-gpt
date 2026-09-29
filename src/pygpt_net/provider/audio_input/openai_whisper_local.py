#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.02 19:40:00                  #
# ================================================== #

import gc
import os
import sys
from urllib.parse import urlparse

from pygpt_net.core.typing_compat import ensure_typing_self_compat
from pygpt_net.core.types import WHISPER_LOCAL_MODELS

from .base import BaseProvider


class OpenAIWhisperLocal(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        OpenAI Whisper provider (local model)

        :param args: args
        :param kwargs: kwargs
        """
        super(OpenAIWhisperLocal, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "openai_whisper_local"
        self.name = "Whisper (local)"
        self.model = None
        self.loaded_model_name = None

        # The renderer memory guard works on process RSS. Local Whisper/Torch
        # lives in the same process, so account for its resident memory
        # separately and exclude that part from the renderer limit.
        self._import_memory_bytes = 0
        self._resident_memory_bytes = 0
        self._whisper_import_tracked = False

    def init_options(self):
        """Initialize options"""
        self.plugin.add_option(
            "whisper_local_model",
            type="combo",
            value="base",
            label="Model",
            tab="openai_whisper_local",
            keys=WHISPER_LOCAL_MODELS,
            description="Select a local Whisper model. The size shown in the list is the approximate checkpoint "
                        "download size on disk, not RAM/VRAM usage. Default: base. Install optional dependencies "
                        "using Config > Package Manager.",
            urls={
                "Models": "https://github.com/openai/whisper"
            }
        )
        self.plugin.add_option(
            "whisper_local_model_custom",
            type="text",
            value="",
            label="Custom model name override",
            tab="openai_whisper_local",
            description="Optional custom model name or local checkpoint path. When set, this value overrides the "
                        "model selected above. Leave empty to use the selected model.",
        )
        self.plugin.add_option(
            "whisper_local_keep_in_memory",
            type="bool",
            value=True,
            label="Keep model in RAM",
            tab="openai_whisper_local",
            description="Keep the local Whisper model loaded in RAM between transcriptions. Disable to reduce RAM "
                        "usage; the model will be loaded from the local cache for each transcription. Default: True.",
        )

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        if not self.is_configured():
            raise ImportError(self.get_config_message())

        model = self.load_model()
        memory_before = self._get_rss_bytes()
        try:
            result = model.transcribe(path)
            return str(result["text"])
        finally:
            # Torch may retain work buffers/allocator arenas after inference.
            # Track any RSS growth so it is not mistaken for renderer memory.
            self._track_resident_growth(memory_before)
            if not self.should_keep_model_in_memory():
                del model
                self.release_model()

    def get_model_name(self) -> str:
        """Return configured local Whisper model name, honoring custom override."""
        custom_name = self.plugin.get_option_value('whisper_local_model_custom')
        if custom_name is not None:
            custom_name = str(custom_name).strip()
            if custom_name:
                return custom_name

        model_name = self.plugin.get_option_value('whisper_local_model')
        if model_name is None:
            return "base"
        model_name = str(model_name).strip()
        return model_name or "base"

    def should_keep_model_in_memory(self) -> bool:
        """Return True when the loaded local Whisper model should stay cached in RAM."""
        try:
            value = self.plugin.get_option_value('whisper_local_keep_in_memory')
            if value is None:
                return True
            return bool(value)
        except Exception:
            return True

    def apply_memory_policy(self):
        """Apply current model/RAM settings to an already loaded model."""
        if self.model is None:
            return
        if (not self.should_keep_model_in_memory()
                or self.loaded_model_name != self.get_model_name()):
            self.release_model()

    def _get_rss_bytes(self) -> int:
        """Return current process RSS, or 0 when it cannot be read."""
        try:
            import psutil
            return int(psutil.Process(os.getpid()).memory_info().rss)
        except Exception:
            return 0

    def _import_whisper(self):
        """Import Whisper and account for Whisper/Torch import-time RSS growth."""
        ensure_typing_self_compat()
        before = self._get_rss_bytes()
        import whisper
        if not self._whisper_import_tracked:
            after = self._get_rss_bytes()
            if before > 0 and after > before:
                self._import_memory_bytes += after - before
            self._whisper_import_tracked = True
        return whisper

    def _track_resident_growth(self, before: int):
        """Account for RSS retained by model loading/inference."""
        if before <= 0:
            return
        after = self._get_rss_bytes()
        if after > before:
            self._resident_memory_bytes += after - before

    def get_memory_excluded_bytes(self) -> int:
        """
        Return estimated resident bytes owned by local Whisper/Torch.

        The process RSS cannot be split exactly by Python module, therefore the
        provider accounts for RSS growth around Whisper import, model loading and
        inference. The value is used only to keep that memory out of the renderer
        auto-cleanup threshold.
        """
        total = max(0, int(self._import_memory_bytes + self._resident_memory_bytes))
        rss = self._get_rss_bytes()
        if rss > 0:
            return min(total, rss)
        return total

    def get_model_cache_path(self) -> str:
        """Return expected path of the configured Whisper model in its cache."""
        model_name = self.get_model_name()
        if os.path.isfile(model_name):
            return model_name

        whisper = self._import_whisper()
        models = getattr(whisper, "_MODELS", {})
        url = models.get(model_name)
        if not url:
            return ""

        default_cache = os.path.join(os.path.expanduser("~"), ".cache")
        download_root = os.path.join(
            os.getenv("XDG_CACHE_HOME", default_cache),
            "whisper",
        )
        filename = os.path.basename(urlparse(url).path)
        return os.path.join(download_root, filename)

    def is_model_downloaded(self) -> bool:
        """Check whether the configured Whisper model checkpoint is present locally."""
        model_name = self.get_model_name()
        if self.model is not None and self.loaded_model_name == model_name:
            return True

        path = self.get_model_cache_path()
        return bool(path and os.path.isfile(path))

    def load_model(self, model_name: str = None):
        """Download/load a Whisper model and optionally keep it in memory for reuse."""
        whisper = self._import_whisper()

        if model_name is None:
            model_name = self.get_model_name()

        if self.model is not None and self.loaded_model_name != model_name:
            self.release_model()

        if self.model is None:
            before = self._get_rss_bytes()
            self.model = whisper.load_model(model_name)
            self.loaded_model_name = model_name
            self._track_resident_growth(before)

        return self.model

    def release_model(self):
        """Release the in-memory Whisper model while keeping the downloaded checkpoint."""
        if self.model is None:
            return

        before = self._get_rss_bytes()
        self.model = None
        self.loaded_model_name = None

        gc.collect()

        # Do not import torch just for cleanup; Whisper imports it already when
        # available. CUDA cache is VRAM, but clearing it is desirable when the
        # user explicitly disables keeping the model in memory.
        try:
            torch = sys.modules.get("torch")
            if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        # glibc may retain large freed arenas. Ask it to return them to the OS so
        # disabling "Keep model in RAM" has an immediate effect on Linux RSS.
        if sys.platform.startswith("linux"):
            try:
                import ctypes
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except Exception:
                pass

        after = self._get_rss_bytes()
        if before > 0 and after >= 0 and before > after:
            freed = before - after
            self._resident_memory_bytes = max(0, self._resident_memory_bytes - freed)

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        try:
            self._import_whisper()
        except ImportError:
            return False
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return (
            "Local Whisper dependencies are unavailable. Install openai-whisper using "
            "Config > Package Manager. A restart may be required. "
            "PyTorch requires significant disk space. FFmpeg must also be available on PATH."
        )
