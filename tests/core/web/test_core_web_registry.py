from types import SimpleNamespace

from pygpt_net.core.web.web import Web


def test_web_registry_registers_provider_for_supported_types_only():
    web = Web(window=None)
    provider = SimpleNamespace(id="search", type=[Web.PROVIDER_SEARCH_ENGINE, "unsupported"])
    web.register(provider)
    assert web.is_registered("search") is True
    assert web.get("search") is provider
    assert web.get_ids() == ["search"]
    assert web.get_providers() == {"search": provider}
    assert web.is_registered("search", "unsupported") is False
    assert web.get("missing") is None
    assert web.get_ids("missing") == []
    assert web.get_providers("missing") == {}
