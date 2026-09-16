#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.16 14:10:00                  #
# ================================================== #

MODE_AGENT = "agent"
MODE_AGENT_LLAMA = "agent_llama"
MODE_AGENT_OPENAI = "agent_openai"
MODE_AGENT_V2 = "agent_v2"
MODE_ASSISTANT = "assistant"
MODE_AUDIO = "audio"
MODE_CHAT = "chat"
MODE_COMPLETION = "completion"
MODE_COMPUTER = "computer"
MODE_EXPERT = "expert"
MODE_IMAGE = "img"
MODE_LANGCHAIN = "langchain"
MODE_LLAMA_INDEX = "llama_index"
MODE_RESEARCH = "research"
MODE_VISION = "vision"

# virtual modes
MODE_LOOP_NEXT = "loop_next"

# Only workflow-oriented modes persist ctx_item_partial / ctx_item_partial_task.
# Other modes may still use the same objects transiently during a live tool loop,
# but their durable conversation format remains the plain ctx_item row.
CTX_PARTIAL_PERSIST_MODES = frozenset((MODE_AGENT_V2,))


def should_persist_ctx_partials(mode) -> bool:
    """Return True when partial/task rows belong to the durable mode format."""
    return str(mode or "") in CTX_PARTIAL_PERSIST_MODES

