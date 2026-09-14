#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    model_limit: int
    app_limit: int
    effective_limit: int
    reserve_tokens: int
    input_limit: int
    checkpoint_tokens: int
    target_tail_tokens: int

    @classmethod
    def build(cls, window, model):
        model_limit = int(getattr(model, "ctx", 0) or 0)
        app_limit = int(window.core.config.get("max_total_tokens") or 0)

        if model_limit > 0 and app_limit > 0:
            effective = min(model_limit, app_limit)
        else:
            effective = model_limit or app_limit

        if effective <= 0:
            return cls(model_limit, app_limit, 0, 0, 0, 0, 0)

        output_reserve = int(window.core.config.get("max_output_tokens") or 0)
        # ``0`` means provider/model default in PyGPT. Reserving zero tokens in
        # that case makes an otherwise safe history fit consume the entire
        # context window and leaves no room for the response. Keep a bounded
        # automatic reserve: proportional for normal windows, capped for very
        # large (hundreds-of-thousands / million-token) models.
        if output_reserve <= 0:
            output_reserve = min(32768, max(1024, int(effective * 0.08)))
        else:
            # Do not let an unusually high explicit output setting consume the
            # whole input budget. The provider may still lower it independently.
            output_reserve = min(output_reserve, max(0, int(effective * 0.35)))
        safety = max(
            int(window.core.config.get("context_threshold") or 0),
            int(effective * 0.03),
        )
        min_input = min(1024, effective)
        reserve = min(
            max(0, output_reserve + safety),
            max(0, effective - min_input),
        )
        input_limit = max(1, effective - reserve)

        threshold = int(window.core.config.get("context.advanced.threshold") or 75)
        target = int(window.core.config.get("context.advanced.target") or 45)
        threshold = min(95, max(20, threshold))
        target = min(threshold - 5, max(10, target))

        checkpoint_tokens = min(
            input_limit,
            max(1, max(min(1024, input_limit), int(input_limit * threshold / 100))),
        )
        target_tail_tokens = min(
            checkpoint_tokens,
            max(1, max(min(512, input_limit), int(input_limit * target / 100))),
        )

        return cls(
            model_limit=model_limit,
            app_limit=app_limit,
            effective_limit=effective,
            reserve_tokens=reserve,
            input_limit=input_limit,
            checkpoint_tokens=checkpoint_tokens,
            target_tail_tokens=target_tail_tokens,
        )
