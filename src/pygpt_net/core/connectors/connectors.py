#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 15:05:00                  #
# ================================================== #

from __future__ import annotations

import json
import os
import re
import shlex
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:  # Python >= 3.11
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover - Python 3.10
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:  # pragma: no cover
        tomllib = None


class ConnectorsError(RuntimeError):
    pass


class Connectors:
    """Universal MCP connector importer/registry.

    Connectors are a convenience layer over the existing MCP plugin.  There is
    intentionally only one runtime registry: ``plugin.mcp.servers``.  Importers
    normalize vendor config dialects (Claude, Codex, OpenClaw, Cursor, VS Code,
    OpenCode, MCPorter and generic MCP JSON/TOML/YAML) into that registry.
    """

    DEFAULT_CATALOG_URL = (
        "https://raw.githubusercontent.com/szczyglis-dev/py-gpt/master/"
        "src/pygpt_net/data/connectors/catalog.json"
    )
    MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024
    MAX_CATALOG_BYTES = 4 * 1024 * 1024
    CONFIG_NAMES = {
        ".mcp.json", "mcp.json", "mcp.jsonc", "mcporter.json", "opencode.json",
        "opencode.jsonc", "config.toml", "settings.json", "settings.jsonc",
    }
    CONFIG_EXTENSIONS = {".json", ".jsonc", ".json5", ".toml", ".yaml", ".yml"}

    def __init__(self, window=None):
        self.window = window

    # REGISTRY ------------------------------------------------------------

    def _plugin(self):
        plugin = self.window.core.plugins.plugins.get("mcp")
        if plugin is None:
            raise ConnectorsError("MCP plugin is not available")
        return plugin

    def get_servers(self) -> List[dict]:
        plugin = self._plugin()
        value = plugin.get_option_value("servers") or []
        return [dict(item) for item in value if isinstance(item, dict)]

    def set_servers(self, servers: Iterable[dict], save: bool = True):
        value = [self._sanitize_server(dict(item)) for item in servers if isinstance(item, dict)]
        plugin = self._plugin()
        # Set directly. Calling BasePlugin.set_option_value would rebuild the
        # dictionary editor for every checkbox click and is unnecessarily heavy.
        plugin.options["servers"]["value"] = value
        self.window.core.config.update_plugin_config("mcp", "servers", value)
        plugin._tools_cache.clear()
        plugin._last_config_signature = None
        if save:
            self.window.core.config.save()
        return value

    def add_servers(self, servers: Iterable[dict], replace: bool = False) -> List[dict]:
        current = self.get_servers()
        by_key = {self._identity(item): idx for idx, item in enumerate(current)}
        imported = []
        for server in servers:
            row = self._sanitize_server(dict(server))
            key = self._identity(row)
            if key in by_key:
                if replace:
                    current[by_key[key]] = row
                    imported.append(row)
                continue
            by_key[key] = len(current)
            current.append(row)
            imported.append(row)
        self.set_servers(current)
        return imported

    def update_server(self, index: int, server: dict):
        servers = self.get_servers()
        if index < 0 or index >= len(servers):
            raise ConnectorsError("Connector no longer exists")
        servers[index] = self._sanitize_server(server)
        self.set_servers(servers)

    def remove_server(self, index: int):
        servers = self.get_servers()
        if index < 0 or index >= len(servers):
            return
        del servers[index]
        self.set_servers(servers)

    def set_active(self, index: int, active: bool):
        servers = self.get_servers()
        if index < 0 or index >= len(servers):
            return
        servers[index]["active"] = bool(active)
        self.set_servers(servers)
        if active:
            self.window.core.plugins.enable("mcp")

    @staticmethod
    def get_server_id(server: dict) -> str:
        """Return the stable textual ID used by presets for an MCP item."""
        return str(server.get("label") or "").strip()

    def get_active_ids(self) -> List[str]:
        """Return textual IDs of active configured MCP servers."""
        out = []
        for server in self.get_servers():
            server_id = self.get_server_id(server)
            if server_id and bool(server.get("active", False)):
                out.append(server_id)
        return out

    def set_active_ids(self, ids: Iterable[str], save: bool = True) -> List[str]:
        """Apply an MCP active-server selection by textual ID.

        Missing IDs are ignored. Every currently available server not present
        in the requested selection is deactivated.
        """
        selected = {str(item).strip() for item in (ids or []) if str(item).strip()}
        servers = self.get_servers()
        active = []
        for server in servers:
            server_id = self.get_server_id(server)
            is_active = bool(server_id and server_id in selected)
            server["active"] = is_active
            if is_active:
                active.append(server_id)
        self.set_servers(servers, save=save)
        if active:
            self.window.core.plugins.enable("mcp")
        return active

    @staticmethod
    def _identity(server: dict) -> Tuple[str, str]:
        return (
            str(server.get("label") or "").strip().lower(),
            str(server.get("server_address") or "").strip(),
        )

    @staticmethod
    def _sanitize_server(server: dict) -> dict:
        defaults = {
            "active": False,
            "label": "connector",
            "server_address": "",
            "authorization": "",
            "allowed_commands": "",
            "disabled_commands": "",
            "transport": "auto",
            "env": "",
            "headers": "",
            "env_http_headers": "",
            "bearer_token_env_var": "",
            "cwd": "",
            "startup_timeout_sec": "",
            "tool_timeout_sec": "",
            "source": "manual",
            "extra": "",
        }
        out = {**defaults, **server}
        out["active"] = bool(out.get("active", False))
        for key in defaults:
            if key == "active":
                continue
            value = out.get(key, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            elif value is None:
                value = ""
            out[key] = str(value)
        out["label"] = out["label"].strip() or "connector"
        out["transport"] = out["transport"].strip().lower() or "auto"
        return out

    # CATALOG -------------------------------------------------------------

    def get_catalog_url(self) -> str:
        value = str(self.window.core.config.get("connectors.catalog.url", "") or "").strip()
        return value or self.DEFAULT_CATALOG_URL

    def set_catalog_url(self, value: str):
        self.window.core.config.set("connectors.catalog.url", str(value or "").strip())
        self.window.core.config.save()

    def get_bundled_catalog_path(self) -> str:
        return os.path.join(self.window.core.config.get_app_path(), "data", "connectors", "catalog.json")

    def fetch_catalog(self, url: Optional[str] = None) -> List[dict]:
        target = str(url or self.get_catalog_url()).strip()
        raw = None
        if target:
            try:
                raw = self._download_bytes(target, self.MAX_CATALOG_BYTES)
            except Exception as exc:
                self._log(exc)
                if target != self.DEFAULT_CATALOG_URL:
                    raise
        if raw is None:
            path = self.get_bundled_catalog_path()
            if not os.path.isfile(path):
                return []
            with open(path, "rb") as handle:
                raw = handle.read(self.MAX_CATALOG_BYTES + 1)
        if len(raw) > self.MAX_CATALOG_BYTES:
            raise ConnectorsError("Connectors catalog is too large")
        try:
            value = json.loads(raw.decode("utf-8-sig"))
        except Exception as exc:
            raise ConnectorsError(f"Invalid connectors catalog JSON: {exc}") from exc
        entries = value.get("connectors", []) if isinstance(value, dict) else value
        if not isinstance(entries, list):
            raise ConnectorsError("Connectors catalog must contain a 'connectors' array")
        return [dict(item) for item in entries if isinstance(item, dict) and item.get("name")]

    def install_catalog_entry(self, entry: dict) -> List[dict]:
        if isinstance(entry.get("config"), dict):
            servers = self.parse_data(entry["config"], source=f"catalog:{entry.get('name')}")
        elif entry.get("github"):
            servers = self.import_github(str(entry["github"]), persist=False)
        elif entry.get("url"):
            raw = self._download_bytes(str(entry["url"]), self.MAX_DOWNLOAD_BYTES)
            servers = self.parse_bytes(raw, str(entry["url"]), source=f"catalog:{entry.get('name')}")
        else:
            raise ConnectorsError("Catalog entry has no config, url or github source")
        for server in servers:
            server["active"] = False
            server["source"] = f"catalog:{entry.get('name')}"
        return self.add_servers(servers)

    # IMPORT --------------------------------------------------------------

    def import_local(self, path: str, persist: bool = True) -> List[dict]:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            raise ConnectorsError(f"Path does not exist: {path}")
        collected = []
        if os.path.isdir(path):
            for candidate in self._iter_config_files(path):
                try:
                    collected.extend(self.parse_file(candidate))
                except Exception as exc:
                    self._log(exc)
        else:
            collected = self.parse_file(path)
        if not collected:
            raise ConnectorsError("No MCP connector definitions found")
        return self.add_servers(collected) if persist else collected

    def import_github(self, url: str, persist: bool = True) -> List[dict]:
        url = str(url or "").strip()
        parsed = urlparse(url)
        if parsed.netloc.lower() not in {"github.com", "www.github.com", "raw.githubusercontent.com"}:
            raw = self._download_bytes(url, self.MAX_DOWNLOAD_BYTES)
            servers = self.parse_bytes(raw, url, source=url)
            return self.add_servers(servers) if persist else servers

        if parsed.netloc.lower() == "raw.githubusercontent.com" or "/blob/" in parsed.path:
            raw_url = self._github_raw_url(url)
            raw = self._download_bytes(raw_url, self.MAX_DOWNLOAD_BYTES)
            servers = self.parse_bytes(raw, raw_url, source=url)
            return self.add_servers(servers) if persist else servers

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ConnectorsError("GitHub URL must point to a repository or config file")
        owner, repo = parts[0], parts[1].removesuffix(".git")
        archive = f"https://api.github.com/repos/{owner}/{repo}/zipball"
        raw = self._download_bytes(archive, self.MAX_DOWNLOAD_BYTES)
        with tempfile.TemporaryDirectory(prefix="pygpt-connectors-") as tmp:
            zip_path = os.path.join(tmp, "repo.zip")
            with open(zip_path, "wb") as handle:
                handle.write(raw)
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(tmp)
            except Exception as exc:
                raise ConnectorsError(f"Invalid GitHub archive: {exc}") from exc
            roots = [p for p in Path(tmp).iterdir() if p.is_dir()]
            root = str(roots[0]) if roots else tmp
            servers = self.import_local(root, persist=False)
            for server in servers:
                server["source"] = url
            return self.add_servers(servers) if persist else servers

    def _iter_config_files(self, root: str):
        count = 0
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "venv", "dist", "build"}]
            depth = len(Path(base).relative_to(root).parts)
            if depth > 5:
                dirs[:] = []
                continue
            for name in files:
                lower = name.lower()
                ext = os.path.splitext(lower)[1]
                if lower not in self.CONFIG_NAMES and ext not in self.CONFIG_EXTENSIONS:
                    continue
                # Prefer files whose names indicate MCP/client config. Generic
                # JSON/YAML is still accepted but only if parsing finds a MCP tree.
                count += 1
                if count > 250:
                    return
                yield os.path.join(base, name)

    # PARSING -------------------------------------------------------------

    def parse_file(self, path: str) -> List[dict]:
        with open(path, "rb") as handle:
            raw = handle.read(self.MAX_DOWNLOAD_BYTES + 1)
        if len(raw) > self.MAX_DOWNLOAD_BYTES:
            raise ConnectorsError(f"Config file is too large: {path}")
        return self.parse_bytes(raw, path, source=path)

    def parse_bytes(self, raw: bytes, hint: str = "config.json", source: str = "import") -> List[dict]:
        text = raw.decode("utf-8-sig")
        data = self._decode_config(text, hint)
        return self.parse_data(data, source=source, hint=hint)

    def parse_data(self, data: Any, source: str = "import", hint: str = "") -> List[dict]:
        if not isinstance(data, dict):
            return []
        dialect, servers = self._find_servers(data, hint)
        if not servers:
            # Accept a single MCP server definition as a portable connector file.
            if self._looks_like_server(data):
                servers = {str(data.get("name") or data.get("label") or "connector"): data}
                dialect = "generic"
            else:
                return []
        result = []
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            row = self._normalize_server(str(name), cfg, dialect=dialect, source=source)
            if row.get("server_address"):
                result.append(row)
        return result

    def _find_servers(self, data: dict, hint: str = "") -> Tuple[str, Dict[str, dict]]:
        for key, dialect in (("mcpServers", "claude"), ("mcp_servers", "codex")):
            value = data.get(key)
            if isinstance(value, dict):
                return dialect, value

        mcp = data.get("mcp")
        if isinstance(mcp, dict):
            if isinstance(mcp.get("servers"), dict):
                return "openclaw", mcp["servers"]
            # OpenCode uses {"mcp": {"name": {type/local/...}}}.
            if any(isinstance(v, dict) and self._looks_like_server(v) for v in mcp.values()):
                return "opencode", mcp

        value = data.get("servers")
        if isinstance(value, dict) and any(self._looks_like_server(v) for v in value.values() if isinstance(v, dict)):
            lower_hint = str(hint).lower()
            dialect = "vscode" if "mcp.json" in lower_hint or ".vscode" in lower_hint else "generic"
            return dialect, value

        # Some MCPorter exports wrap the map in a profile/config object.
        for key in ("config", "profile", "mcpConfig"):
            nested = data.get(key)
            if isinstance(nested, dict):
                dialect, value = self._find_servers(nested, hint)
                if value:
                    return dialect, value
        return "generic", {}

    @staticmethod
    def _looks_like_server(value: dict) -> bool:
        keys = set(value.keys())
        return bool(keys.intersection({
            "command", "url", "baseUrl", "base_url", "server_address", "transport",
            "type", "args", "headers", "env", "environment",
        }))

    def _normalize_server(self, name: str, cfg: dict, dialect: str, source: str) -> dict:
        command = cfg.get("command")
        args = cfg.get("args") or cfg.get("arguments") or []
        if isinstance(command, list):
            cmd_parts = [str(x) for x in command]
            command = cmd_parts[0] if cmd_parts else ""
            args = cmd_parts[1:] + (list(args) if isinstance(args, list) else [])
        if isinstance(args, str):
            try:
                args = shlex.split(args)
            except Exception:
                args = [args]
        if not isinstance(args, list):
            args = []

        url = (
            cfg.get("server_address") or cfg.get("url") or cfg.get("baseUrl") or
            cfg.get("base_url") or cfg.get("serverUrl") or ""
        )
        transport = str(cfg.get("transport") or cfg.get("type") or "auto").lower()
        if transport in {"local", "stdio"}:
            transport = "stdio"
        elif transport in {"remote", "streamable-http", "streamable_http", "http"}:
            transport = "http"
        elif transport not in {"sse", "auto"}:
            transport = "auto"

        if command:
            quoted = " ".join(shlex.quote(str(x)) for x in [command, *args])
            address = f"stdio: {quoted}"
            transport = "stdio"
        else:
            address = str(url or "").strip()
            if transport == "sse" and address.startswith("http"):
                pass
            elif transport == "auto" and address:
                transport = "http"

        env = cfg.get("env") or cfg.get("environment") or cfg.get("env_vars") or {}
        headers = cfg.get("headers") or cfg.get("http_headers") or {}
        env_headers = cfg.get("env_http_headers") or cfg.get("header_env") or {}
        authorization = str(cfg.get("authorization") or "")
        if isinstance(headers, dict):
            for key in list(headers):
                if str(key).lower() == "authorization" and not authorization:
                    authorization = str(headers.pop(key))
                    break

        allowed = cfg.get("enabled_tools") or cfg.get("allowed_tools") or cfg.get("allowedTools") or []
        disabled = cfg.get("disabled_tools") or cfg.get("disabledTools") or cfg.get("denied_tools") or []
        tool_filter = cfg.get("toolFilter") or cfg.get("tool_filter")
        if isinstance(tool_filter, dict):
            allowed = allowed or tool_filter.get("allow") or tool_filter.get("include") or []
            disabled = disabled or tool_filter.get("deny") or tool_filter.get("exclude") or []

        startup = cfg.get("startup_timeout_sec")
        tool_timeout = cfg.get("tool_timeout_sec")
        if dialect == "openclaw":
            startup = startup or cfg.get("connectTimeout") or cfg.get("connect_timeout")
            tool_timeout = tool_timeout or cfg.get("timeout")
        elif dialect == "opencode":
            # OpenCode timeout values are milliseconds.
            startup_ms = cfg.get("startup_timeout") or cfg.get("startupTimeout")
            execution_ms = cfg.get("execution_timeout") or cfg.get("executionTimeout") or cfg.get("timeout")
            startup = startup or self._ms_to_sec(startup_ms)
            tool_timeout = tool_timeout or self._ms_to_sec(execution_ms)

        enabled = cfg.get("enabled")
        if enabled is None:
            enabled = not bool(cfg.get("disabled", False))

        known = {
            "name", "label", "command", "args", "arguments", "url", "baseUrl", "base_url",
            "serverUrl", "server_address", "transport", "type", "env", "environment", "env_vars",
            "headers", "http_headers", "env_http_headers", "header_env", "authorization",
            "bearer_token_env_var", "cwd", "working_dir", "enabled_tools", "allowed_tools",
            "allowedTools", "disabled_tools", "disabledTools", "denied_tools", "toolFilter",
            "tool_filter", "startup_timeout_sec", "tool_timeout_sec", "connectTimeout",
            "connect_timeout", "timeout", "startup_timeout", "startupTimeout", "execution_timeout",
            "executionTimeout", "enabled", "disabled",
        }
        extra = {key: value for key, value in cfg.items() if key not in known}
        # Keep OAuth/helper metadata for round-tripping, but never execute helper
        # commands merely because a foreign config was imported.

        row = {
            "active": False,  # explicit user opt-in after import
            "label": str(cfg.get("label") or name or "connector"),
            "server_address": address,
            "authorization": authorization,
            "allowed_commands": self._join_list(allowed),
            "disabled_commands": self._join_list(disabled),
            "transport": transport,
            "env": self._json_field(env),
            "headers": self._json_field(headers),
            "env_http_headers": self._json_field(env_headers),
            "bearer_token_env_var": str(cfg.get("bearer_token_env_var") or ""),
            "cwd": str(cfg.get("cwd") or cfg.get("working_dir") or ""),
            "startup_timeout_sec": self._text_number(startup),
            "tool_timeout_sec": self._text_number(tool_timeout),
            "source": source or dialect,
            "extra": self._json_field({"dialect": dialect, "vendor": extra} if extra else {"dialect": dialect}),
        }
        # Remember the source enabled state without auto-running it.
        if bool(enabled):
            meta = self._json_load(row["extra"])
            meta["imported_enabled"] = True
            row["extra"] = self._json_field(meta)
        return self._sanitize_server(row)

    @staticmethod
    def _join_list(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(x) for x in value if str(x).strip())
        return ""

    @staticmethod
    def _json_field(value: Any) -> str:
        if value in (None, "", {}, []):
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _json_load(value: str) -> dict:
        try:
            obj = json.loads(value or "{}")
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _text_number(value: Any) -> str:
        if value in (None, ""):
            return ""
        try:
            number = float(value)
            return str(int(number)) if number.is_integer() else str(number)
        except Exception:
            return str(value)

    @staticmethod
    def _ms_to_sec(value: Any):
        if value in (None, ""):
            return ""
        try:
            return float(value) / 1000.0
        except Exception:
            return value

    def _decode_config(self, text: str, hint: str) -> dict:
        try:
            import yaml
        except ImportError:  # pragma: no cover
            yaml = None
        lower = str(hint).lower()
        suffix = os.path.splitext(urlparse(lower).path)[1]
        errors = []
        if suffix == ".toml" or "config.toml" in lower:
            try:
                return self._decode_toml(text)
            except Exception as exc:
                errors.append(exc)
        if suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise ConnectorsError("PyYAML is required to import YAML connector configs")
            value = yaml.safe_load(text)
            return value if isinstance(value, dict) else {}
        try:
            return json.loads(self._strip_jsonc(text))
        except Exception as exc:
            errors.append(exc)
        # Try TOML even when the extension is unknown (pasted/raw GitHub URLs).
        try:
            return self._decode_toml(text)
        except Exception as exc:
            errors.append(exc)
        if yaml is not None:
            try:
                value = yaml.safe_load(text)
                if isinstance(value, dict):
                    return value
            except Exception as exc:
                errors.append(exc)
        raise ConnectorsError(f"Unsupported or invalid connector config: {errors[-1] if errors else 'unknown format'}")

    @staticmethod
    def _strip_jsonc(text: str) -> str:
        # Small state machine so URLs such as https:// are not treated as comments.
        out = []
        i = 0
        in_string = False
        quote = '"'
        escaped = False
        while i < len(text):
            ch = text[i]
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if in_string:
                out.append(ch)
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    in_string = False
                i += 1
                continue
            if ch in {'"', "'"}:
                in_string = True
                quote = ch
                out.append(ch)
                i += 1
                continue
            if ch == "/" and nxt == "/":
                i += 2
                while i < len(text) and text[i] not in "\r\n":
                    i += 1
                continue
            if ch == "/" and nxt == "*":
                i += 2
                while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue
            out.append(ch)
            i += 1
        cleaned = "".join(out)
        return re.sub(r",\s*([}\]])", r"\1", cleaned)

    def _decode_toml(self, text: str) -> dict:
        if tomllib is not None:
            return tomllib.loads(text)
        # Dependency-free fallback for the MCP subset used by Codex.  Supports
        # [mcp_servers.NAME] and one-level child tables such as .env/.http_headers.
        root: Dict[str, Any] = {}
        current: Dict[str, Any] = root
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                path = self._split_toml_path(line[1:-1].strip())
                current = root
                for part in path:
                    current = current.setdefault(part, {})
                continue
            if "=" not in line:
                continue
            key, raw_value = line.split("=", 1)
            current[key.strip().strip('"\'')] = self._parse_toml_scalar(raw_value.strip())
        return root

    @staticmethod
    def _split_toml_path(value: str) -> List[str]:
        return [part.strip().strip('"\'') for part in value.split(".") if part.strip()]

    @staticmethod
    def _parse_toml_scalar(value: str):
        value = value.split(" #", 1)[0].strip()
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if value.startswith("[") and value.endswith("]"):
            body = value[1:-1].strip()
            if not body:
                return []
            # MCP args/tool lists overwhelmingly contain strings; use JSON after
            # normalizing single quotes, falling back to a comma split.
            try:
                return json.loads("[" + body.replace("'", '"') + "]")
            except Exception:
                return [x.strip().strip('"\'') for x in body.split(",") if x.strip()]
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        try:
            return int(value)
        except Exception:
            try:
                return float(value)
            except Exception:
                return value

    # NETWORK -------------------------------------------------------------

    def _download_bytes(self, url: str, limit: int) -> bytes:
        req = Request(url, headers={"User-Agent": "PyGPT Connectors/1.0", "Accept": "application/json, text/plain, */*"})
        with urlopen(req, timeout=20) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ConnectorsError("Downloaded connector data is too large")
        return data

    @staticmethod
    def _github_raw_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.lower() == "raw.githubusercontent.com":
            return url
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 5 and parts[2] == "blob":
            return f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/{parts[3]}/{'/'.join(parts[4:])}"
        return url

    def _log(self, value):
        try:
            self.window.core.debug.log(value)
        except Exception:
            pass
