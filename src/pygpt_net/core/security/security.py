#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.18 16:00:00                  #
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

    def is_in_workdir(self, path: str) -> bool:
        """Check path containment using resolved paths (including symlink resolution)."""
        try:
            workdir = self._normalize_path(self.get_workdir())
            target = self._normalize_path(path)
            return os.path.commonpath([workdir, target]) == workdir
        except (TypeError, ValueError, OSError):
            return False

    def ensure_read(self, path: str, sandbox: bool = False) -> str:
        """Validate a local file/directory read. Security restrictions are bypassed in sandbox mode."""
        if path is None or str(path).strip() == "":
            return path
        if sandbox or not self.is_read_restricted() or self.is_in_workdir(path):
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
        if sandbox or not self.is_write_restricted() or self.is_in_workdir(path):
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
