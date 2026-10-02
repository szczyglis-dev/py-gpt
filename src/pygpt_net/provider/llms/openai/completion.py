#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 12:00:00                  #
# ================================================== #

"""OpenAICompletion transport adapter, independent of provider selection."""

from llama_index.llms.openai_like import OpenAILike
from pygpt_net.provider.core.model.compat import is_openai_reasoning_model_id


class OpenAICompletion(OpenAILike):
    """Normalize Chat Completions kwargs for OpenAI reasoning models."""

    @staticmethod
    def _is_reasoning_model(model_id: str) -> bool:
        return is_openai_reasoning_model_id(model_id)

    def _get_model_kwargs(self, **kwargs):
        params = super()._get_model_kwargs(**kwargs)
        if not self._is_reasoning_model(self.model):
            return params

        # Reasoning models do not share the classic sampling surface.
        # Keep Completion mode compatible with current Chat Completions
        # models and avoid parameters rejected by newer GPT/o-series IDs.
        for key in (
                "temperature",
                "top_p",
                "presence_penalty",
                "frequency_penalty",
                "stop",
        ):
            params.pop(key, None)

        if "max_tokens" in params:
            params.setdefault("max_completion_tokens", params["max_tokens"])
            params.pop("max_tokens", None)
        return params

