# -*- coding: utf-8 -*-
from datetime import datetime, timezone


class RememberTool:
    """Save facts and memories to Firebase Firestore"""

    def __init__(self, firebase_client, user_id: str):
        self.firebase = firebase_client
        self.user_id = user_id

    async def execute(self, args: dict) -> dict:
        content = args.get("content", "")
        category = args.get("category", "fact")
        importance = float(args.get("importance", 0.5))
        tags = args.get("tags", [])

        if not content:
            return {"success": False, "error": "Content is required"}

        memory = {
            "content": content,
            "category": category,
            "importance": importance,
            "tags": tags,
            "source": "pygpt"
        }

        doc_id = self.firebase.save_memory(self.user_id, memory)

        return {
            "success": True,
            "message": f"Memory saved: '{content[:60]}...' [{category}]",
            "doc_id": doc_id,
            "importance": importance
        }
