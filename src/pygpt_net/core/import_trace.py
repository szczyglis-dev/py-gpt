#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 15:45:00                  #
# ================================================== #

"""Optional import tracer used for startup diagnostics.

The tracer is intentionally based only on Python's standard library and is
installed only when explicitly requested from the command line.  It wraps the
internal import dispatcher without changing finder/loader order, so normal
module resolution remains untouched.
"""

from __future__ import annotations

import importlib._bootstrap as _bootstrap
import linecache
import os
import sys
import time
from types import FrameType, ModuleType
from typing import Optional


TRACE_FLAG = "--trace-imports"
TRACE_DEPTH_FLAG = "--trace-imports-depth"
TRACE_IGNORE_FLAG = "--ignore"
TRACE_ONLY_FLAG = "--only"
DEFAULT_DEPTH = 6
MAX_DEPTH = 50


class ImportTracer:
    """Log every module loaded for the first time after tracer installation."""

    def __init__(
        self,
        depth: int = DEFAULT_DEPTH,
        ignore: Optional[list[str]] = None,
        only: Optional[list[str]] = None,
    ):
        self.depth = max(1, min(int(depth), MAX_DEPTH))
        self.ignore = tuple(x for x in (ignore or []) if x)
        self.only = tuple(x for x in (only or []) if x)
        self.started_at = time.perf_counter()
        self.seen = set(sys.modules)
        self.logged = set()
        self.counter = 0
        self._original_find_and_load = None
        self._trace_file = os.path.abspath(__file__)

    def install(self) -> None:
        """Install the tracer once for the current process."""
        current = _bootstrap._find_and_load
        if getattr(current, "__pygpt_import_tracer__", False):
            return

        self._original_find_and_load = current
        tracer = self

        def traced_find_and_load(name, import_):
            # Fast path for modules already present before this import request.
            if name in sys.modules:
                return current(name, import_)

            stack = tracer._capture_stack()
            module = current(name, import_)

            # Only successful, first-time loads are printed.  Nested imports
            # are logged by their own traced_find_and_load invocation first.
            if name not in tracer.seen and name not in tracer.logged:
                tracer.seen.add(name)
                tracer.logged.add(name)
                if tracer._should_log(name):
                    tracer._log_module(name, module, stack)

            return module

        traced_find_and_load.__pygpt_import_tracer__ = True
        traced_find_and_load.__wrapped__ = current
        _bootstrap._find_and_load = traced_find_and_load

        options = [f"stack depth={self.depth}"]
        if self.only:
            options.append("only=" + ",".join(self.only))
        if self.ignore:
            options.append("ignore=" + ",".join(self.ignore))
        print(
            f"[IMPORT TRACE] enabled ({'; '.join(options)})",
            flush=True,
        )

    def uninstall(self) -> None:
        """Restore the original import dispatcher, if this instance installed it."""
        if self._original_find_and_load is None:
            return
        if getattr(_bootstrap._find_and_load, "__pygpt_import_tracer__", False):
            _bootstrap._find_and_load = self._original_find_and_load
        self._original_find_and_load = None

    def _should_log(self, name: str) -> bool:
        """Return True when a module name passes configured prefix filters."""
        if self.only and not name.startswith(self.only):
            return False
        if self.ignore and name.startswith(self.ignore):
            return False
        return True

    def _capture_stack(self):
        """Capture a compact caller chain without importing traceback/inspect."""
        frames = []
        try:
            frame = sys._getframe(2)
        except ValueError:
            return frames

        while frame is not None and len(frames) < self.depth:
            if self._is_useful_frame(frame):
                filename = frame.f_code.co_filename
                lineno = frame.f_lineno
                frames.append(
                    (
                        self._short_path(filename),
                        lineno,
                        frame.f_code.co_name,
                        linecache.getline(filename, lineno).strip(),
                    )
                )
            frame = frame.f_back
        return frames

    def _is_useful_frame(self, frame: FrameType) -> bool:
        filename = frame.f_code.co_filename
        if not filename:
            return False
        if filename == self._trace_file:
            return False
        if filename.startswith("<frozen importlib"):
            return False
        module_name = frame.f_globals.get("__name__", "")
        if module_name in {"importlib", "importlib._bootstrap", "importlib._bootstrap_external"}:
            return False
        return True

    @staticmethod
    def _short_path(filename: str) -> str:
        """Keep trace paths readable while preserving useful package context."""
        if not filename:
            return "<unknown>"
        if filename.startswith("<"):
            return filename

        normalized = os.path.abspath(filename).replace("\\", "/")

        marker = "/pygpt_net/"
        if marker in normalized:
            return "pygpt_net/" + normalized.split(marker, 1)[1]

        marker = "/site-packages/"
        if marker in normalized:
            return "site-packages/" + normalized.split(marker, 1)[1]

        marker = "/dist-packages/"
        if marker in normalized:
            return "dist-packages/" + normalized.split(marker, 1)[1]

        try:
            cwd = os.path.abspath(os.getcwd()).replace("\\", "/").rstrip("/")
            if cwd and normalized.startswith(cwd + "/"):
                return normalized[len(cwd) + 1:]
        except Exception:
            pass

        return normalized

    @staticmethod
    def _module_origin(module: ModuleType) -> str:
        filename = getattr(module, "__file__", None)
        if filename:
            return ImportTracer._short_path(filename)

        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None) if spec is not None else None
        if origin:
            return str(origin)
        return "<unknown>"

    def _log_module(self, name: str, module: ModuleType, stack) -> None:
        self.counter += 1
        elapsed = time.perf_counter() - self.started_at
        origin = self._module_origin(module)

        lines = [
            f"[IMPORT {self.counter:04d} +{elapsed:8.3f}s] {name}",
            f"  origin: {origin}",
        ]
        if stack:
            lines.append("  requested by:")
            for idx, (filename, lineno, funcname, source) in enumerate(stack, 1):
                lines.append(
                    f"    {idx}. {filename}:{lineno} in {funcname}()"
                )
                if source:
                    lines.append(f"       {source}")
        else:
            lines.append("  requested by: <no Python caller frame>")

        print("\n".join(lines), flush=True)


def _parse_depth(argv: list[str]) -> int:
    depth = DEFAULT_DEPTH
    for idx, arg in enumerate(argv):
        if arg.startswith(TRACE_DEPTH_FLAG + "="):
            try:
                depth = int(arg.split("=", 1)[1])
            except (TypeError, ValueError):
                pass
            break
        if arg == TRACE_DEPTH_FLAG and idx + 1 < len(argv):
            try:
                depth = int(argv[idx + 1])
            except (TypeError, ValueError):
                pass
            break
    return max(1, min(depth, MAX_DEPTH))


def _parse_prefixes(argv: list[str], flag: str) -> list[str]:
    """Collect repeated prefix filters from ``--flag value`` and ``--flag=value``."""
    values = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg.startswith(flag + "="):
            value = arg.split("=", 1)[1].strip()
            values.extend(
                prefix.strip()
                for prefix in value.split(",")
                if prefix.strip()
            )
            idx += 1
            continue
        if arg == flag and idx + 1 < len(argv):
            value = argv[idx + 1].strip()
            if value and not value.startswith("--"):
                values.extend(
                    prefix.strip()
                    for prefix in value.split(",")
                    if prefix.strip()
                )
                idx += 2
                continue
        idx += 1
    return values


def _consume_args(argv: list[str]) -> None:
    """Remove tracer-only switches before QApplication sees argv."""
    cleaned = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == TRACE_FLAG:
            idx += 1
            continue
        if arg.startswith(TRACE_DEPTH_FLAG + "="):
            idx += 1
            continue
        if arg == TRACE_DEPTH_FLAG:
            idx += 1
            if idx < len(argv):
                try:
                    int(argv[idx])
                except (TypeError, ValueError):
                    pass
                else:
                    idx += 1
            continue
        if arg.startswith(TRACE_IGNORE_FLAG + "=") or arg.startswith(TRACE_ONLY_FLAG + "="):
            idx += 1
            continue
        if arg in {TRACE_IGNORE_FLAG, TRACE_ONLY_FLAG}:
            idx += 1
            if idx < len(argv) and not argv[idx].startswith("--"):
                idx += 1
            continue
        cleaned.append(arg)
        idx += 1
    argv[:] = cleaned


def enable_from_argv(argv: Optional[list[str]] = None) -> Optional[ImportTracer]:
    """Enable import tracing when ``--trace-imports`` is present.

    The tracer flag, optional depth, and repeated ``--ignore`` / ``--only``
    prefix filters are removed from ``argv`` after parsing so they never reach
    Qt or application-level parsers.
    """
    if argv is None:
        argv = sys.argv
    if TRACE_FLAG not in argv:
        return None

    depth = _parse_depth(argv)
    ignore = _parse_prefixes(argv, TRACE_IGNORE_FLAG)
    only = _parse_prefixes(argv, TRACE_ONLY_FLAG)
    _consume_args(argv)

    tracer = ImportTracer(depth=depth, ignore=ignore, only=only)
    tracer.install()
    return tracer
