#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Memory Server - Firebase Firestore backend
Transport: stdio (default) or HTTP/SSE

Usage:
  python server.py                    # stdio transport
  python server.py --transport http   # HTTP transport on port 8080

Environment variables:
  FIREBASE_PROJECT_ID   - Firebase project ID
  FIREBASE_CREDENTIALS  - Path to service account JSON
  MCP_USER_ID           - User namespace (default: 'default')
  EMBEDDING_MODEL       - 'local' | 'openai' | 'gemini'
"""
import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.remember import RememberTool
from tools.recall import RecallTool
from tools.summarize import SummarizeTool
from tools.sync import SyncTool
from firebase.client import FirebaseClient


class MCPMemoryServer:
    def __init__(self):
        self.project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
        self.credentials = os.environ.get("FIREBASE_CREDENTIALS", "")
        self.user_id = os.environ.get("MCP_USER_ID", "default")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "local")

        self.firebase = FirebaseClient(
            project_id=self.project_id,
            credentials_path=self.credentials
        )

        self.tools = {
            "remember_fact": RememberTool(self.firebase, self.user_id),
            "semantic_recall": RecallTool(self.firebase, self.user_id, self.embedding_model),
            "summarize_context": SummarizeTool(self.firebase, self.user_id),
            "sync_devices": SyncTool(self.firebase, self.user_id),
        }

        self.manifest = {
            "name": "mcp-memory-server",
            "version": "1.0.0",
            "description": "Firebase-backed persistent memory for PyGPT",
            "tools": self._get_tools_schema()
        }

    def _get_tools_schema(self):
        return [
            {
                "name": "remember_fact",
                "description": "Save a fact, preference or project detail to long-term memory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "The information to remember"},
                        "category": {
                            "type": "string",
                            "enum": ["preference", "fact", "skill", "project", "conversation"],
                            "description": "Category of the memory"
                        },
                        "importance": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Importance score (0.0-1.0)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for filtering"
                        }
                    },
                    "required": ["content", "category"]
                }
            },
            {
                "name": "semantic_recall",
                "description": "Search memory using semantic similarity. Returns relevant memories matching the query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for in memory"},
                        "limit": {"type": "integer", "default": 5, "description": "Max results"},
                        "category": {"type": "string", "description": "Filter by category (optional)"},
                        "min_importance": {"type": "number", "default": 0.0, "description": "Min importance threshold"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "summarize_context",
                "description": "Get a summary of recent conversations on a topic.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Topic to summarize"},
                        "days_back": {"type": "integer", "default": 7, "description": "How many days back to look"}
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "sync_devices",
                "description": "Sync memory state between devices. Returns latest context from any device.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Unique device identifier"},
                        "push": {"type": "boolean", "default": False, "description": "Push local state to cloud"}
                    },
                    "required": ["device_id"]
                }
            }
        ]

    async def handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", 1)

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": self.manifest}

        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.manifest["tools"]}}

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
                }

            try:
                result = await self.tools[tool_name].execute(args)
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result)}]}
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32000, "message": str(e)}
                }
        else:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"}
            }

    async def run_stdio(self):
        """Run server on stdio transport"""
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            try:
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                error = {"jsonrpc": "2.0", "id": None,
                         "error": {"code": -32700, "message": f"Parse error: {e}"}}
                print(json.dumps(error), flush=True)


def main():
    parser = argparse.ArgumentParser(description="MCP Memory Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = MCPMemoryServer()

    if args.transport == "stdio":
        asyncio.run(server.run_stdio())
    else:
        print(f"HTTP transport not yet implemented. Use stdio.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
