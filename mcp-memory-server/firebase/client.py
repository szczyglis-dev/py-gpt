# -*- coding: utf-8 -*-
"""
Firebase Firestore client wrapper.
Handles connection, CRUD and queries for memory storage.
"""
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class FirebaseClient:
    def __init__(self, project_id: str, credentials_path: str):
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.db = None
        self._connect()

    def _connect(self):
        if not FIREBASE_AVAILABLE:
            print("[MCP Memory] firebase-admin not installed. Run: pip install firebase-admin",
                  flush=True)
            return
        if not self.project_id or not self.credentials_path:
            print("[MCP Memory] Firebase credentials not configured.", flush=True)
            return
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.credentials_path)
                firebase_admin.initialize_app(cred, {"projectId": self.project_id})
            self.db = firestore.client()
            print(f"[MCP Memory] Connected to Firebase project: {self.project_id}", flush=True)
        except Exception as e:
            print(f"[MCP Memory] Firebase connection error: {e}", flush=True)

    def is_connected(self) -> bool:
        return self.db is not None

    # ---- Memory CRUD ----

    def save_memory(self, user_id: str, memory: Dict[str, Any]) -> str:
        """Save a memory document. Returns the document ID."""
        if not self.is_connected():
            return "offline"
        memory["created_at"] = datetime.now(timezone.utc)
        memory["updated_at"] = datetime.now(timezone.utc)
        ref = self.db.collection("users").document(user_id).collection("memory").add(memory)
        return ref[1].id

    def get_memories(self, user_id: str, category: Optional[str] = None,
                     limit: int = 20) -> List[Dict]:
        """Retrieve memories, optionally filtered by category."""
        if not self.is_connected():
            return []
        ref = self.db.collection("users").document(user_id).collection("memory")
        if category:
            ref = ref.where("category", "==", category)
        ref = ref.order_by("importance", direction=firestore.Query.DESCENDING).limit(limit)
        return [{"id": doc.id, **doc.to_dict()} for doc in ref.stream()]

    def search_memories_by_tag(self, user_id: str, tags: List[str]) -> List[Dict]:
        """Search memories by tags."""
        if not self.is_connected():
            return []
        ref = (self.db.collection("users").document(user_id)
               .collection("memory")
               .where("tags", "array_contains_any", tags)
               .limit(10))
        return [{"id": doc.id, **doc.to_dict()} for doc in ref.stream()]

    def save_conversation(self, user_id: str, conv: Dict[str, Any]) -> str:
        """Save a conversation summary."""
        if not self.is_connected():
            return "offline"
        conv["timestamp"] = datetime.now(timezone.utc)
        ref = (self.db.collection("users").document(user_id)
               .collection("conversations").add(conv))
        return ref[1].id

    def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get most recent conversations."""
        if not self.is_connected():
            return []
        ref = (self.db.collection("users").document(user_id)
               .collection("conversations")
               .order_by("timestamp", direction=firestore.Query.DESCENDING)
               .limit(limit))
        return [{"id": doc.id, **doc.to_dict()} for doc in ref.stream()]

    def update_device_sync(self, user_id: str, device_id: str, state: Dict) -> None:
        """Update sync state for a device."""
        if not self.is_connected():
            return
        (self.db.collection("users").document(user_id)
         .collection("devices").document(device_id).set({
             **state,
             "last_seen": datetime.now(timezone.utc)
         }, merge=True))

    def get_all_device_states(self, user_id: str) -> List[Dict]:
        """Get sync state of all known devices."""
        if not self.is_connected():
            return []
        ref = (self.db.collection("users").document(user_id)
               .collection("devices"))
        return [{"device_id": doc.id, **doc.to_dict()} for doc in ref.stream()]
