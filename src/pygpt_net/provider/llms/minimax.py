from typing import Optional, Dict, List

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class MiniMaxLLM(BaseLLM):
    """MiniMax text provider used alongside media models."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "minimax"
        self.name = "MiniMax"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def llama(self, window, model: ModelItem, stream: bool = False) -> LlamaBaseLLM:
        from llama_index.llms.openai_like import OpenAILike
        args = self.parse_args(model.llama_index, window)
        args.setdefault("model", model.id)
        args.setdefault("api_key", window.core.config.get("api_key_minimax", ""))
        args.setdefault("api_base", window.core.config.get("api_endpoint_minimax", ""))
        args.setdefault("is_chat_model", True)
        args.setdefault("is_function_calling_model", model.tool_calls)
        return OpenAILike(**self.inject_llamaindex_http_clients(args, window.core.config))

    def get_embeddings_model(self, window, config: Optional[List[Dict]] = None) -> BaseEmbedding:
        from llama_index.embeddings.openai_like import OpenAILikeEmbedding
        args = self.parse_args({"args": config or []}, window)
        args.setdefault("api_key", window.core.config.get("api_key_minimax", ""))
        args.setdefault("api_base", window.core.config.get("api_endpoint_minimax", ""))
        return OpenAILikeEmbedding(**self.inject_llamaindex_http_clients(args, window.core.config))
