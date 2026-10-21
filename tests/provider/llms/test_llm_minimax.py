"""MiniMax catalog, compatibility and serialized Chat Completions requests."""
import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import openai
from packaging.version import Version

from pygpt_net.controller.model.importer import Importer
from pygpt_net.core.models.models import Models
from pygpt_net.core.types.reasoning import get_model_efforts
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.api.openai import ApiOpenAI
from pygpt_net.provider.api.openai.chat import Chat
from pygpt_net.provider.core.config.patches.patch_before_2_8_33 import Patch, rewrite_placeholders
from pygpt_net.provider.llms.minimax import MiniMaxLLM
from pygpt_net.provider.llms.open_router.provider import OpenRouterLLM


class TestMiniMax(unittest.TestCase):
    def setUp(self):
        self.window = MagicMock()
        self.window.controller.chat.remote_tools.enabled.return_value = False
        self.values = {"max_total_tokens": 1000000, "use_context": False}
        self.provider_values = {"api_key": "fixture-key", "api_base": "https://api.minimax.io/v1"}
        cfg = self.window.core.config
        cfg.get.side_effect = lambda key, default=None: self.values.get(key, default)
        cfg.has.return_value = False
        cfg.get_provider.side_effect = lambda provider, key, default=None: self.provider_values.get(key, default)
        self.provider = MiniMaxLLM().bind(self.window)
        self.window.core.llm.get.side_effect = lambda name: self.provider if name == "minimax" else None
        self.window.core.llm.is_custom_provider.return_value = False
        self.models = Models(self.window)
        self.window.core.models = self.models
        self.api = ApiOpenAI(self.window)
        self.window.core.api.openai = self.api
        self.api.vision = MagicMock()
        self.api.vision.build_content.side_effect = lambda content, attachments: content
        self.api.tools = MagicMock()
        self.api.tools.prepare.return_value = []
        self.window.core.tokens.from_messages.return_value = 10
        self.window.core.tokens.from_user.return_value = 5
        self.window.core.attachments.native.get_refs.return_value = []
        root = Path(__file__).resolve().parents[3]
        self.catalog = json.loads((root / "src/pygpt_net/data/config/models.json").read_text())["items"]

    def model(self, model_id="MiniMax-M3.1-Flash"):
        model = ModelItem(model_id)
        if model_id in self.catalog:
            model.from_dict(self.catalog[model_id])
        else:
            model.name = model_id
            model.provider = "minimax"
            model.ctx = 1000000
        return model

    def send(self, model, stream=False):
        requests = []

        def transport(request):
            payload = json.loads(request.content)
            requests.append((request, payload))
            response = {"id": "fixture", "object": "chat.completion", "created": 0,
                        "model": payload["model"], "choices": [
                            {"index": 0, "message": {"role": "assistant", "content": "ok"},
                             "finish_reason": "stop"}]}
            if stream:
                return httpx.Response(200, text="data: [DONE]\n\n", headers={"content-type": "text/event-stream"})
            return httpx.Response(200, json=response)

        # Keep client creation and SDK serialization real; replace only HTTP I/O.
        real_client = openai.OpenAI
        with httpx.Client(transport=httpx.MockTransport(transport)) as http_client:
            with patch("openai.OpenAI", side_effect=lambda **args: real_client(**args, http_client=http_client)):
                context = SimpleNamespace(
                    prompt="hello", stream=stream, max_tokens=100, system_prompt="system",
                    mode="chat", model=model, external_functions=[], attachments={},
                    multimodal_ctx=None, history=[],
                    ctx=SimpleNamespace(input_name="user", output_name="assistant"),
                )
                response = Chat(self.window).send(context)
                if stream:
                    list(response)
        self.assertEqual(len(requests), 1)
        return requests[0]

    def test_catalog_and_importer(self):
        ids = [item["id"] for item in self.provider.get_models(self.window)]
        self.assertEqual(ids, ["MiniMax-M3.1-Flash", "MiniMax-M3"])
        self.assertEqual([key for key, value in self.catalog.items() if value["provider"] == "minimax"], ids)
        self.assertEqual(self.model().ctx, 1000000)
        self.assertEqual(self.model().tokens, 524288)
        self.assertTrue(self.provider.is_openai_compatible())
        self.window.core.llm.get_provider_name.return_value = "MiniMax"
        importer = Importer(self.window)
        importer.provider = "minimax"
        imported = importer.get_available()
        self.assertEqual(list(imported), ids)
        self.assertEqual(imported[ids[0]].ctx, 1000000)
        self.assertEqual(imported[ids[0]].tokens, 524288)
        self.assertTrue(imported[ids[0]].reasoning_effort)
        self.assertTrue(imported[ids[1]].tool_calls)
        self.assertNotIn("completion", imported[ids[0]].mode)

    def test_order_and_saved_models(self):
        other = self.model("unrelated")
        other.provider = "other"
        legacy = self.model("MiniMax-M2.7")
        self.models.items = {item.id: item for item in (other, self.model("MiniMax-M3"), legacy, self.model())}
        self.models.sort_items()
        keys = list(self.models.items)
        self.assertLess(keys.index("MiniMax-M3.1-Flash"), keys.index("MiniMax-M3"))
        self.assertIs(self.models.get("MiniMax-M2.7"), legacy)
        self.assertEqual(self.models.resolve_model_key("chat", legacy.id), legacy.id)
        self.assertIs(self.models.get("unrelated"), other)

    def test_default_and_regions(self):
        for endpoint in ("https://api.minimax.io/v1", "https://api.minimaxi.com/v1"):
            with self.subTest(endpoint=endpoint):
                self.provider_values["api_base"] = endpoint
                request, body = self.send(self.model())
                self.assertEqual(str(request.url), endpoint + "/chat/completions")
                self.assertEqual(body["model"], "MiniMax-M3.1-Flash")
                self.assertNotIn("service_tier", body)
                self.assertNotIn("reasoning_split", body)
                self.assertNotIn("thinking", body)
                self.assertIn(body["reasoning_effort"], get_model_efforts(self.model()))
                self.assertEqual(body["messages"][-1]["content"], "hello")

    def test_flash_efforts_and_stream(self):
        for effort in ("low", "medium", "high", "xhigh", "max", "none"):
            with self.subTest(effort=effort):
                self.values["model.reasoning_effort"] = effort
                _, body = self.send(self.model(), stream=True)
                self.assertNotEqual(body.get("reasoning_effort"), "none")
                if effort != "none":
                    self.assertEqual(body["reasoning_effort"], effort)
                self.assertTrue(body["stream"])
        self.assertNotIn("none", get_model_efforts(self.model()))

    def test_m3_legacy_and_custom_ids(self):
        for model_id in ("MiniMax-M3", "MiniMax-M2.7", "my-custom-model"):
            with self.subTest(model=model_id):
                model = self.model(model_id)
                model.custom_api_endpoint = "https://custom.example/v1"
                model.custom_api_key = "custom-fixture"
                request, body = self.send(model)
                self.assertEqual(body["model"], model_id)
                self.assertEqual(str(request.url), "https://custom.example/v1/chat/completions")
                self.assertEqual(request.headers["authorization"], "Bearer custom-fixture")
                self.assertNotIn("reasoning_effort", body)

    def test_multimodal_and_tools(self):
        content = [{"type": "text", "text": "describe"},
                   {"type": "image_url", "image_url": {"url": "https://example.test/image.png"}}]
        tools = [{"type": "function", "function": {"name": "lookup", "parameters": {"type": "object"}}}]
        self.api.vision.build_content.return_value = content
        self.api.vision.build_content.side_effect = None
        self.api.tools.prepare.return_value = tools
        _, body = self.send(self.model())
        self.assertEqual(body["messages"][-1]["content"], content)
        self.assertEqual(body["tools"], tools)

    def test_openrouter_discovery_and_saved_request(self):
        provider = OpenRouterLLM().bind(self.window)
        self.window.core.llm.get.side_effect = lambda name: provider if name == "open_router" else self.provider
        self.provider_values["api_base"] = "https://openrouter.ai/api/v1"
        ids = ["minimax/minimax-m2.7", "minimax/minimax-m3", "minimax/minimax-m3.1-flash:free",
               "other/model", "minimax/speech-02", "minimax/minimax-music"]
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
            "data": [{"id": model_id, "object": "model", "created": 0, "owned_by": "fixture"}
                     for model_id in ids], "object": "list"}))
        real_client = openai.OpenAI
        with httpx.Client(transport=transport) as client:
            with patch("openai.OpenAI", side_effect=lambda **args: real_client(**args, http_client=client)):
                models = provider.get_models(self.window)
        self.assertEqual([model["id"] for model in models], ids[1:])
        for model_id in ids[:4]:
            with self.subTest(model=model_id):
                model = self.model(model_id)
                model.provider = "open_router"
                request, body = self.send(model)
                self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/chat/completions")
                self.assertEqual(body["model"], model_id)
                self.assertNotIn("reasoning_effort", body)

    def test_legacy_settings_migration(self):
        data = {"__meta__": {"version": "2.8.0"}, "api_key_minimax": "old-fixture-key",
                "api_endpoint_minimax": "https://custom.example/v1", "model": "MiniMax-M2.7",
                "prompt": "Keep {api_key_minimax}",
                "providers": {"minimax": {"api_key": "new-fixture-key"}}}
        self.window.core.config.all.return_value = copy.deepcopy(data)
        migrated, updated, _ = Patch(self.window).execute(Version("2.9.1"))
        self.assertTrue(updated)
        self.assertEqual(migrated["providers"]["minimax"], {
            "api_key": "new-fixture-key", "api_base": "https://custom.example/v1"})
        self.assertEqual(migrated["model"], "MiniMax-M2.7")
        self.assertEqual(migrated["prompt"], data["prompt"])
        self.assertEqual(rewrite_placeholders("{api_key_minimax}"), "{providers[minimax][api_key]}")


if __name__ == "__main__":
    unittest.main()
