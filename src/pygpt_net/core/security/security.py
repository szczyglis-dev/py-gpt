#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.19 16:05:00                  #
# ================================================== #

import os
import re
import shlex
from typing import Iterable, List, Optional


class SecurityError(PermissionError):
    """Raised when a host-side plugin operation is blocked by Security settings."""


class Security:
    """Shared host-side security checks used by plugins."""

    READ_RESTRICT_KEY = "security.filesystem.read.restrict"
    WRITE_RESTRICT_KEY = "security.filesystem.write.restrict"
    WHITELIST_ENABLED_KEY = "security.commands.whitelist.enabled"
    WHITELIST_KEY_PREFIX = "security.commands.whitelist."
    BLACKLIST_KEY_PREFIX = "security.commands.blacklist."
    COMPUTER_HALT_INSECURE_KEY = "security.computer.halt_insecure"

    _SHELL_SPLIT_RE = re.compile(r"(?:&&|\|\||[;|\n\r])+")
    _WINDOWS_EXTENSIONS = (".exe", ".cmd", ".bat", ".com")

    def __init__(self, window=None):
        self.window = window

    def get_workdir(self) -> str:
        """Return the plugin filesystem working directory (the user data directory)."""
        return self.window.core.config.get_user_dir("data")

    def get_os_id(self) -> str:
        """Return settings suffix for the current host operating system."""
        platforms = self.window.core.platforms
        if platforms.is_windows():
            return "windows"
        if platforms.is_mac():
            return "macos"
        return "linux"

    def get_os_label(self) -> str:
        """Return the human-readable operating-system label used by the Settings UI."""
        return {
            "linux": "Linux",
            "windows": "Windows",
            "macos": "macOS",
        }[self.get_os_id()]

    def is_read_restricted(self) -> bool:
        return bool(self.window.core.config.get(self.READ_RESTRICT_KEY, True))

    def is_write_restricted(self) -> bool:
        return bool(self.window.core.config.get(self.WRITE_RESTRICT_KEY, False))

    @staticmethod
    def _normalize_path(path: str) -> str:
        return os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(str(path)))))

    @classmethod
    def _is_in_dir(cls, path: str, directory: str) -> bool:
        """Check path containment using resolved paths (including symlink resolution)."""
        try:
            root = cls._normalize_path(directory)
            target = cls._normalize_path(path)
            return os.path.commonpath([root, target]) == root
        except (TypeError, ValueError, OSError):
            return False

    def is_in_workdir(self, path: str) -> bool:
        """Return True when path is inside the user-facing workdir data directory."""
        return self._is_in_dir(path, self.get_workdir())

    def is_in_internal_tmp(self, path: str) -> bool:
        """Return True when path is inside the app-owned workdir temporary directory."""
        return self._is_in_dir(path, self.window.core.config.get_user_dir("tmp"))

    def is_in_allowed_workdir(self, path: str) -> bool:
        """Return True for paths allowed by the workdir filesystem restriction."""
        return self.is_in_workdir(path) or self.is_in_internal_tmp(path)

    def ensure_read(self, path: str, sandbox: bool = False) -> str:
        """Validate a local file/directory read. Security restrictions are bypassed in sandbox mode."""
        if path is None or str(path).strip() == "":
            return path
        if sandbox or not self.is_read_restricted() or self.is_in_allowed_workdir(path):
            return path
        raise SecurityError(
            "Permission denied - filesystem read access outside the workdir data directory is disabled. "
            "Enable filesystem access outside workdir in Settings -> Security "
            "(disable the read restriction). Allowed directory: {}"
            .format(self.get_workdir())
        )

    def ensure_write(self, path: str, sandbox: bool = False) -> str:
        """Validate a local file/directory write. Security restrictions are bypassed in sandbox mode."""
        if path is None or str(path).strip() == "":
            return path
        if sandbox or not self.is_write_restricted() or self.is_in_allowed_workdir(path):
            return path
        raise SecurityError(
            "Permission denied - filesystem write access outside the workdir data directory is disabled. "
            "Enable filesystem access outside workdir in Settings -> Security "
            "(disable the write restriction). Allowed directory: {}"
            .format(self.get_workdir())
        )

    def ensure_reads(self, paths: Iterable[str], sandbox: bool = False):
        for path in paths or []:
            self.ensure_read(path, sandbox=sandbox)

    def ensure_writes(self, paths: Iterable[str], sandbox: bool = False):
        for path in paths or []:
            self.ensure_write(path, sandbox=sandbox)

    @staticmethod
    def _parse_list(value) -> set:
        if value is None:
            return set()
        if isinstance(value, (list, tuple, set)):
            parts = value
        else:
            parts = re.split(r"[;,]+", str(value))
        return {str(item).strip().lower() for item in parts if str(item).strip()}

    def get_command_whitelist(self) -> set:
        key = self.WHITELIST_KEY_PREFIX + self.get_os_id()
        return self._parse_list(self.window.core.config.get(key, ""))

    def get_command_blacklist(self) -> set:
        key = self.BLACKLIST_KEY_PREFIX + self.get_os_id()
        return self._parse_list(self.window.core.config.get(key, ""))

    def is_command_whitelist_enabled(self) -> bool:
        return bool(self.window.core.config.get(self.WHITELIST_ENABLED_KEY, False))

    def _normalize_command_name(self, value: str) -> str:
        name = os.path.basename(str(value).strip().strip('"\''))
        name = name.lower()
        if self.get_os_id() == "windows":
            for ext in self._WINDOWS_EXTENSIONS:
                if name.endswith(ext):
                    name = name[:-len(ext)]
                    break
        return name

    def _segment_command(self, segment: str) -> Optional[str]:
        segment = segment.strip()
        if not segment:
            return None
        try:
            tokens = shlex.split(segment, posix=self.get_os_id() != "windows")
        except ValueError:
            tokens = segment.split()
        if not tokens:
            return None

        idx = 0
        # Skip POSIX environment assignments before the executable.
        while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx]):
            idx += 1
        if idx >= len(tokens):
            return None

        name = self._normalize_command_name(tokens[idx])
        return name or None

    def extract_command_names(self, command: str) -> List[str]:
        """Extract executable/builtin names from a possibly chained shell command."""
        if command is None:
            return []
        text = str(command).strip()
        if not text:
            return []

        # PowerShell/cmd are treated as executables themselves. Allowing an interpreter
        # intentionally grants it the ability to run its own command language.
        parts = self._SHELL_SPLIT_RE.split(text)
        if self.get_os_id() == "windows":
            expanded = []
            for part in parts:
                expanded.extend(re.split(r"(?<!\^)&", part))
            parts = expanded

        names = []
        for part in parts:
            name = self._segment_command(part)
            if name and name not in names:
                names.append(name)
        return names


    def is_computer_sandbox(self) -> bool:
        """Return True when Computer Use runs in sandbox mode."""
        return bool(self.window.core.config.get("remote_tools.computer_use.sandbox", False))

    def is_computer_halt_insecure_enabled(self) -> bool:
        """Return True when provider-flagged Computer Use actions require explicit confirmation."""
        return bool(self.window.core.config.get(self.COMPUTER_HALT_INSECURE_KEY, True))

    @staticmethod
    def _decision_value(value) -> str:
        """Normalize SDK enum/string safety decision values."""
        if value is None:
            return ""
        raw = getattr(value, "value", value)
        text = str(raw).strip().lower()
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        return text

    def has_pending_computer_safety(self, ctx) -> bool:
        """Return True if a provider marked the current Computer Use action as requiring confirmation."""
        if ctx is None or not isinstance(getattr(ctx, "extra", None), dict):
            return False

        extra = ctx.extra
        checks = extra.get("pending_safety_checks")
        if isinstance(checks, list) and len(checks) > 0:
            return True

        decisions = extra.get("computer_safety_decisions")
        if isinstance(decisions, list):
            for item in decisions:
                if not isinstance(item, dict):
                    continue
                if self._decision_value(item.get("decision")) == "require_confirmation":
                    return True
        return False

    def should_halt_computer(self, ctx) -> bool:
        """Return True if a pending Computer Use action must wait for user confirmation."""
        if not self.has_pending_computer_safety(ctx):
            return False
        if self.is_computer_sandbox():
            return False
        if not self.is_computer_halt_insecure_enabled():
            return False
        extra = getattr(ctx, "extra", None) or {}
        return not bool(extra.get("computer_safety_confirmed", False))

    def can_acknowledge_computer_safety(self, ctx) -> bool:
        """Return True when provider safety checks may be acknowledged back to the API."""
        if not self.has_pending_computer_safety(ctx):
            return False
        if self.is_computer_sandbox() or not self.is_computer_halt_insecure_enabled():
            return True
        extra = getattr(ctx, "extra", None) or {}
        return bool(extra.get("computer_safety_confirmed", False))

    @staticmethod
    def mark_computer_safety_confirmed(ctx):
        """Mark a paused Computer Use operation as explicitly confirmed by the user."""
        if ctx is None:
            return
        if not isinstance(getattr(ctx, "extra", None), dict):
            ctx.extra = {}
        ctx.extra["computer_safety_confirmed"] = True
        ctx.extra["computer_safety_waiting"] = False

    def get_computer_safety_messages(self, ctx) -> List[str]:
        """Return provider-supplied safety explanations for display in the chat."""
        messages: List[str] = []
        if ctx is None or not isinstance(getattr(ctx, "extra", None), dict):
            return messages

        for check in ctx.extra.get("pending_safety_checks") or []:
            if isinstance(check, dict):
                msg = str(check.get("message") or check.get("code") or "").strip()
                if msg and msg not in messages:
                    messages.append(msg)

        for item in ctx.extra.get("computer_safety_decisions") or []:
            if isinstance(item, dict):
                msg = str(item.get("explanation") or "").strip()
                if msg and msg not in messages:
                    messages.append(msg)
        return messages

    def ensure_command(self, command: str, sandbox: bool = False) -> List[str]:
        """Validate a host system command against the current OS whitelist/blacklist."""
        if sandbox:
            return self.extract_command_names(command)

        names = self.extract_command_names(command)
        if not names:
            return names

        if self.is_command_whitelist_enabled():
            allowed = self.get_command_whitelist()
            denied = [name for name in names if name not in allowed]
            if denied:
                raise SecurityError(
                    "Permission denied - system command '{}' is not allowed by the enabled whitelist. "
                    "Edit Settings -> Security -> {} -> System commands whitelist. "
                    "Whitelist rules take precedence over the blacklist."
                    .format(denied[0], self.get_os_label())
                )
            return names

        blocked = self.get_command_blacklist()
        denied = [name for name in names if name in blocked]
        if denied:
            raise SecurityError(
                "Permission denied - system command '{}' is blocked by the blacklist. "
                "Edit Settings -> Security -> {} -> System commands blacklist."
                .format(denied[0], self.get_os_label())
            )
        return names
