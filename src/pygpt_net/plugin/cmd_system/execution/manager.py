#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 11:00:00                  #
# ================================================== #

from .docker import DockerBackend
from .host import HostBackend
from ..sandbox import SandboxMode


class ExecutionManager:
    """Resolve System/OS execution backend from the Sandbox option."""

    BACKENDS = {
        SandboxMode.DISABLED.value: HostBackend,
        SandboxMode.DOCKER.value: DockerBackend,
    }

    def __init__(self, plugin=None):
        self.plugin = plugin
        self._instances = {}

    @classmethod
    def register_backend(cls, mode: str | SandboxMode, backend_cls):
        """Register a backend implementation for a sandbox mode."""
        key = mode.value if isinstance(mode, SandboxMode) else str(mode)
        cls.BACKENDS[key] = backend_cls

    def get_mode(self) -> SandboxMode:
        value = self.plugin.get_option_value("sandbox")
        if isinstance(value, bool):
            return SandboxMode.DOCKER if value else SandboxMode.DISABLED
        if value in (None, ""):
            return SandboxMode.DISABLED
        try:
            return SandboxMode(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported System/OS sandbox mode: {value}") from exc

    def get_backend(self, mode: str | SandboxMode | None = None):
        """Return a cached backend instance for the requested/current mode."""
        if mode is None:
            mode = self.get_mode()
        key = mode.value if isinstance(mode, SandboxMode) else str(mode)
        backend_cls = self.BACKENDS.get(key)
        if backend_cls is None:
            raise ValueError(f"No System/OS execution backend registered for mode: {key}")
        if key not in self._instances or not isinstance(self._instances[key], backend_cls):
            self._instances[key] = backend_cls(self.plugin)
        return self._instances[key]
