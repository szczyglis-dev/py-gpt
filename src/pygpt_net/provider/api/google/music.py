#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 09:30:00                  #
# ================================================== #

import base64
import datetime
import json
import os
import shutil
import subprocess
from typing import Optional, Dict, Any, List

import requests
from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from google import genai

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Music:
    """
    Text-to-music generation for Google (Lyria) in the "image" mode.

    This class encapsulates the whole music generation flow using Vertex AI Lyria.
    It mirrors the architecture used for images and videos (worker + signals),
    and saves outputs to disk as WAV by default, with optional ffmpeg transcoding to MP3/MP4.
    """

    def __init__(self, window=None):
        self.window = window
        self.worker: Optional[MusicWorker] = None

    def is_music_model(self, model_id: str) -> bool:
        """
        Heuristic check whether selected model is a music model (Lyria family).

        :param model_id: model id
        :return: True if Lyria/music model, False otherwise
        """
        mid = (model_id or "").lower()
        return "lyria" in mid or "music" in mid

    def generate(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            sync: bool = True
    ) -> bool:
        """
        Generate music using Vertex AI Lyria.

        :param context: BridgeContext with prompt, model, attachments (ignored)
        :param extra: extra parameters:
            - num: int, number of samples (maps to sample_count if no seed)
            - seed: int, generation seed (mutually exclusive with sample_count)
            - negative_prompt: str, negative prompt to exclude elements
            - format: str, 'wav' (default), 'mp3', or 'mp4'
            - inline: bool, inline mode
        :param sync: run synchronously (blocking) if True
        :return: True if started
        """
        extra = extra or {}
        ctx = context.ctx or CtxItem()
        model = context.model
        prompt = context.prompt or ""
        inline = bool(extra.get("inline", False))

        worker = MusicWorker()
        worker.window = self.window
        worker.client = self.window.core.api.google.get_client()
        worker.ctx = ctx

        # config
        worker.model = (model.id if model else "lyria-002")  # Lyria model id or resource
        worker.input_prompt = prompt
        worker.negative_prompt = extra.get("negative_prompt") or None

        # sample_count vs seed (mutually exclusive)
        worker.num = int(extra.get("num", 1))
        seed = extra.get("seed")
        worker.seed = int(seed) if seed not in (None, "") else None

        # preferred output format
        worker.out_format = str(extra.get("format") or self._default_format()).lower()

        # optional prompt improvement
        prompt_model = self.window.core.models.from_defaults()
        tmp = self.window.core.config.get('music.prompt_model') or self.window.core.config.get('video.prompt_model')
        if self.window.core.models.has(tmp):
            prompt_model = self.window.core.models.get(tmp)
        worker.model_prompt = prompt_model
        worker.system_prompt = self.window.core.prompt.get('music') or self.window.core.prompt.get('video')
        worker.raw = bool(self.window.core.config.get('img_raw'))

        worker.inline = inline

        self.worker = worker
        # Reuse video handlers for UX consistency (status/messages/download area)
        self.worker.signals.finished.connect(self.window.core.video.handle_finished)
        self.worker.signals.finished_inline.connect(self.window.core.video.handle_finished_inline)
        self.worker.signals.status.connect(self.window.core.video.handle_status)
        self.worker.signals.error.connect(self.window.core.video.handle_error)

        if sync or not self.window.controller.kernel.async_allowed(ctx):
            self.worker.run()
            return True

        # Use video busy state for unified UX
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {"id": "video"}))
        self.window.threadpool.start(self.worker)
        return True

    def _default_format(self) -> str:
        """
        Determine default preferred output format for saved files.
        """
        # try config override
        try:
            fmt = self.window.core.config.get('music.format')
            if isinstance(fmt, str) and fmt.strip():
                return fmt.strip()
        except Exception:
            pass
        # default to mp3 as most interoperable
        return "mp3"


class MusicSignals(QObject):
    finished = Signal(object, list, str)         # ctx, paths, prompt
    finished_inline = Signal(object, list, str)  # ctx, paths, prompt
    status = Signal(object)                      # message
    error = Signal(object)                       # exception


class MusicWorker(QRunnable):
    """
    Worker that calls the Vertex AI Lyria REST API (predict) to generate audio,
    then saves to disk. Transcodes to MP3/MP4 if ffmpeg is available and requested.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = MusicSignals()
        self.window = None
        self.client: Optional[genai.Client] = None
        self.ctx: Optional[CtxItem] = None

        # inputs
        self.model: str = "lyria-002"
        self.input_prompt: str = ""
        self.negative_prompt: Optional[str] = None
        self.num: int = 1
        self.seed: Optional[int] = None
        self.out_format: str = "mp3"  # wav | mp3 | mp4

        # prompt improvement
        self.model_prompt = None
        self.system_prompt = ""
        self.raw = False

        # ui
        self.inline: bool = False

    @Slot()
    def run(self):
        try:
            # Validate Vertex configuration first
            if not self._using_vertex():
                raise RuntimeError(
                    "Vertex AI is required for music (Lyria). Enable Vertex in settings and configure credentials."
                )

            # Optional prompt enhancement via LLM
            if not self.raw and self.input_prompt:
                try:
                    self.signals.status.emit(trans('vid.status.prompt.wait'))
                    bridge_context = BridgeContext(
                        prompt=self.input_prompt,
                        system_prompt=self.system_prompt,
                        model=self.model_prompt,
                        max_tokens=200,
                        temperature=1.0,
                    )
                    ev = KernelEvent(KernelEvent.CALL, {'context': bridge_context, 'extra': {}})
                    self.window.dispatch(ev)
                    resp = ev.data.get('response')
                    if resp:
                        self.input_prompt = resp
                except Exception as e:
                    # non-fatal
                    self.signals.error.emit(e)
                    self.signals.status.emit(trans('vid.status.prompt.error') + ": " + str(e))

            # Build request
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
            model_id = self._normalize_model_id(self.model)

            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model_id}:predict"
            token = self._get_access_token()

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # sample_count vs seed (mutually exclusive per Lyria API)
            instances: Dict[str, Any] = {
                "prompt": self.input_prompt,
            }
            if self.negative_prompt:
                instances["negative_prompt"] = self.negative_prompt

            params: Dict[str, Any] = {}
            if self.seed is not None and self.num > 1:
                # Keep API valid: if seed is set, do not set sample_count
                self.signals.status.emit("Seed provided; generating a single seeded sample (sample_count ignored).")
            if self.seed is not None:
                instances["seed"] = int(self.seed)
            elif self.num > 1:
                params["sample_count"] = int(self.num)

            body = {
                "instances": [instances],
                "parameters": params,
            }

            self.signals.status.emit(trans('vid.status.generating') + f": {self.input_prompt}...")

            # Call REST API
            resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=120)
            if resp.status_code != 200:
                raise RuntimeError(f"Lyria API error: {resp.status_code} {resp.text}")

            data = resp.json() or {}
            preds = data.get("predictions") or []
            if not preds:
                raise RuntimeError("No audio predictions returned.")

            # Decode and save each audio clip
            paths: List[str] = []
            for idx, p in enumerate(preds):
                # API returns base64-encoded WAV in audioContent
                b64 = p.get("audioContent") or ""
                mime = p.get("mimeType") or "audio/wav"
                if not b64:
                    continue
                wav_bytes = base64.b64decode(b64)

                saved_path = self._save(idx, wav_bytes, mime)
                if saved_path:
                    paths.append(saved_path)

            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.input_prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.input_prompt)

        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self._cleanup()

    # ---------- helpers ----------

    def _using_vertex(self) -> bool:
        """Check if Vertex AI is active via env variable set by ApiGoogle.setup_env()."""
        val = os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or ""
        return str(val).lower() in ("1", "true", "yes", "y")

    def _normalize_model_id(self, model_id: str) -> str:
        """
        Normalize model id to the publisher form 'lyria-002'.
        Accepts inputs like 'lyria-002', 'models/lyria-002', or full resource names.
        """
        if not model_id:
            return "lyria-002"
        # get trailing token after '/'
        tail = model_id.split("/")[-1]
        if tail.startswith("lyria"):
            return tail
        # fallback
        return "lyria-002"

    def _get_access_token(self) -> str:
        """
        Obtain OAuth2 access token for Vertex AI (cloud-platform scope) using ADC.
        """
        try:
            import google.auth
            from google.auth.transport.requests import Request as GRequest
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            creds.refresh(GRequest())
            return creds.token
        except Exception as e:
            # As a fallback, allow passing a pre-fetched token via env var.
            token = os.getenv("VERTEX_AI_TOKEN") or os.getenv("GCP_ACCESS_TOKEN") or ""
            if token:
                return token
            raise e

    def _save(self, idx: int, wav_bytes: bytes, mime: str) -> Optional[str]:
        """
        Save audio to disk. Primary save as WAV; then optionally transcode to MP3/MP4 if requested.
        """
        # Build base filename
        safe = self.window.core.video.make_safe_filename(self.input_prompt)
        base_name = (
            datetime.date.today().strftime("%Y-%m-%d") + "_" +
            datetime.datetime.now().strftime("%H-%M-%S") + "-" +
            safe + "-" + str(idx + 1)
        )

        # Directories: prefer 'audio' user dir if available, else fallback to 'video'
        try:
            out_dir = self.window.core.config.get_user_dir("audio")
        except Exception:
            out_dir = self.window.core.config.get_user_dir("video")

        os.makedirs(out_dir, exist_ok=True)

        # Always persist a WAV first (what API returns)
        wav_path = os.path.join(out_dir, base_name + ".wav")
        self.signals.status.emit(trans('vid.status.downloading') + f" ({idx + 1} / {max(1, self.num)}) -> {wav_path}")
        with open(wav_path, "wb") as f:
            f.write(wav_bytes)

        # Transcode if needed
        fmt = (self.out_format or "mp3").lower()
        if fmt == "wav":
            return wav_path

        ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if not ffmpeg:
            # No ffmpeg -> keep WAV
            self.signals.status.emit("ffmpeg not found. Saved WAV output only.")
            return wav_path

        if fmt == "mp3":
            out_path = os.path.join(out_dir, base_name + ".mp3")
            cmd = [ffmpeg, "-y", "-i", wav_path, "-vn", "-codec:a", "libmp3lame", "-b:a", "192k", out_path]
        elif fmt == "mp4":
            out_path = os.path.join(out_dir, base_name + ".mp4")
            # audio-only MP4 (AAC)
            cmd = [ffmpeg, "-y", "-i", wav_path, "-vn", "-c:a", "aac", "-b:a", "192k", out_path]
        else:
            # Unknown format -> keep WAV
            return wav_path

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return out_path
        except Exception:
            # If transcoding fails, keep WAV
            return wav_path

    def _cleanup(self):
        """Cleanup signals object."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass