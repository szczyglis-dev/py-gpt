#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import re
import shlex
from fnmatch import fnmatchcase
from typing import Any, Dict, List, Optional, Tuple

_ENV_PATTERNS = (
    re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}"),
    re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)", re.I),
)


def json_dict(value: Any) -> Dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except Exception:
        pass
    return {}


def expand_env(value: Any) -> str:
    text = str(value or "")
    text = os.path.expandvars(text)
    for pattern in _ENV_PATTERNS:
        text = pattern.sub(lambda m: os.environ.get(m.group(1), m.group(0)), text)
    return text


def build_env(server: dict) -> Optional[dict]:
    env_cfg = json_dict(server.get("env"))
    if not env_cfg:
        return None
    env = dict(os.environ)
    for key, value in env_cfg.items():
        env[str(key)] = expand_env(value)
    return env


def build_headers(server: dict) -> Optional[dict]:
    headers = {key: expand_env(value) for key, value in json_dict(server.get("headers")).items()}
    for header, env_name in json_dict(server.get("env_http_headers")).items():
        value = os.environ.get(str(env_name), "")
        if value:
            headers[str(header)] = value
    token_env = str(server.get("bearer_token_env_var") or "").strip()
    if token_env and os.environ.get(token_env):
        headers.setdefault("Authorization", f"Bearer {os.environ[token_env]}")
    auth = expand_env(server.get("authorization"))
    if auth:
        headers["Authorization"] = auth
    return headers or None


def parse_stdio(address: str) -> Tuple[str, List[str]]:
    cmdline = str(address or "")
    if cmdline.lower().startswith("stdio:"):
        cmdline = cmdline[len("stdio:"):]
    tokens = shlex.split(cmdline.strip())
    if not tokens:
        raise ValueError("Invalid stdio address: empty command")
    return tokens[0], tokens[1:]


def float_option(server: dict, key: str, default: float) -> float:
    try:
        value = server.get(key)
        if value in (None, ""):
            return float(default)
        return max(0.1, float(value))
    except Exception:
        return float(default)


def tool_allowed(name: str, allowed: Optional[set], disabled: Optional[set]) -> bool:
    if disabled and any(fnmatchcase(name, pattern) for pattern in disabled):
        return False
    if allowed and not any(fnmatchcase(name, pattern) for pattern in allowed):
        return False
    return True
