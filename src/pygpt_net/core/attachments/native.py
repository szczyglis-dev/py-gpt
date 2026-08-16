#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.16 19:20:00                  #
# ================================================== #

import mimetypes
import os
from typing import Optional, Dict, Any, Iterable

from pygpt_net.core.types import MODE_CHAT, MODE_COMPUTER, MODE_RESEARCH
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.model import ModelItem


class Native:
    """Provider-native attachment upload helpers."""

    DIRECT_MODES = {MODE_CHAT, MODE_RESEARCH, MODE_COMPUTER}

    OPENAI_EXTENSIONS = {
        ".pdf",
        ".xla", ".xlb", ".xlc", ".xlm", ".xls", ".xlsx", ".xlt", ".xlw",
        ".csv", ".tsv", ".iif",
        ".doc", ".docx", ".dot", ".odt", ".rtf",
        ".pot", ".ppa", ".pps", ".ppt", ".pptx", ".pwz", ".wiz",
        ".asm", ".bat", ".c", ".cc", ".conf", ".cpp", ".css", ".cxx", ".def", ".dic",
        ".eml", ".h", ".hh", ".htm", ".html", ".ics", ".ifb", ".in", ".js", ".json",
        ".ksh", ".list", ".log", ".markdown", ".md", ".mht", ".mhtml", ".mime", ".mjs",
        ".nws", ".pl", ".py", ".rst", ".s", ".sql", ".srt", ".text", ".txt", ".vcf",
        ".vtt", ".xml",
        # Additional code/text extensions accepted through documented text/code MIME types.
        ".jsx", ".ts", ".tsx", ".java", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
        ".swift", ".kt", ".kts", ".sh", ".bash", ".zsh", ".ps1", ".yaml", ".yml",
        ".toml", ".ini", ".cfg",
    }
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".csv", ".tsv", ".json", ".html", ".htm", ".xml", ".css", ".rtf",
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts", ".sh", ".bash", ".zsh",
        ".ps1", ".sql", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log",
    }
    GOOGLE_MIMES = {
        "text/html", "text/css", "text/plain", "text/xml", "text/csv", "text/rtf", "text/javascript",
        "application/json", "application/pdf",
    }
    OPENAI_REQUEST_LIMIT = 50 * 1024 * 1024
    XAI_FILE_LIMIT = 48 * 1024 * 1024
    ANTHROPIC_FILE_LIMIT = 500 * 1024 * 1024
    GOOGLE_FILE_LIMIT = 2 * 1024 * 1024 * 1024
    GOOGLE_PDF_LIMIT = 50 * 1024 * 1024

    def __init__(self, window=None):
        self.window = window
        self._used_bytes = {}

    def reset(self):
        """Reset per-request native upload counters."""
        self._used_bytes = {}

    def is_preferred(self) -> bool:
        """Return whether native file upload preference is enabled."""
        return bool(self.window.core.config.get("ctx.attachment.native_upload", False))

    def get_model(self) -> Optional[ModelItem]:
        """Return currently selected model."""
        key = self.window.core.config.get("model")
        if not key:
            return None
        try:
            return self.window.core.models.get(key)
        except Exception:
            return None

    def get_provider(self, mode: str, model: Optional[ModelItem] = None) -> Optional[str]:
        """Return provider name when the current route can consume native file references."""
        if not self.is_preferred() or mode not in self.DIRECT_MODES:
            return None
        model = model or self.get_model()
        if model is None:
            return None
        provider = str(model.provider or "")
        cfg = self.window.core.config
        if provider == "openai":
            return provider
        if provider == "google" and cfg.get("api_native_google", False):
            # Gemini File API upload is used here. Vertex AI uses a different file/GCS flow.
            if cfg.get("api_native_google.use_vertex", False):
                return None
            return provider
        if provider == "anthropic" and cfg.get("api_native_anthropic", False):
            return provider
        if provider == "x_ai" and cfg.get("api_native_xai", False):
            model_id = str(model.id or "").lower()
            if model_id.startswith("grok-4") and "imagine" not in model_id:
                return provider
        return None

    def can_upload(self, path: str, mode: str, model: Optional[ModelItem] = None) -> bool:
        """Check provider/model/file compatibility without reading file contents."""
        provider = self.get_provider(mode, model)
        if not provider or not path or not os.path.isfile(path):
            return False
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        if size <= 0:
            return False
        if not self._within_limits(provider, size):
            return False

        ext = os.path.splitext(path)[1].lower()
        mime = self._mime(path)
        if provider == "openai":
            if ext == ".pdf" and not self._model_has_image_input(model):
                return False
            return ext in self.OPENAI_EXTENSIONS
        if provider == "google":
            if ext == ".pdf" and size > self.GOOGLE_PDF_LIMIT:
                return False
            return ext == ".pdf" or ext in self.TEXT_EXTENSIONS or mime in self.GOOGLE_MIMES
        if provider == "anthropic":
            return ext == ".pdf" or ext in self.TEXT_EXTENSIONS
        if provider == "x_ai":
            return ext == ".pdf" or ext in self.TEXT_EXTENSIONS
        return False

    def upload(self, path: str, mode: str, model: Optional[ModelItem] = None) -> Dict[str, Any]:
        """Upload one file using the selected provider's native Files API."""
        model = model or self.get_model()
        provider = self.get_provider(mode, model)
        if not provider or not self.can_upload(path, mode, model):
            raise ValueError("Native file upload is not supported for this provider/model/file.")

        if provider == "openai":
            result = self._upload_openai(path, mode, model)
        elif provider == "google":
            result = self._upload_google(path, mode, model)
        elif provider == "anthropic":
            result = self._upload_anthropic(path, mode, model)
        elif provider == "x_ai":
            result = self._upload_xai(path, mode, model)
        else:
            raise ValueError(f"Unsupported native upload provider: {provider}")

        self._used_bytes[provider] = self._used_bytes.get(provider, 0) + os.path.getsize(path)
        return result

    def _within_limits(self, provider: str, size: int) -> bool:
        used = self._used_bytes.get(provider, 0)
        if provider == "openai":
            return size < self.OPENAI_REQUEST_LIMIT and used + size <= self.OPENAI_REQUEST_LIMIT
        if provider == "x_ai":
            return size <= self.XAI_FILE_LIMIT
        if provider == "anthropic":
            return size <= self.ANTHROPIC_FILE_LIMIT
        if provider == "google":
            return size <= self.GOOGLE_FILE_LIMIT
        return False

    def _upload_openai(self, path: str, mode: str, model: ModelItem) -> Dict[str, Any]:
        client = self.window.core.api.openai.get_client(mode, model)
        with open(path, "rb") as handle:
            uploaded = client.files.create(file=handle, purpose="user_data")
        return self._ref(
            provider="openai",
            file_id=str(uploaded.id),
            path=path,
            mime=self._mime(path),
        )

    def _upload_google(self, path: str, mode: str, model: ModelItem) -> Dict[str, Any]:
        client = self.window.core.api.google.get_client(mode, model)
        mime = self._google_mime(path)
        uploaded = client.files.upload(file=path, config={"mime_type": mime})
        uri = str(getattr(uploaded, "uri", "") or "")
        if not uri:
            raise RuntimeError("Gemini File API did not return a file URI.")
        mime = str(getattr(uploaded, "mime_type", "") or mime)
        ref = self._ref(
            provider="google",
            file_id=str(getattr(uploaded, "name", "") or ""),
            path=path,
            mime=mime,
        )
        ref["uri"] = uri
        return ref

    def _upload_anthropic(self, path: str, mode: str, model: ModelItem) -> Dict[str, Any]:
        client = self.window.core.api.anthropic.get_client(mode, model)
        ext = os.path.splitext(path)[1].lower()
        mime = "application/pdf" if ext == ".pdf" else "text/plain"
        with open(path, "rb") as handle:
            data = handle.read()
        file_part = (os.path.basename(path), data, mime)
        files_api = client.beta.files
        try:
            uploaded = files_api.upload(
                file=file_part,
                betas=["files-api-2025-04-14"],
            )
        except TypeError:
            # Newer SDKs apply the Files API beta header from the beta namespace.
            uploaded = files_api.upload(file=file_part)
        return self._ref(
            provider="anthropic",
            file_id=str(uploaded.id),
            path=path,
            mime=mime,
        )

    def _upload_xai(self, path: str, mode: str, model: ModelItem) -> Dict[str, Any]:
        client = self.window.core.api.xai.get_client(mode, model)
        try:
            uploaded = client.files.upload(path)
        except Exception:
            with open(path, "rb") as handle:
                data = handle.read()
            try:
                uploaded = client.files.upload(data, filename=os.path.basename(path))
            except Exception:
                with open(path, "rb") as handle:
                    uploaded = client.files.upload(handle, filename=os.path.basename(path))
        return self._ref(
            provider="x_ai",
            file_id=str(uploaded.id),
            path=path,
            mime=self._mime(path),
        )

    @staticmethod
    def _ref(provider: str, file_id: str, path: str, mime: str) -> Dict[str, Any]:
        return {
            "provider": provider,
            "id": file_id,
            "name": os.path.basename(path),
            "mime_type": mime,
            "size": os.path.getsize(path),
        }

    @staticmethod
    def _model_has_image_input(model: Optional[ModelItem]) -> bool:
        """Return whether model metadata declares vision/image input support."""
        if model is None:
            return False
        inputs = getattr(model, "input", None) or []
        modes = getattr(model, "mode", None) or []
        return "image" in inputs or "vision" in modes

    @staticmethod
    def _google_mime(path: str) -> str:
        """Return a Gemini document MIME, mapping generic text/code files to text/plain."""
        ext = os.path.splitext(path)[1].lower()
        mapping = {
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".csv": "text/csv",
            ".html": "text/html",
            ".htm": "text/html",
            ".css": "text/css",
            ".xml": "text/xml",
            ".rtf": "text/rtf",
            ".js": "text/javascript",
            ".mjs": "text/javascript",
        }
        if ext in mapping:
            return mapping[ext]
        if ext in Native.TEXT_EXTENSIONS:
            return "text/plain"
        return Native._mime(path)

    @staticmethod
    def _mime(path: str) -> str:
        mime, _ = mimetypes.guess_type(path)
        if mime:
            if mime == "application/javascript":
                return "text/javascript"
            return mime
        ext = os.path.splitext(path)[1].lower()
        if ext in Native.TEXT_EXTENSIONS:
            return "text/plain"
        return "application/octet-stream"

    def get_refs(
            self,
            attachments: Optional[Dict[str, AttachmentItem]],
            provider: str,
            include_meta: bool = True,
    ) -> Iterable[Dict[str, Any]]:
        """Return de-duplicated native references for the current request.

        Current in-memory attachment refs are always included. Persisted refs from
        the context metadata are included for stateless provider routes so an
        uploaded native file behaves like other context attachments on subsequent
        turns. Forced append-once disables persisted refs.
        """
        refs = []
        seen = set()

        def add(ref: Dict[str, Any]):
            if not isinstance(ref, dict) or ref.get("provider") != provider or not ref.get("id"):
                return
            key = (provider, str(ref.get("id")), str(ref.get("uri") or ""))
            if key in seen:
                return
            seen.add(key)
            refs.append(ref)

        if attachments:
            for attachment in attachments.values():
                extra = getattr(attachment, "extra", None)
                if not isinstance(extra, dict):
                    continue
                for ref in extra.get("native_files", []) or []:
                    add(ref)

        if include_meta and not self.window.core.config.get("ctx.attachment.append_once", False):
            try:
                meta = self.window.core.ctx.get_current_meta()
            except Exception:
                meta = None
            if meta is not None:
                for item in meta.get_additional_ctx():
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != "native_file" or item.get("native_provider") != provider:
                        continue
                    add({
                        "provider": provider,
                        "id": item.get("native_id"),
                        "uri": item.get("native_uri"),
                        "mime_type": item.get("native_mime_type"),
                        "name": item.get("context_name") or item.get("name"),
                        "size": item.get("size", 0),
                    })

        return refs
