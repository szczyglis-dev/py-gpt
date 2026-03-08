# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta


class SummarizeTool:
    """Summarize recent conversations on a topic"""

    def __init__(self, firebase_client, user_id: str):
        self.firebase = firebase_client
        self.user_id = user_id

    async def execute(self, args: dict) -> dict:
        topic = args.get("topic", "")
        days_back = int(args.get("days_back", 7))

        if not topic:
            return {"success": False, "error": "Topic is required"}

        conversations = self.firebase.get_recent_conversations(self.user_id, limit=50)

        # Filter by date
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        recent = []
        for conv in conversations:
            ts = conv.get("timestamp")
            if ts and hasattr(ts, "replace"):
                if ts.replace(tzinfo=timezone.utc) >= cutoff:
                    recent.append(conv)

        # Filter by topic keywords
        topic_lower = topic.lower()
        relevant = [
            c for c in recent
            if topic_lower in c.get("content", "").lower()
            or topic_lower in c.get("title", "").lower()
            or any(topic_lower in t.lower() for t in c.get("tags", []))
        ]

        if not relevant:
            return {
                "success": True,
                "topic": topic,
                "summary": f"No recent conversations about '{topic}' found in the last {days_back} days.",
                "count": 0
            }

        snippets = [c.get("content", "")[:150] for c in relevant[:5]]
        summary = f"Found {len(relevant)} conversations about '{topic}' in the last {days_back} days:\n"
        summary += "\n".join(f"- {s}..." for s in snippets)

        return {
            "success": True,
            "topic": topic,
            "summary": summary,
            "count": len(relevant),
            "days_back": days_back
        }
