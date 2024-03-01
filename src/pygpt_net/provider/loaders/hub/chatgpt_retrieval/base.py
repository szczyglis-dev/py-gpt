"""
ChatGPT Plugin.

Based on: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-chatgpt-plugin/llama_index/readers/chatgpt_plugin/base.py
"""

import os
from typing import Any, List, Optional

import requests
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from requests.adapters import HTTPAdapter, Retry


class ChatGPTRetrievalPluginReader(BaseReader):
    """ChatGPT Retrieval Plugin reader."""

    def __init__(
        self,
        endpoint_url: str,
        bearer_token: Optional[str] = None,
        retries: Optional[Retry] = None,
        batch_size: int = 100,
    ) -> None:
        """Chatgpt Retrieval Plugin."""
        self._endpoint_url = endpoint_url
        self._bearer_token = bearer_token
        self._retries = retries
        self._batch_size = batch_size
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize the reader."""
        self._s = requests.Session()
        self._s.mount("http://", HTTPAdapter(max_retries=self._retries))

    def load_data(
        self,
        query: str,
        top_k: int = 10,
        separate_documents: bool = True,
        **kwargs: Any,
    ) -> List[Document]:
        """Load data from ChatGPT Retrieval Plugin."""
        if not self._initialized:
            self._initialize()
            self._initialized = True
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        queries = [{"query": query, "top_k": top_k}]
        res = requests.post(
            f"{self._endpoint_url}/query", headers=headers, json={"queries": queries}
        )
        documents: List[Document] = []
        for query_result in res.json()["results"]:
            for result in query_result["results"]:
                result_id = result["id"]
                result_txt = result["text"]
                result_embedding = result["embedding"]
                document = Document(
                    text=result_txt,
                    id_=result_id,
                    embedding=result_embedding,
                )
                documents.append(document)

            # NOTE: there should only be one query
            break

        if not separate_documents:
            text_list = [doc.get_content() for doc in documents]
            text = "\n\n".join(text_list)
            documents = [Document(text=text)]

        return documents