"""MiniMax music generation support for the media-generation mode."""

import base64
import binascii
import datetime
import os
from typing import Any, Dict, Optional

import requests
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem


class Music:
    """Generate music with MiniMax's regional music_generation endpoints."""

    def __init__(self, window=None):
        self.window = window
        self.worker: Optional[MusicWorker] = None

    @staticmethod
    def is_music_model(model_id: str) -> bool:
        return str(model_id or "").lower() in {"music-3.0", "music-2.6", "music-cover"}

    def generate(self, context: BridgeContext, extra: Optional[Dict[str, Any]] = None,
                 sync: bool = True) -> bool:
        extra = extra or {}
        worker = MusicWorker()
        worker.window = self.window
        worker.ctx = context.ctx or CtxItem()
        worker.model = context.model.id if context.model else "music-3.0"
        worker.prompt = context.prompt or ""
        worker.lyrics = extra.get("lyrics")
        worker.output_format = str(extra.get("output_format") or extra.get("format") or "url").lower()
        worker.audio_setting = extra.get("audio_setting") or {}
        worker.audio_format = str(worker.audio_setting.get("format") or "mp3").lower()
        worker.request_options = {
            key: extra[key] for key in (
                "stream", "lyrics_optimizer", "is_instrumental", "audio_url",
                "audio_base64", "cover_feature_id", "aigc_watermark"
            ) if key in extra
        }
        worker.inline = bool(extra.get("inline", False))
        self.worker = worker
        worker.signals.finished.connect(self.window.core.video.handle_finished)
        worker.signals.finished_inline.connect(self.window.core.video.handle_finished_inline)
        worker.signals.status.connect(self.window.core.video.handle_status)
        worker.signals.error.connect(self.window.core.video.handle_error)
        if sync or not self.window.controller.kernel.async_allowed(worker.ctx):
            worker.run()
        else:
            self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {"id": "video"}))
            self.window.threadpool.start(worker)
        return True


class MusicSignals(QObject):
    finished = Signal(object, list, str)
    finished_inline = Signal(object, list, str)
    status = Signal(object)
    error = Signal(object)


class MusicWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = MusicSignals()
        self.window = None
        self.ctx = None
        self.model = "music-3.0"
        self.prompt = ""
        self.lyrics = None
        self.output_format = "url"
        self.audio_setting: Dict[str, Any] = {}
        self.audio_format = "mp3"
        self.request_options: Dict[str, Any] = {}
        self.inline = False

    @Slot()
    def run(self):
        try:
            cfg = self.window.core.config
            token = cfg.get("api_key_minimax") or os.environ.get("MINIMAX_API_KEY") or ""
            if not token:
                raise RuntimeError("MiniMax API key is not configured.")
            endpoint = (cfg.get("api_endpoint_minimax") or "https://api.minimax.io/v1").rstrip("/")
            body: Dict[str, Any] = {"model": self.model, "prompt": self.prompt,
                                    "output_format": self.output_format}
            if self.lyrics is not None:
                body["lyrics"] = self.lyrics
            if self.audio_setting:
                body["audio_setting"] = self.audio_setting
            body.update(self.request_options)
            self.signals.status.emit("Generating music...")
            response = requests.post(
                endpoint + "/music_generation",
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                json=body, timeout=180,
            )
            response.raise_for_status()
            payload = response.json() or {}
            if (payload.get("base_resp") or {}).get("status_code") != 0:
                raise RuntimeError("MiniMax music generation returned an error.")
            data = payload.get("data") or {}
            if data.get("status") == 1 and not data.get("audio"):
                raise RuntimeError("MiniMax music generation is still in progress.")
            audio = data.get("audio")
            if not audio:
                raise RuntimeError("MiniMax music generation returned no audio.")
            raw = self._decode_audio(audio)
            path = self._save(raw)
            paths = [path] if path else []
            if self.inline:
                self.signals.finished_inline.emit(self.ctx, paths, self.prompt)
            else:
                self.signals.finished.emit(self.ctx, paths, self.prompt)
        except Exception as exc:
            self.signals.error.emit(exc)

    @staticmethod
    def _decode_audio(audio: Any) -> bytes:
        if isinstance(audio, (bytes, bytearray)):
            return bytes(audio)
        value = str(audio)
        if value.startswith(("http://", "https://")):
            result = requests.get(value, timeout=120)
            result.raise_for_status()
            return result.content
        try:
            return binascii.unhexlify(value)
        except (binascii.Error, ValueError):
            return base64.b64decode(value)

    def _save(self, content: bytes) -> str:
        safe = self.window.core.video.make_safe_filename(self.prompt) or "music"
        extension = self.audio_format if self.audio_format in {"mp3", "wav", "pcm"} else "mp3"
        filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-") + safe + "." + extension
        try:
            directory = self.window.core.config.get_user_dir("audio")
        except Exception:
            directory = self.window.core.config.get_user_dir("video")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        with open(path, "wb") as output:
            output.write(content)
        return path
