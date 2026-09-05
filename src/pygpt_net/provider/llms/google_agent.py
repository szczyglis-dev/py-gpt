#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from pygpt_net.provider.llms.google_capture import PyGPTGoogleGenAI


class AgentGoogleGenAI(PyGPTGoogleGenAI):
    """Google GenAI adapter used by Agents v2.

    Shared PyGPTGoogleGenAI handles provider-native tool merging, Gemini's
    built-in/function-tool context flag and grounding URL capture. Keeping the
    agent subclass separate leaves a clean extension point for agent-only
    behavior without duplicating provider plumbing.
    """

    pass
