# -*- coding: utf-8 -*-
from typing import List


class RecallTool:
    """Semantic memory retrieval with optional embeddings"""

    def __init__(self, firebase_client, user_id: str, embedding_model: str = "local"):
        self.firebase = firebase_client
        self.user_id = user_id
        self.embedding_model = embedding_model
        self.embedder = None
        self._init_embedder()

    def _init_embedder(self):
        if self.embedding_model == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                print("[MCP Memory] Local embedder loaded (all-MiniLM-L6-v2)", flush=True)
            except ImportError:
                print("[MCP Memory] sentence-transformers not installed. Falling back to keyword search.", flush=True)

    def _embed(self, text: str) -> List[float]:
        if self.embedder:
            return self.embedder.encode(text).tolist()
        return []

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _keyword_search(self, query: str, memories: list) -> list:
        query_words = set(query.lower().split())
        scored = []
        for mem in memories:
            content_words = set(mem.get("content", "").lower().split())
            tags = set(t.lower() for t in mem.get("tags", []))
            overlap = len(query_words & (content_words | tags))
            if overlap > 0:
                scored.append((overlap, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    async def execute(self, args: dict) -> dict:
        query = args.get("query", "")
        limit = int(args.get("limit", 5))
        category = args.get("category", None)
        min_importance = float(args.get("min_importance", 0.0))

        if not query:
            return {"success": False, "error": "Query is required"}

        # Get all memories from Firebase
        memories = self.firebase.get_memories(
            self.user_id, category=category, limit=100
        )

        # Filter by importance
        memories = [m for m in memories if m.get("importance", 0) >= min_importance]

        if not memories:
            return {
                "success": True,
                "query": query,
                "results": [],
                "message": "No memories found yet. I'll remember things as we talk."
            }

        # Semantic or keyword search
        if self.embedder:
            query_embedding = self._embed(query)
            scored = []
            for mem in memories:
                content = mem.get("content", "")
                if not mem.get("embedding"):
                    mem["embedding"] = self._embed(content)
                score = self._cosine_similarity(query_embedding, mem["embedding"])
                scored.append((score, mem))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [m for _, m in scored[:limit]]
        else:
            results = self._keyword_search(query, memories)[:limit]

        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "content": m.get("content"),
                    "category": m.get("category"),
                    "importance": m.get("importance"),
                    "tags": m.get("tags", []),
                    "created_at": str(m.get("created_at", ""))
                }
                for m in results
            ],
            "total_memories": len(memories),
            "search_type": "semantic" if self.embedder else "keyword"
        }
