from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.provider.web.base import BaseProvider
from pygpt_net.provider.web.duckduck_search import DuckDuckGoSearch
from pygpt_net.provider.web.google_custom_search import GoogleCustomSearch
from pygpt_net.provider.web.microsoft_bing import MicrosoftBingSearch


def plugin(options=None):
    options = options or {}
    p = MagicMock()
    p.get_option_value.side_effect = lambda key: options.get(key)
    return p


def test_base_provider_contract():
    p1 = plugin()
    base = BaseProvider(p1)
    assert base.plugin is p1
    assert base.id == "" and base.name == "" and base.type == []
    base.init_options = MagicMock()
    p2 = plugin()
    base.init(p2)
    assert base.plugin is p2
    base.init_options.assert_called_once_with()
    assert base.search("q") is None
    assert base.is_configured([]) is None
    assert base.get_config_message() == ""


def test_duckduckgo_init_options_registers_expected_settings():
    p = plugin()
    provider = DuckDuckGoSearch(plugin=p)
    provider.init_options()
    keys = [call.args[0] for call in p.add_option.call_args_list]
    assert keys == ["ddg_region", "ddg_safesearch", "ddg_timelimit", "ddg_backend"]


def test_duckduckgo_search_mocked_backend_limits_offsets_and_deduplicates():
    p = plugin({
        "ddg_region": "pl-pl",
        "ddg_safesearch": "OFF",
        "ddg_timelimit": "W",
        "ddg_backend": "LITE",
    })
    provider = DuckDuckGoSearch(plugin=p)
    ddgs = MagicMock()
    ddgs.__enter__.return_value.text.return_value = [
        {"href": "https://a"}, {"url": "https://b"}, {"href": "https://b"},
        {"href": "https://c"}, {"href": "https://d"},
    ]
    cls = MagicMock(return_value=ddgs)
    provider._load_ddgs = MagicMock(return_value=cls)

    assert provider.search("query", limit=3, offset=1) == ["https://b", "https://c"]
    ddgs.__enter__.return_value.text.assert_called_once_with(
        "query", region="pl-pl", safesearch="off", timelimit="w", backend="lite", max_results=4,
    )


def test_duckduckgo_search_handles_absent_backend_bad_limits_and_errors(capsys):
    provider = DuckDuckGoSearch(plugin=plugin())
    provider._load_ddgs = MagicMock(return_value=None)
    assert provider.search("q") == []
    assert "package not installed" in capsys.readouterr().out

    provider._load_ddgs = MagicMock(return_value=MagicMock(side_effect=RuntimeError("boom")))
    assert provider.search("q", limit=0) == []
    assert "boom" in capsys.readouterr().out
    assert provider.search("q", limit=10, offset=100) == []


def test_duckduckgo_configuration_and_message():
    provider = DuckDuckGoSearch(plugin=plugin())
    provider._load_ddgs = MagicMock(return_value=object())
    assert provider.is_configured([{"cmd": "other"}]) is True
    assert provider.is_configured([{"cmd": "web_search"}]) is True
    provider._load_ddgs.return_value = None
    assert provider.is_configured([{"cmd": "web_urls"}]) is False
    assert "DuckDuckGo provider requires" in provider.get_config_message()


def test_duckduckgo_dynamic_import_fallbacks_without_real_dependency():
    fake_primary = SimpleNamespace(DDGS="primary")
    fake_fallback = SimpleNamespace(DDGS="fallback")
    with patch.dict("sys.modules", {"duckduckgo_search": fake_primary}):
        assert DuckDuckGoSearch._load_ddgs() == "primary"
    with patch.dict("sys.modules", {"duckduckgo_search": None, "ddgs": fake_fallback}):
        assert DuckDuckGoSearch._load_ddgs() == "fallback"
    with patch.dict("sys.modules", {"duckduckgo_search": None, "ddgs": None}):
        assert DuckDuckGoSearch._load_ddgs() is None


def test_google_init_credentials_and_configuration():
    p = plugin({"google_api_key": "key", "google_api_cx": "cx"})
    provider = GoogleCustomSearch(plugin=p)
    provider.init_options()
    assert [c.args[0] for c in p.add_option.call_args_list] == ["google_api_key", "google_api_cx"]
    assert provider.get_key() == "key"
    assert provider.get_cx() == "cx"
    assert provider.is_configured([{"cmd": "web_search"}]) is True
    assert provider.is_configured([{"cmd": "other"}]) is True
    p.get_option_value.side_effect = lambda key: "" if key == "google_api_key" else "cx"
    assert provider.is_configured([{"cmd": "web_urls"}]) is False
    assert "Google Custom Search API key" in provider.get_config_message()


def test_google_search_mocks_http_helper_and_clamps_limit():
    p = plugin({"google_api_key": "key", "google_api_cx": "cx"})
    p.get_url.return_value = '{"items":[{"link":"https://a"},{"link":"https://b"}]}'
    provider = GoogleCustomSearch(plugin=p)
    assert provider.search("a b", limit=99, offset=2) == ["https://a", "https://b"]
    called_url = p.get_url.call_args.args[0]
    assert "num=10" in called_url and "start=2" in called_url and "q=a%20b" in called_url

    p.get_url.return_value = "not-json"
    assert provider.search("q") == []
    p.get_url.return_value = "{}"
    assert provider.search("q") == []


def test_bing_init_credentials_configuration_and_search_are_network_mocked():
    p = plugin({"bing_api_key": "key", "bing_endpoint": "https://bing.invalid/search"})
    provider = MicrosoftBingSearch(plugin=p)
    provider.init_options()
    assert [c.args[0] for c in p.add_option.call_args_list] == ["bing_api_key", "bing_endpoint"]
    assert provider.get_key() == "key"
    assert provider.is_configured([{"cmd": "web_search"}]) is True
    assert provider.is_configured([{"cmd": "other"}]) is True

    response = MagicMock(status_code=200)
    response.json.return_value = {"webPages": {"value": [{"url": "https://a"}, {"url": "https://b"}]}}
    with patch("pygpt_net.provider.web.microsoft_bing.requests.get", return_value=response) as get:
        assert provider.search("a b", limit=99, offset=3) == ["https://a", "https://b"]
    url = get.call_args.args[0]
    assert "q=a%20b" in url and "count=10" in url and "offset=3" in url
    assert get.call_args.kwargs["headers"] == {"Ocp-Apim-Subscription-Key": "key"}


def test_bing_search_error_response_and_missing_key(capsys):
    p = plugin({"bing_api_key": "", "bing_endpoint": "https://bing.invalid"})
    provider = MicrosoftBingSearch(plugin=p)
    assert provider.is_configured([{"cmd": "web_urls"}]) is False
    assert "Microsoft Bing Search API key" in provider.get_config_message()
    response = MagicMock(status_code=500, text="error")
    with patch("pygpt_net.provider.web.microsoft_bing.requests.get", return_value=response):
        assert provider.search("q", limit=0) == []
    assert "500" in capsys.readouterr().out
