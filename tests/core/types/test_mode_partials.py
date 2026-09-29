from pygpt_net.core.types.mode import (
    CTX_PARTIAL_PERSIST_MODES,
    MODE_AGENT_V2,
    MODE_CHAT,
    should_persist_ctx_partials,
)


def test_mode_partials_persist_only_for_agents_v2():
    assert CTX_PARTIAL_PERSIST_MODES == frozenset((MODE_AGENT_V2,))
    assert should_persist_ctx_partials(MODE_AGENT_V2) is True
    assert should_persist_ctx_partials(MODE_CHAT) is False
    assert should_persist_ctx_partials(None) is False
    assert should_persist_ctx_partials("") is False
