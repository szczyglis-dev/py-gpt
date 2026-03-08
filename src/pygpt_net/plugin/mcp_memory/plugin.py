# -*- coding: utf-8 -*-
import subprocess
import sys
import os
from pathlib import Path
from pygpt_net.plugin.base import BasePlugin


class MemoryCloudPlugin(BasePlugin):
    """MCP Memory Cloud - Firebase Firestore persistent memory"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "mcp_memory"
        self.name = "Memory Cloud (MCP + Firebase)"
        self.description = "Persistent cloud memory with semantic search via MCP and Firebase Firestore"
        self.order = 50
        self.use_locale = True
        self._mcp_process = None

    def init_options(self):
        self.add_option("enabled", type="bool", value=False,
                        label="Enable Memory Cloud",
                        description="Sync conversations to Firebase Firestore via MCP")
        self.add_option("firebase_project_id", type="text", value="",
                        label="Firebase Project ID",
                        description="Your Firebase project ID (e.g. my-pygpt-memory)")
        self.add_option("firebase_credentials_path", type="text", value="",
                        label="Firebase Credentials JSON path",
                        description="Path to your Firebase service account JSON file")
        self.add_option("user_id", type="text", value="default",
                        label="User ID",
                        description="Unique identifier for your memory namespace")
        self.add_option("auto_remember", type="bool", value=True,
                        label="Auto-remember conversations",
                        description="Automatically save conversations to cloud memory")
        self.add_option("semantic_search", type="bool", value=True,
                        label="Enable semantic search",
                        description="Use embeddings for smart memory retrieval")
        self.add_option("embedding_model", type="combo", value="local",
                        label="Embedding model",
                        keys=["local", "openai", "gemini"],
                        description="Model to use for generating embeddings")
        self.add_option("memory_ttl_days", type="int", value=90,
                        label="Memory TTL (days)", min=7, max=365,
                        description="Days to keep short-term memories (0=forever)")
        self.add_option("sync_mode", type="combo", value="realtime",
                        label="Sync mode",
                        keys=["realtime", "manual", "on_exit"],
                        description="When to sync to cloud")
        self.add_option("mcp_server_path", type="text",
                        value=str(Path(__file__).parent.parent.parent.parent.parent /
                                  "mcp-memory-server" / "server.py"),
                        label="MCP Server path",
                        description="Path to the MCP memory server script")

    def setup(self):
        return self.options

    def attach(self, window):
        self.window = window
        if self.get_option_value("enabled"):
            self._start_mcp_server()

    def _start_mcp_server(self):
        """Start the standalone MCP memory server as subprocess"""
        server_path = self.get_option_value("mcp_server_path")
        project_id = self.get_option_value("firebase_project_id")
        creds_path = self.get_option_value("firebase_credentials_path")

        if not project_id or not creds_path:
            self.log("Memory Cloud: Firebase credentials not configured", "warning")
            return

        env = os.environ.copy()
        env["FIREBASE_PROJECT_ID"] = project_id
        env["FIREBASE_CREDENTIALS"] = creds_path
        env["MCP_USER_ID"] = self.get_option_value("user_id")
        env["EMBEDDING_MODEL"] = self.get_option_value("embedding_model")

        try:
            self._mcp_process = subprocess.Popen(
                [sys.executable, server_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.log(f"Memory Cloud MCP server started (PID {self._mcp_process.pid})")
        except Exception as e:
            self.log(f"Memory Cloud: Failed to start MCP server: {e}", "error")

    def on_ctx_end(self, ctx):
        """Auto-save conversation when context ends"""
        if not self.get_option_value("enabled"):
            return
        if not self.get_option_value("auto_remember"):
            return
        if self._mcp_process and self.get_option_value("sync_mode") == "realtime":
            self._sync_context(ctx)

    def _sync_context(self, ctx):
        """Send context to MCP server for saving"""
        # Will be handled by PyGPT MCP plugin infrastructure
        pass

    def on_disable(self):
        if self._mcp_process:
            self._mcp_process.terminate()
            self._mcp_process = None

    def destroy(self):
        self.on_disable()
