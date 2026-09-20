#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 12:00:00                  #
# ================================================== #

from __future__ import annotations

import ctypes
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional, Sequence

from .packages import (
    BUILTIN_BASE_PACKAGES,
    get_builtin_environment_packages,
    get_builtin_packages,
)


class BuiltinSandboxError(RuntimeError):
    """Raised when the built-in execution runtime cannot be prepared."""


class BuiltinSandboxRuntime:
    """Managed Python runtime used by the built-in Code/System sandboxes.

    ``uv`` manages the interpreter/virtual environment, while the child process
    is additionally restricted with an OS-specific best-effort sandbox:

    * Linux: Landlock filesystem allow-list (when supported by the kernel).
    * macOS: ``/usr/bin/sandbox-exec`` Seatbelt profile (when available).
    * Windows: a Job Object with kill-on-close plus an isolated HOME/TEMP/venv.

    The sandbox venv is intentionally independent from the Python environment
    used to run/freeze PyGPT itself.
    """

    PYTHON_VERSION = "3.12"
    _prepare_lock = threading.RLock()
    _LANDLOCK_LAUNCHER = ".pygpt_landlock.py"
    _MARKER = ".pygpt-sandbox.json"
    _FALLBACK_WARNING_PREFIX = "[BUILT-IN SANDBOX] WARNING:"

    def __init__(self, window, name: str):
        if name not in {"python", "os"}:
            raise ValueError(f"Unsupported built-in sandbox name: {name}")
        self.window = window
        self.name = name
        self._landlock_preflight_result = None
        self._landlock_preflight_details = ""
        self._fallback_warning = None

    # ------------------------------------------------------------------
    # Paths / environment
    # ------------------------------------------------------------------

    @property
    def profile_root(self) -> str:
        return os.path.realpath(self.window.core.config.get_user_path())

    @property
    def sandbox_root(self) -> str:
        return os.path.join(self.profile_root, "sandbox")

    @property
    def runtime_root(self) -> str:
        return os.path.join(self.sandbox_root, "runtime")

    @property
    def cache_root(self) -> str:
        return os.path.join(self.sandbox_root, "cache")

    @property
    def venv_root(self) -> str:
        return os.path.join(self.sandbox_root, self.name)

    @property
    def state_root(self) -> str:
        return os.path.join(self.sandbox_root, "state", self.name)

    @property
    def private_root(self) -> str:
        # Keep runtime state outside the venv target. Creating HOME/TMP before
        # ``uv venv`` must not make ``sandbox/python`` or ``sandbox/os`` look
        # like a pre-existing non-venv directory.
        return self.state_root

    @property
    def home_dir(self) -> str:
        return os.path.join(self.private_root, "home")

    @property
    def temp_dir(self) -> str:
        return os.path.join(self.private_root, "tmp")

    @property
    def app_temp_dir(self) -> str:
        """Shared PyGPT temporary directory used by interpreter state files."""
        return os.path.realpath(self.window.core.config.get_user_dir("tmp"))

    @property
    def marker_path(self) -> str:
        return os.path.join(self.venv_root, self._MARKER)

    @property
    def python_bin(self) -> str:
        if os.name == "nt":
            return os.path.join(self.venv_root, "Scripts", "python.exe")
        return os.path.join(self.venv_root, "bin", "python")

    @property
    def bin_dir(self) -> str:
        if os.name == "nt":
            return os.path.join(self.venv_root, "Scripts")
        return os.path.join(self.venv_root, "bin")

    @property
    def pip_bin(self) -> str:
        if os.name == "nt":
            return os.path.join(self.bin_dir, "pip.exe")
        return os.path.join(self.bin_dir, "pip")

    def get_data_dir(self, ctx=None) -> str:
        return os.path.realpath(self.window.core.filesystem.get_data_dir(ctx=ctx))

    def _ensure_directories(self, ctx=None):
        for path in (
            self.sandbox_root,
            self.runtime_root,
            self.cache_root,
            self.app_temp_dir,
            self.get_data_dir(ctx=ctx),
        ):
            os.makedirs(path, exist_ok=True)

    def _build_env(self, ctx=None) -> dict[str, str]:
        self._ensure_private_dirs()
        env = dict(os.environ)
        parent_virtual_env = str(env.get("VIRTUAL_ENV") or "").strip()
        parent_path = str(env.get("PATH") or "")
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONSTARTUP", None)
        env.pop("PYTHONBREAKPOINT", None)
        env["VIRTUAL_ENV"] = self.venv_root
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        env["HOME"] = self.home_dir
        env["USERPROFILE"] = self.home_dir
        env["TMPDIR"] = self.temp_dir
        env["TMP"] = self.temp_dir
        env["TEMP"] = self.temp_dir
        env["UV_CACHE_DIR"] = self.cache_root
        env["UV_PYTHON_INSTALL_DIR"] = self.runtime_root
        env["UV_PYTHON_INSTALL_REGISTRY"] = "0"
        env["UV_PYTHON_NO_REGISTRY"] = "1"
        env["UV_NO_CONFIG"] = "1"

        # Never inherit executable scripts from the virtual environment used to
        # run PyGPT itself.  If e.g. the sandbox does not contain a bare `pip`,
        # falling through to the application's venv would make `pip list` and
        # package installs operate on the wrong environment.
        blocked_roots = []
        if parent_virtual_env:
            blocked_roots.append(os.path.realpath(parent_virtual_env))
        if getattr(sys, "prefix", None) and getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
            blocked_roots.append(os.path.realpath(sys.prefix))

        # uv is an implementation detail and all runtime-manager calls use its
        # absolute path.  Do not expose the directory containing PyGPT's own uv
        # executable in the child PATH: in source/pip installs that directory is
        # usually the application's venv and may also contain its `pip`, Python,
        # and unrelated console scripts.
        path_parts = [self.bin_dir]
        seen = {os.path.normcase(os.path.realpath(p)) for p in path_parts if p}
        for item in parent_path.split(os.pathsep):
            item = item.strip()
            if not item:
                continue
            real = os.path.realpath(item)
            if any(self._is_within(real, root) for root in blocked_roots):
                continue
            key = os.path.normcase(real)
            if key in seen:
                continue
            seen.add(key)
            path_parts.append(item)
        env["PATH"] = os.pathsep.join(path_parts)
        return env

    def _ensure_private_dirs(self):
        os.makedirs(self.home_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # uv / venv provisioning
    # ------------------------------------------------------------------

    def find_uv(self) -> str:
        configured = str(os.environ.get("PYGPT_UV_BIN") or "").strip()
        if configured and os.path.isfile(configured):
            return os.path.realpath(configured)

        candidates = []
        executable_name = "uv.exe" if os.name == "nt" else "uv"

        # PyInstaller onedir/onefile locations.
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            candidates.append(os.path.join(bundle_root, executable_name))
        candidates.append(os.path.join(os.path.dirname(sys.executable), executable_name))

        try:
            import uv  # type: ignore
            try:
                candidates.append(os.fspath(uv.find_uv_bin()))
            except (AttributeError, FileNotFoundError, OSError):
                pass
        except ImportError:
            pass

        found = shutil.which(executable_name) or shutil.which("uv")
        if found:
            candidates.append(found)

        for path in candidates:
            if path and os.path.isfile(path):
                return os.path.realpath(path)

        raise BuiltinSandboxError(
            "Built-in sandbox requires the 'uv' executable. Install the PyGPT "
            "dependency 'uv' or use a package/build that bundles it."
        )

    def _base_python(self) -> Optional[str]:
        """Return a packaged interpreter that must be reused, if configured.

        Snap is intentionally configured this way: strict confinement may deny
        executing a freshly downloaded interpreter from writable storage. Other
        builds use uv-managed CPython in ``sandbox/runtime``.
        """
        path = str(os.environ.get("PYGPT_SANDBOX_PYTHON") or "").strip()
        if path and os.path.isfile(path):
            return os.path.realpath(path)
        return None

    def _marker_data(self) -> dict:
        return {
            "version": 5,
            "python": self.PYTHON_VERSION,
            "base_python": self._base_python() or "managed",
            "name": self.name,
            "packages": get_builtin_environment_packages(self.name),
        }

    def _marker_matches(self) -> bool:
        if not os.path.isfile(self.python_bin) or not os.path.isfile(self.marker_path):
            return False
        try:
            with open(self.marker_path, "r", encoding="utf-8") as handle:
                current = json.load(handle)
            return current == self._marker_data()
        except (OSError, ValueError, TypeError):
            return False

    def is_ready(self) -> bool:
        """Return True when the managed environment matches the current spec."""
        return self._marker_matches()

    def _is_existing_venv(self) -> bool:
        return (
            os.path.isfile(os.path.join(self.venv_root, "pyvenv.cfg"))
            and os.path.isfile(self.python_bin)
        )

    def _prepare_venv_target(self):
        """Remove only stale/non-venv contents from our managed venv path.

        Older Built-in sandbox builds created ``.pygpt/tmp`` inside the venv
        target before calling ``uv venv``. Recent uv versions intentionally
        refuse to clear a directory that is not already a virtual environment.
        Clean that stale managed directory ourselves, while leaving valid venvs
        for uv's normal ``--clear`` recreation path.
        """
        if not os.path.lexists(self.venv_root) or self._is_existing_venv():
            return

        sandbox_root = os.path.realpath(self.sandbox_root)
        target = os.path.realpath(self.venv_root)
        expected = os.path.realpath(os.path.join(sandbox_root, self.name))
        if target != expected or os.path.dirname(target) != sandbox_root:
            raise BuiltinSandboxError(
                f"Refusing to clean unexpected built-in sandbox path: {target}"
            )

        if os.path.islink(self.venv_root) or os.path.isfile(self.venv_root):
            os.unlink(self.venv_root)
        else:
            shutil.rmtree(self.venv_root)

    def ensure_ready(self, ctx=None) -> str:
        """Create/update the sandbox venv and return its Python executable."""
        with self._prepare_lock:
            self._ensure_directories(ctx=ctx)
            if self._marker_matches():
                self._ensure_private_dirs()
                return self.python_bin

            # A previous/aborted provisioning attempt may have left a managed
            # directory at the venv target that is not actually a venv. Clean
            # only that exact managed path before asking uv to recreate it.
            self._prepare_venv_target()

            uv_bin = self.find_uv()
            env = dict(os.environ)
            env["UV_CACHE_DIR"] = self.cache_root
            env["UV_PYTHON_INSTALL_DIR"] = self.runtime_root
            env["UV_PYTHON_INSTALL_REGISTRY"] = "0"
            env["UV_PYTHON_NO_REGISTRY"] = "1"
            env["UV_NO_CONFIG"] = "1"

            base_python = self._base_python()
            if base_python:
                venv_python = base_python
                python_flags = ["--no-managed-python", "--no-python-downloads"]
            else:
                # Install/verify the requested managed runtime first. ``python
                # find`` does not download missing runtimes in every uv release.
                install = subprocess.run(
                    [
                        uv_bin, "python", "install", self.PYTHON_VERSION,
                        "--install-dir", self.runtime_root,
                        "--managed-python", "--no-config",
                    ],
                    cwd=self.sandbox_root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if install.returncode != 0:
                    details = (install.stderr or install.stdout or b"").decode(
                        "utf-8", errors="replace"
                    ).strip()
                    raise BuiltinSandboxError(
                        f"Unable to install managed Python for built-in sandbox: {details}"
                    )

                # Resolve uv's minor-version alias to the concrete patch-specific
                # interpreter before creating the venv. uv intentionally exposes
                # e.g. cpython-3.12-... as a symlink to cpython-3.12.14-...; using
                # the canonical interpreter avoids mixed base_prefix/exec_prefix
                # paths when the child is later restricted by Landlock/Seatbelt.
                find = subprocess.run(
                    [
                        uv_bin, "python", "find", self.PYTHON_VERSION,
                        "--managed-python", "--no-python-downloads", "--no-config",
                    ],
                    cwd=self.sandbox_root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if find.returncode != 0:
                    details = (find.stderr or find.stdout or b"").decode(
                        "utf-8", errors="replace"
                    ).strip()
                    raise BuiltinSandboxError(
                        f"Unable to resolve managed Python for built-in sandbox: {details}"
                    )
                discovered = (find.stdout or b"").decode(
                    "utf-8", errors="replace"
                ).strip().splitlines()
                venv_python = os.path.realpath(discovered[-1].strip()) if discovered else ""
                if not venv_python or not os.path.isfile(venv_python):
                    raise BuiltinSandboxError(
                        "uv did not return a usable managed Python executable"
                    )
                python_flags = ["--no-python-downloads"]

            # uv 0.10+ intentionally points managed venv interpreters at a
            # minor-version intermediary (e.g. cpython-3.12-linux-...) so uv can
            # transparently move them between patch releases.  That symlink is
            # problematic for python-build-standalone when a filesystem sandbox
            # is applied: CPython can resolve base_prefix and base_exec_prefix
            # through different paths and fail before importing `encodings`.
            #
            # Keep uv responsible for installing the managed CPython and for all
            # package operations, but create managed venvs with the concrete
            # patch-specific interpreter and real executable copies.  Packaged
            # interpreters (notably Snap) keep using `uv venv`, because copying
            # an executable out of a confined read-only package may not be
            # executable from writable storage.
            if base_python:
                command = [
                    uv_bin,
                    "venv",
                    self.venv_root,
                    "--clear",
                    "--no-config",
                    "--python",
                    venv_python,
                    *python_flags,
                ]
                create_error = "Unable to start uv"
            else:
                command = [
                    venv_python,
                    "-m",
                    "venv",
                    "--clear",
                    "--copies",
                    "--without-pip",
                    self.venv_root,
                ]
                create_error = "Unable to start managed Python"

            try:
                result = subprocess.run(
                    command,
                    cwd=self.sandbox_root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            except OSError as exc:
                raise BuiltinSandboxError(f"{create_error}: {exc}") from exc

            if result.returncode != 0 or not os.path.isfile(self.python_bin):
                stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
                stdout = (result.stdout or b"").decode("utf-8", errors="replace").strip()
                details = stderr or stdout or f"venv creation exited with code {result.returncode}"
                raise BuiltinSandboxError(f"Unable to create built-in sandbox environment: {details}")

            # A managed venv must identify itself as the venv before we install
            # anything into it.  This also catches future uv/PBS path-layout
            # regressions early with a useful error instead of a fatal CPython
            # bootstrap traceback under Landlock.
            identity_code = (
                "import encodings, os, sys; "
                "print(os.path.realpath(sys.prefix)); "
                "print(os.path.realpath(sys.base_prefix))"
            )
            identity = subprocess.run(
                [self.python_bin, "-I", "-c", identity_code],
                cwd=self.sandbox_root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            identity_lines = (identity.stdout or b"").decode(
                "utf-8", errors="replace"
            ).strip().splitlines()
            if (
                identity.returncode != 0
                or not identity_lines
                or os.path.realpath(identity_lines[0]) != os.path.realpath(self.venv_root)
            ):
                details = (identity.stderr or identity.stdout or b"").decode(
                    "utf-8", errors="replace"
                ).strip() or "sandbox Python did not report the virtual environment as sys.prefix"
                raise BuiltinSandboxError(
                    f"Built-in sandbox virtual environment is invalid: {details}"
                )

            # Seed pip from CPython's bundled ensurepip instead of contacting
            # PyPI during environment creation.  --default-pip is important:
            # without it ensurepip may create only pip3/pip3.x, letting a bare
            # `pip` command fall through to the PyGPT application's own venv.
            seed = subprocess.run(
                [self.python_bin, "-m", "ensurepip", "--upgrade", "--default-pip"],
                cwd=self.sandbox_root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if seed.returncode != 0:
                details = (seed.stderr or seed.stdout or b"").decode(
                    "utf-8", errors="replace"
                ).strip()
                raise BuiltinSandboxError(
                    f"Unable to seed pip in the built-in sandbox environment: {details}"
                )

            # Keep packaging tools current, just like the stock Docker images.
            bootstrap = subprocess.run(
                [
                    uv_bin, "pip", "install", "--upgrade",
                    "--python", self.python_bin,
                    "--no-config",
                    *BUILTIN_BASE_PACKAGES,
                ],
                cwd=self.sandbox_root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if bootstrap.returncode != 0:
                details = (bootstrap.stderr or bootstrap.stdout or b"").decode(
                    "utf-8", errors="replace"
                ).strip()
                raise BuiltinSandboxError(
                    "Unable to install base packages in the built-in sandbox "
                    f"environment: {details}"
                )
            if not os.path.isfile(self.pip_bin):
                raise BuiltinSandboxError(
                    "Built-in sandbox provisioning did not create its own pip "
                    f"executable at: {self.pip_bin}"
                )

            packages = get_builtin_packages(self.name)
            if packages:
                install_packages = subprocess.run(
                    [
                        uv_bin, "pip", "install",
                        "--python", self.python_bin,
                        "--no-config",
                        *packages,
                    ],
                    cwd=self.sandbox_root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                if install_packages.returncode != 0:
                    details = (
                        install_packages.stderr or install_packages.stdout or b""
                    ).decode("utf-8", errors="replace").strip()
                    raise BuiltinSandboxError(
                        "Unable to install default packages in the built-in "
                        f"sandbox environment: {details}"
                    )

            self._ensure_private_dirs()
            with open(self.marker_path, "w", encoding="utf-8") as handle:
                json.dump(self._marker_data(), handle, indent=2, sort_keys=True)
            # A recreated venv/runtime needs a fresh Landlock compatibility probe.
            self._landlock_preflight_result = None
            return self.python_bin

    # ------------------------------------------------------------------
    # Files / process execution
    # ------------------------------------------------------------------

    @staticmethod
    def _is_within(path: str, root: str) -> bool:
        try:
            path = os.path.normcase(os.path.realpath(path))
            root = os.path.normcase(os.path.realpath(root))
            return os.path.commonpath([path, root]) == root
        except (OSError, TypeError, ValueError):
            return False

    def resolve_data_path(self, path: str, ctx=None, allow_internal: bool = False) -> str:
        """Resolve a tool path and reject host paths outside the sandbox roots."""
        if not path:
            raise BuiltinSandboxError("Empty path")
        data_dir = self.get_data_dir(ctx=ctx)
        resolved = os.path.realpath(path if os.path.isabs(path) else os.path.join(data_dir, path))
        if self._is_within(resolved, data_dir):
            return resolved
        if allow_internal and self._is_within(resolved, self.venv_root):
            return resolved
        raise BuiltinSandboxError(
            f"Built-in sandbox path is outside the data directory: {resolved}. "
            f"Allowed data directory: {data_dir}"
        )

    def temp_path(self, filename: str) -> str:
        """Return a PyGPT interpreter temp path available inside the sandbox."""
        os.makedirs(self.app_temp_dir, exist_ok=True)
        safe_name = os.path.basename(str(filename))
        return os.path.join(self.app_temp_dir, safe_name)

    def run_python(self, path: str, ctx=None):
        self.ensure_ready(ctx=ctx)
        path = os.path.realpath(path)
        return self._communicate([self.python_bin, "-u", path], ctx=ctx)

    def run_shell(self, command: str, ctx=None):
        self.ensure_ready(ctx=ctx)
        if os.name == "nt":
            shell = os.environ.get("COMSPEC") or r"C:\Windows\System32\cmd.exe"
            argv = [shell, "/d", "/s", "/c", command]
        else:
            shell = "/bin/sh"
            argv = [shell, "-c", command]
        return self._communicate(argv, ctx=ctx)

    def _warn_isolation_fallback(self, reason: str):
        """Log an explicit warning when OS isolation falls back to subprocess-only."""
        reason = str(reason or "unknown reason").strip()
        message = (
            f"{self._FALLBACK_WARNING_PREFIX} {self.name}: OS filesystem isolation "
            f"is unavailable; using separate-process isolation only. Reason: {reason}"
        )
        if message == self._fallback_warning:
            return
        self._fallback_warning = message
        # Always make this visible in the process console, regardless of the
        # configured app log level. Keep it in app.log as a warning as well.
        try:
            print(message)
        except Exception:
            pass
        try:
            logger = logging.getLogger()
            if logger.hasHandlers():
                logger.warning(message)
        except Exception:
            pass

    def _communicate(self, argv: Sequence[str], ctx=None):
        data_dir = self.get_data_dir(ctx=ctx)
        env = self._build_env(ctx=ctx)
        command = list(argv)

        if sys.platform == "darwin":
            command = self._wrap_macos(command, data_dir)
        elif sys.platform.startswith("linux"):
            env["PYGPT_SANDBOX_RO"] = os.pathsep.join(self._linux_read_roots())
            env["PYGPT_SANDBOX_RW"] = os.pathsep.join([
                data_dir, self.venv_root, self.cache_root, self.state_root,
                self.app_temp_dir,
            ])
            # Verify that the uv-managed interpreter can fully initialize after
            # Landlock is applied. If a kernel/runtime combination rejects one
            # of Python's own runtime paths, degrade to process isolation rather
            # than launching a broken interpreter.
            if self._linux_landlock_preflight(data_dir, env):
                command = self._wrap_linux(command, data_dir)
            else:
                self._warn_isolation_fallback(self._landlock_preflight_details)

        creationflags = 0
        start_new_session = False
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            start_new_session = True

        process = subprocess.Popen(
            command,
            cwd=data_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )

        job = self._attach_windows_job(process) if os.name == "nt" else None
        if os.name == "nt" and not job:
            self._warn_isolation_fallback(
                "Windows Job Object could not be attached to the child process"
            )
        try:
            return process.communicate()
        finally:
            if job:
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
                kernel32.CloseHandle.restype = wintypes.BOOL
                kernel32.CloseHandle(job)

    # ------------------------------------------------------------------
    # Linux: Landlock
    # ------------------------------------------------------------------

    def _landlock_launcher_path(self) -> str:
        return os.path.join(self.private_root, self._LANDLOCK_LAUNCHER)

    def _write_landlock_launcher(self) -> str:
        self._ensure_private_dirs()
        path = self._landlock_launcher_path()
        source = r'''#!/usr/bin/env python3
import ctypes
import errno
import os
import sys

# Linux Landlock syscall numbers are part of the generic syscall table used by
# the supported PyGPT Linux architectures (x86_64/aarch64).
SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_RULE_PATH_BENEATH = 1
PR_SET_NO_NEW_PRIVS = 38

EXECUTE = 1 << 0
WRITE_FILE = 1 << 1
READ_FILE = 1 << 2
READ_DIR = 1 << 3
REMOVE_DIR = 1 << 4
REMOVE_FILE = 1 << 5
MAKE_CHAR = 1 << 6
MAKE_DIR = 1 << 7
MAKE_REG = 1 << 8
MAKE_SOCK = 1 << 9
MAKE_FIFO = 1 << 10
MAKE_BLOCK = 1 << 11
MAKE_SYM = 1 << 12
REFER = 1 << 13
TRUNCATE = 1 << 14
IOCTL_DEV = 1 << 15
RESOLVE_UNIX = 1 << 16

SCOPE_ABSTRACT_UNIX_SOCKET = 1 << 0
SCOPE_SIGNAL = 1 << 1
LANDLOCK_ABI = None

class RulesetAttr(ctypes.Structure):
    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
        ("handled_access_net", ctypes.c_uint64),
        ("scoped", ctypes.c_uint64),
    ]

class PathBeneathAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int)]

libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long


def syscall(number, *args):
    result = libc.syscall(number, *args)
    if result < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return result


def apply_landlock(ro_paths, rw_paths):
    global LANDLOCK_ABI
    try:
        abi = syscall(
            SYS_LANDLOCK_CREATE_RULESET,
            ctypes.c_void_p(),
            ctypes.c_size_t(0),
            ctypes.c_uint32(LANDLOCK_CREATE_RULESET_VERSION),
        )
    except OSError as exc:
        if exc.errno in (errno.ENOSYS, errno.EOPNOTSUPP, errno.EINVAL, errno.EPERM):
            raise RuntimeError(f"Landlock unavailable: {exc}") from exc
        raise

    LANDLOCK_ABI = abi
    handled = (
        EXECUTE | WRITE_FILE | READ_FILE | READ_DIR | REMOVE_DIR | REMOVE_FILE |
        MAKE_CHAR | MAKE_DIR | MAKE_REG | MAKE_SOCK | MAKE_FIFO | MAKE_BLOCK | MAKE_SYM
    )
    if abi >= 2:
        handled |= REFER
    if abi >= 3:
        handled |= TRUNCATE
    if abi >= 5:
        handled |= IOCTL_DEV
    if abi >= 9:
        # Prevent connections to pathname UNIX sockets outside allow-listed
        # writable roots (e.g. Docker/system service sockets).
        handled |= RESOLVE_UNIX

    scoped = 0
    if abi >= 6:
        # Keep abstract UNIX sockets and signals inside the new Landlock
        # domain. TCP/UDP networking remains available for package installs.
        scoped = SCOPE_ABSTRACT_UNIX_SOCKET | SCOPE_SIGNAL

    ruleset_attr = RulesetAttr(
        handled_access_fs=handled,
        handled_access_net=0,
        scoped=scoped,
    )
    if abi < 4:
        ruleset_size = ctypes.sizeof(ctypes.c_uint64)
    elif abi < 6:
        ruleset_size = ctypes.sizeof(ctypes.c_uint64) * 2
    else:
        ruleset_size = ctypes.sizeof(ctypes.c_uint64) * 3
    ruleset_fd = syscall(
        SYS_LANDLOCK_CREATE_RULESET,
        ctypes.byref(ruleset_attr),
        ctypes.c_size_t(ruleset_size),
        ctypes.c_uint32(0),
    )

    read_access = EXECUTE | READ_FILE | READ_DIR
    rw_access = handled
    open_flags = getattr(os, "O_PATH", os.O_RDONLY) | getattr(os, "O_CLOEXEC", 0)

    def add(path, access):
        if not path or not os.path.exists(path):
            return
        fd = os.open(path, open_flags)
        try:
            attr = PathBeneathAttr(allowed_access=access & handled, parent_fd=fd)
            syscall(
                SYS_LANDLOCK_ADD_RULE,
                ruleset_fd,
                ctypes.c_int(LANDLOCK_RULE_PATH_BENEATH),
                ctypes.byref(attr),
                ctypes.c_uint32(0),
            )
        finally:
            os.close(fd)

    try:
        for item in ro_paths:
            add(item, read_access)
        for item in rw_paths:
            add(item, rw_access)
        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            err = ctypes.get_errno()
            raise OSError(err, os.strerror(err))
        syscall(SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, ctypes.c_uint32(0))
    finally:
        os.close(ruleset_fd)
    return True


def main():
    if "--" not in sys.argv:
        raise SystemExit("missing -- separator")
    sep = sys.argv.index("--")
    ro_paths = [p for p in os.environ.get("PYGPT_SANDBOX_RO", "").split(os.pathsep) if p]
    rw_paths = [p for p in os.environ.get("PYGPT_SANDBOX_RW", "").split(os.pathsep) if p]
    try:
        active = apply_landlock(ro_paths, rw_paths)
    except Exception as exc:
        active = False
        print(
            "PYGPT_LANDLOCK_FALLBACK: "
            f"abi={LANDLOCK_ABI if LANDLOCK_ABI is not None else 'unknown'}; "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
    os.environ["PYGPT_BUILTIN_SANDBOX_FS"] = "landlock" if active else "process"
    argv = sys.argv[sep + 1:]
    if not argv:
        raise SystemExit("missing command")
    os.execvpe(argv[0], argv, os.environ)


if __name__ == "__main__":
    main()
'''
        try:
            current = Path(path).read_text(encoding="utf-8") if os.path.isfile(path) else None
        except OSError:
            current = None
        if current != source:
            Path(path).write_text(source, encoding="utf-8")
        return path

    def _linux_read_roots(self) -> list[str]:
        roots = []
        candidates = [
            "/bin", "/sbin", "/usr", "/lib", "/lib64", "/etc",
            "/dev", "/proc", "/sys", self.runtime_root,
        ]
        snap_root = os.environ.get("SNAP")
        if snap_root:
            candidates.append(snap_root)
        base_python = self._base_python()
        if base_python:
            candidates.append(os.path.dirname(base_python))
        seen = set()
        for path in candidates:
            if not path or not os.path.exists(path):
                continue
            real = os.path.realpath(path)
            if real not in seen:
                seen.add(real)
                roots.append(real)
        return roots

    @staticmethod
    def _linux_lsm_info() -> str:
        """Return active Linux Security Modules for fallback diagnostics."""
        try:
            value = Path("/sys/kernel/security/lsm").read_text(encoding="utf-8").strip()
            return value or "unknown"
        except OSError as exc:
            return f"unavailable ({exc})"

    def _linux_landlock_preflight(self, data_dir: str, env: dict[str, str]) -> bool:
        """Return True only when Python can initialize inside our Landlock domain.

        This is intentionally a runtime probe: python-build-standalone layout
        and Landlock behavior both depend on the runtime/kernel versions. A failed probe
        falls back to the existing process-isolation mode instead of making the
        Code Interpreter unusable.
        """
        cached = getattr(self, "_landlock_preflight_result", None)
        if cached is not None:
            return bool(cached)

        launcher = self._write_landlock_launcher()
        probe_path = os.path.join(self.temp_dir, ".landlock-probe")
        try:
            Path(probe_path).write_text("probe", encoding="utf-8")
        except OSError as exc:
            self._landlock_preflight_result = False
            self._landlock_preflight_details = f"unable to create Landlock probe file: {exc}"
            return False

        probe_env = dict(env)
        probe_env["PYGPT_SANDBOX_PROBE"] = probe_path
        # Verify a real path outside the allow-list is denied, not only that the
        # Landlock syscall sequence reported success. The parent of the PyGPT
        # workdir is intentionally not part of RO/RW roots.
        deny_probe = os.path.dirname(self.profile_root.rstrip(os.sep)) or os.sep
        probe_env["PYGPT_SANDBOX_DENY_PROBE"] = deny_probe
        probe_code = """
import encodings
import importlib
import os

if os.environ.get("PYGPT_BUILTIN_SANDBOX_FS") != "landlock":
    print("PYGPT_LANDLOCK_NOT_ACTIVE", file=__import__("sys").stderr)
    raise SystemExit(3)
importlib.import_module("json")
open(os.devnull, "rb").close()
probe_path = os.environ["PYGPT_SANDBOX_PROBE"]
open(probe_path, "rb").close()
with open(probe_path, "ab") as handle:
    handle.write(b"x")
outside_path = os.environ["PYGPT_SANDBOX_DENY_PROBE"]
denied = False
try:
    os.listdir(outside_path)
except PermissionError:
    denied = True
if not denied:
    print(f"PYGPT_LANDLOCK_OUTSIDE_PATH_READABLE: {outside_path}", file=__import__("sys").stderr)
    raise SystemExit(4)
print("PYGPT_LANDLOCK_OK")
"""
        probe = [
            self.python_bin, "-u", launcher, "--",
            self.python_bin, "-I", "-c", probe_code,
        ]
        try:
            result = subprocess.run(
                probe,
                cwd=data_dir,
                env=probe_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
            )
            ok = (
                result.returncode == 0
                and b"PYGPT_LANDLOCK_OK" in (result.stdout or b"")
            )
            if ok:
                self._landlock_preflight_details = ""
            else:
                stdout = (result.stdout or b"").decode("utf-8", errors="replace").strip()
                stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
                detail = stderr or stdout or "no diagnostic output"
                self._landlock_preflight_details = (
                    f"Landlock preflight failed with exit code {result.returncode}: {detail}; "
                    f"active LSMs: {self._linux_lsm_info()}"
                )
        except (OSError, subprocess.SubprocessError) as exc:
            ok = False
            self._landlock_preflight_details = (
                f"Landlock preflight could not run: {exc}; "
                f"active LSMs: {self._linux_lsm_info()}"
            )
        finally:
            try:
                os.unlink(probe_path)
            except OSError:
                pass
        self._landlock_preflight_result = ok
        return ok

    def _wrap_linux(self, argv: list[str], data_dir: str) -> list[str]:
        launcher = self._write_landlock_launcher()
        return [self.python_bin, "-u", launcher, "--", *argv]

    # ------------------------------------------------------------------
    # macOS: Seatbelt sandbox-exec
    # ------------------------------------------------------------------

    @staticmethod
    def _sb_quote(path: str) -> str:
        return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'

    def _macos_profile(self, data_dir: str) -> str:
        read_roots = [
            "/System", "/usr", "/bin", "/sbin", "/Library", "/private/etc",
            "/dev", self.runtime_root, self.venv_root, self.state_root,
            self.app_temp_dir, data_dir,
        ]
        write_roots = [
            data_dir, self.venv_root, self.cache_root, self.state_root,
            self.app_temp_dir,
        ]
        read_rules = "\n".join(
            f"(allow file-read* (subpath {self._sb_quote(os.path.realpath(p))}))"
            for p in read_roots if os.path.exists(p)
        )
        write_rules = "\n".join(
            f"(allow file-write* (subpath {self._sb_quote(os.path.realpath(p))}))"
            for p in write_roots if os.path.exists(p)
        )
        return f'''(version 1)
(deny default)
(allow process-fork)
(allow process-exec)
(allow signal (target same-sandbox))
(allow process-info* (target same-sandbox))
(allow mach-priv-task-port (target same-sandbox))
(allow user-preference-read)
(allow sysctl-read)
(allow mach-lookup)
(allow ipc-posix*)
(allow iokit-open)
(allow network-outbound (remote ip "*:*"))
(allow file-read-metadata)
(allow file-map-executable)
{read_rules}
{write_rules}
(allow file-write-data (literal "/dev/null"))
'''

    def _wrap_macos(self, argv: list[str], data_dir: str) -> list[str]:
        sandbox_exec = "/usr/bin/sandbox-exec"
        if not os.path.isfile(sandbox_exec):
            self._warn_isolation_fallback("/usr/bin/sandbox-exec is not available")
            return argv
        return [sandbox_exec, "-p", self._macos_profile(data_dir), *argv]

    # ------------------------------------------------------------------
    # Windows: Job Object
    # ------------------------------------------------------------------

    @staticmethod
    def _attach_windows_job(process):
        if os.name != "nt":
            return None
        try:
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
            kernel32.CreateJobObjectW.restype = wintypes.HANDLE
            kernel32.SetInformationJobObject.argtypes = [
                wintypes.HANDLE, wintypes.INT, wintypes.LPVOID, wintypes.DWORD
            ]
            kernel32.SetInformationJobObject.restype = wintypes.BOOL
            kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL

            job = kernel32.CreateJobObjectW(None, None)
            if not job:
                return None

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("ReadOperationCount", ctypes.c_uint64),
                    ("WriteOperationCount", ctypes.c_uint64),
                    ("OtherOperationCount", ctypes.c_uint64),
                    ("ReadTransferCount", ctypes.c_uint64),
                    ("WriteTransferCount", ctypes.c_uint64),
                    ("OtherTransferCount", ctypes.c_uint64),
                ]

            class BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", ctypes.c_uint32),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", ctypes.c_uint32),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", ctypes.c_uint32),
                    ("SchedulingClass", ctypes.c_uint32),
                ]

            class EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
            JobObjectExtendedLimitInformation = 9
            info = EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            ok = kernel32.SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            if not ok or not kernel32.AssignProcessToJobObject(
                job, wintypes.HANDLE(process._handle)
            ):
                kernel32.CloseHandle(job)
                return None
            return job
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Model/UI description
    # ------------------------------------------------------------------

    def isolation_name(self) -> str:
        if sys.platform.startswith("linux"):
            return "Linux Landlock (with process-isolation fallback)"
        if sys.platform == "darwin":
            return "macOS Seatbelt/sandbox-exec (with process-isolation fallback)"
        if os.name == "nt":
            return "Windows Job Object/process isolation"
        return "separate-process isolation"

    def filesystem_context(self, data_dir: str) -> str:
        return (
            "The built-in sandbox uses a separate uv-managed virtual environment at "
            f"{self.venv_root}. Its working directory is {data_dir}. Use that data "
            "directory for all user files. The sandbox runs in a separate process; "
            f"filesystem/process isolation is provided by {self.isolation_name()}."
        )
