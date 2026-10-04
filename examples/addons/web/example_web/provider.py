"""Runnable web-search provider using the public MediaWiki OpenSearch API."""

import json
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from pygpt_net.provider.web.base import BaseProvider


class ExampleWeb(BaseProvider):
    def __init__(self):
        super().__init__()
        self.id = "example_web"
        self.name = "Example Wikipedia search"
        self.type = ["search_engine"]

    def init_options(self):
        self.plugin.add_option(
            "example_wiki_language",
            type="text",
            value="en",
            label="Wikipedia language",
            description="MediaWiki language subdomain, for example en or pl.",
            tab=self.id,
        )

    def search(self, query, limit=10, offset=0):
        limit = max(1, min(int(limit or 10), 10))
        offset = max(0, int(offset or 0))
        language = str(self.plugin.get_option_value("example_wiki_language") or "en").strip() or "en"
        params = urlencode(
            {
                "action": "opensearch",
                "search": str(query),
                "limit": limit + offset,
                "namespace": 0,
                "format": "json",
            }
        )
        url = f"https://{language}.wikipedia.org/w/api.php?{params}"
        request = Request(url, headers={"User-Agent": "PyGPT external add-on example"})
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

        urls = list(payload[3]) if isinstance(payload, list) and len(payload) > 3 else []
        return urls[offset:offset + limit]

    def is_configured(self, cmds):
        return True
