"""Stable identities for legacy LlamaIndex role memories within a conversation."""
import json
from copy import deepcopy
from llama_index.core.memory import ChatMemoryBuffer


class WorkflowMemory(ChatMemoryBuffer):
    """Live memory resource, shared across state-store snapshots.

    Recent workflows versions deep-copy values on state-store reads/writes.
    Native agents mutate the retrieved memory without storing it back, so a
    regular in-memory ChatMemoryBuffer silently loses those mutations. Memory
    is deliberately reference-stable, like the DB-backed Memory implementation,
    but does not carry an async database connection across worker event loops.
    """
    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return self


def memory_namespace(provider, context):
    preset = getattr(context, 'preset', None)
    preset_id = (getattr(preset, 'uuid', None) or getattr(preset, 'filename', None) or '')
    provider_id = provider.custom_id or provider.id
    return json.dumps(['llama', provider_id, str(preset_id)], ensure_ascii=False)


def session_value(window, provider, context, key, factory):
    item = getattr(context, 'ctx', None)
    meta = getattr(item, 'meta', None)
    if meta is None:
        return factory()
    return window.core.agents.get_session_memory(
        meta, memory_namespace(provider, context), key, factory)


def role_memory(window, provider, context, key, *, history=None, token_limit=40000):
    # ChatMemoryBuffer keeps native ChatMessage/tool blocks and has no async DB
    # connections tied to the event loop of a previous asyncio.run() worker.
    return session_value(window, provider, context, key, lambda: WorkflowMemory.from_defaults(
        chat_history=deepcopy(list(history or [])), token_limit=token_limit))
