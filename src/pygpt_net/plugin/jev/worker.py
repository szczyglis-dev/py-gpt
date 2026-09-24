#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 19:27:00                  #
# ================================================== #

import json
import os
import time
from typing import Any, Dict

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseSignals, BaseWorker


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    DEFAULT_BASE_URL = "https://api.typesafe.ai"
    DEFAULT_MODEL = "jev-latest"
    DEFAULT_TIMEOUT = 10
    MAX_RETRIES = 2
    RETRY_STATUS_CODES = {429, 529}

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__(*args, **kwargs)
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """Execute queued Jev commands."""
        try:
            responses = []
            for item in self.cmds or []:
                if self.is_stopped():
                    break
                try:
                    if item.get("cmd") != "jev_evaluate":
                        continue
                    response = self.cmd_jev_evaluate(item)
                    if response is not None:
                        responses.append(response)
                except Exception as e:
                    responses.append(self.make_response(item, self.throw_error(e)))

            if responses:
                self.reply_more(responses)
        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def cmd_jev_evaluate(self, item: dict) -> dict:
        """Evaluate structured state with TypeSafe AI Jev / System One."""
        params = item.get("params") or {}
        state = params.get("state")
        questions = params.get("questions")
        model = self._model()

        self._validate_state(state)
        self._validate_questions(questions)

        payload = {
            "state": state,
            "model": model,
            "questions": questions,
        }
        result = self._post(payload)
        return self.make_response(item, result)

    def _api_key(self) -> str:
        key = (
            os.environ.get("TYPESAFE_API_KEY")
            or self._config_value("api_key_jev")
            or ""
        )
        key = str(key).strip()
        if not key:
            raise RuntimeError(
                "Missing Jev API key. Configure it in Settings > API Keys > Jev "
                "or set TYPESAFE_API_KEY."
            )
        return key

    def _api_base(self) -> str:
        value = (
            os.environ.get("TYPESAFE_BASE_URL")
            or self._config_value("api_endpoint_jev")
            or self.DEFAULT_BASE_URL
        )
        return str(value).strip().rstrip("/")

    def _endpoint(self) -> str:
        base = self._api_base()
        if not base:
            base = self.DEFAULT_BASE_URL
        if base.endswith("/v1/systemone"):
            return base
        if base.endswith("/v1"):
            return f"{base}/systemone"
        return f"{base}/v1/systemone"

    def _model(self) -> str:
        value = None
        if self.plugin is not None:
            value = self.plugin.get_option_value("model")
        return str(value or self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL

    def _config_value(self, key: str):
        if self.window is None or getattr(self.window, "core", None) is None:
            return None
        config = getattr(self.window.core, "config", None)
        if config is None:
            return None
        return config.get(key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "pygpt-net-jev-plugin/1.0",
        }

    def _post(self, payload: dict) -> dict:
        url = self._endpoint()
        headers = self._headers()

        for attempt in range(self.MAX_RETRIES + 1):
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.DEFAULT_TIMEOUT,
            )

            if response.status_code in self.RETRY_STATUS_CODES and attempt < self.MAX_RETRIES:
                time.sleep(self._retry_delay(response, attempt))
                continue

            return self._parse_response(response)

        raise RuntimeError("Jev request failed after retries.")

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        retry_after_ms = response.headers.get("retry-after-ms")
        if retry_after_ms:
            try:
                return max(0.0, float(retry_after_ms) / 1000.0)
            except (TypeError, ValueError):
                pass

        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except (TypeError, ValueError):
                pass

        return 0.5 * (2 ** attempt)

    def _parse_response(self, response: requests.Response) -> dict:
        try:
            payload = response.json() if response.content else {}
        except ValueError:
            payload = response.text or ""

        if not 200 <= response.status_code < 300:
            if isinstance(payload, str):
                detail = payload.strip()[:2000] or "HTTP error"
            else:
                detail = json.dumps(payload, ensure_ascii=False)[:2000]
            raise RuntimeError(f"Jev API error {response.status_code}: {detail}")

        if not isinstance(payload, dict):
            raise RuntimeError("Jev API returned an unexpected non-object JSON response.")
        return payload

    @staticmethod
    def _validate_state(state: Any):
        if not isinstance(state, (dict, list, str)):
            raise ValueError("Param 'state' must be a JSON object, array, or string.")
        if isinstance(state, str) and not state.strip():
            raise ValueError("Param 'state' must not be empty.")

    @classmethod
    def _validate_questions(cls, questions: Any):
        if not isinstance(questions, dict) or not questions:
            raise ValueError("Param 'questions' must be a non-empty object keyed by question IDs.")

        for question_id, spec in questions.items():
            if not isinstance(question_id, str) or not question_id.strip():
                raise ValueError("Each Jev question ID must be a non-empty string.")
            if not isinstance(spec, dict):
                raise ValueError(f"Question '{question_id}' must be an object.")

            question_type = str(spec.get("type") or "").strip().lower()
            if question_type not in {"choice", "score", "noul"}:
                raise ValueError(
                    f"Question '{question_id}' has unsupported type '{question_type}'. "
                    "Expected 'choice', 'score', or 'noul'."
                )

            instructions = spec.get("instructions")
            if instructions is None or instructions == "" or instructions == [] or instructions == {}:
                raise ValueError(f"Question '{question_id}' requires non-empty 'instructions'.")

            criteria = spec.get("criteria")
            if question_type == "choice":
                if not isinstance(criteria, dict) or not 1 <= len(criteria) <= 255:
                    raise ValueError(
                        f"Choice question '{question_id}' requires criteria with 1-255 options."
                    )
            elif question_type == "score":
                if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
                    raise ValueError(
                        f"Score question '{question_id}' requires an ordered criteria array with 2-10 entries."
                    )
            elif criteria is not None:
                if not isinstance(criteria, dict):
                    raise ValueError(f"Noul question '{question_id}' criteria must be an object when provided.")
                invalid = set(criteria) - {"true", "false"}
                if invalid:
                    raise ValueError(
                        f"Noul question '{question_id}' criteria only supports 'true' and 'false' keys."
                    )
