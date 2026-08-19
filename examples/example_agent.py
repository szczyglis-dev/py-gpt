#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT custom-agent provider tutorial               #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

from typing import Any, Dict

from pygpt_net.provider.agents.openai.agent import Agent as OpenAIAgentBase


class ExampleAgent(OpenAIAgentBase):
    """Customize the built-in simple OpenAI Agents workflow.

    Subclassing an existing provider is the easiest safe starting point when the
    execution loop/tool handling is already what you need. For a completely new
    engine, inherit `pygpt_net.provider.agents.base.BaseAgent` and implement the
    current `get_agent()` and async `run()` contract yourself.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_agent"  # unique ID shown in agent type choices
        self.name = "Example custom agent"
        # `type` and `mode` are inherited from the built-in OpenAI agent so PyGPT
        # knows which agent mode/runtime should execute this provider.

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """Add one instruction, then let the built-in provider create the agent."""
        # Copy the dict instead of modifying shared caller state in place.
        kwargs = dict(kwargs or {})
        current_prompt = str(kwargs.get("system_prompt") or "").strip()
        tutorial_instruction = (
            "You are running through the ExampleAgent extension. "
            "Keep answers concise unless the user asks for detail."
        )
        kwargs["system_prompt"] = (
            f"{tutorial_instruction}\n\n{current_prompt}"
            if current_prompt
            else tutorial_instruction
        )
        return super().get_agent(window, kwargs)

    # `run()` is intentionally inherited. It already handles OpenAI Agents tool
    # setup, streaming, response IDs, experts/handoffs, Computer Use, and PyGPT's
    # Bridge/ConnectionContext integration. Override it only when you truly need
    # a different execution lifecycle.
