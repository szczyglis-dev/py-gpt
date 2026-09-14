#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Internal ChatMessage metadata used only inside the bounded Agents v2 memory.
# It is stripped before provider calls.  We put it on the assistant message of a
# projected durable turn, so seeing it in a flushed batch means that whole source
# turn has crossed the rolling-memory boundary and may safely be represented by
# continuation notes on future runs.
SOURCE_ITEM_KWARG = "_pygpt_context_source_item_id"

# LlamaIndex BaseMemoryBlock.aput() injects this transport key when a session id
# is supplied. It is useful to the memory backend but should never consume
# continuation-summary budget.
MEMORY_TRANSPORT_KWARGS = {"session_id", SOURCE_ITEM_KWARG}
