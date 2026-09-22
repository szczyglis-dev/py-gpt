#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 16:05:00                  #
# ================================================== #

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
from typing import Callable, Optional, Sequence

from .packages import (
    BUILTIN_BASE_PACKAGES,
    get_builtin_packages,
)


class BuiltinSandboxError(RuntimeError):
    """Raised when the built-in execution runtime cannot be prepared."""


class BuiltinSandboxRuntime:
    """Managed Python runtime used by the built-in Code/System sandboxes.

    ``uv`` manages an interpreter/virtual environment independent from the
    Python environment used to run/freeze PyGPT itself. Commands execute in a
    separate child process. On Windows the child is additionally attached to a
    Job Object with kill-on-close.
    """

    PYTHON_VERSION = "3.12"
    _prepare_lock = threading.RLock()
    _MARKER = ".pygpt-sandbox.json"

    def __init__(
            self,
            window,
            name: str,
            packages_provider: Optional[Callable[[], Sequence[str]]] = None,
    ):
        if name not in {"python", "os"}:
            raise ValueError(f"Unsupported built-in sandbox name: {name}")
        self.window = window
        self.name = name
        self.packages_provider = packages_provider

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

    def get_packages(self) -> list[str]:
        """Return the current user-configured package list for this venv."""
        if self.packages_provider is None:
            return get_builtin_packages(self.name)
        packages = self.packages_provider()
        return [str(item).strip() for item in packages if str(item).strip()]

    def _marker_data(self) -> dict:
        return {
            "version": 7,
            "python": self.PYTHON_VERSION,
            "base_python": self._base_python() or "managed",
            "name": self.name,
            "packages": [*BUILTIN_BASE_PACKAGES, *self.get_packages()],
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

    def ensure_ready(self, ctx=None, force: bool = False) -> str:
        """Create/update the sandbox venv and return its Python executable."""
        with self._prepare_lock:
            self._ensure_directories(ctx=ctx)
            if not force and self._marker_matches():
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
                # e.g. cpython-3.12-... as a symlink to cpython-3.12.14-....
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

            # Keep uv responsible for installing the managed CPython and package
            # operations, while managed runtimes use a concrete patch-specific
            # interpreter and real executable copies. Packaged interpreters
            # (notably Snap) keep using ``uv venv`` because copying an executable
            # out of a confined read-only package may not be executable from
            # writable storage.
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
            # anything into it. This catches future uv/PBS path-layout regressions
            # early with a useful error.
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

            packages = self.get_packages()
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
        """Resolve a built-in runtime path without filesystem access filtering.

        Relative paths are resolved against the current PyGPT data directory;
        absolute paths are preserved (after ``realpath`` normalization). The
        built-in backend intentionally does not enforce a filesystem boundary.
        """
        if not path:
            raise BuiltinSandboxError("Empty path")
        data_dir = self.get_data_dir(ctx=ctx)
        return os.path.realpath(
            path if os.path.isabs(path) else os.path.join(data_dir, path)
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

    def prepare_process(self, argv: Sequence[str], ctx=None):
        """Prepare a child command with the built-in runtime environment."""
        data_dir = self.get_data_dir(ctx=ctx)
        env = self._build_env(ctx=ctx)
        return list(argv), data_dir, env

    def attach_process_job(self, process):
        """Attach a Windows child to the Built-in sandbox Job Object."""
        if os.name != "nt":
            return None
        return self._attach_windows_job(process)

    @staticmethod
    def close_process_job(job):
        """Close a Windows Job Object handle returned by attach_process_job()."""
        if not job or os.name != "nt":
            return
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(job)

    def _communicate(self, argv: Sequence[str], ctx=None):
        command, data_dir, env = self.prepare_process(argv, ctx=ctx)

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

        job = self.attach_process_job(process)
        try:
            return process.communicate()
        finally:
            self.close_process_job(job)

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
        if os.name == "nt":
            return "Windows Job Object/process isolation"
        return "separate-process isolation"

    def filesystem_context(self, data_dir: str) -> str:
        runtime_artifacts = os.path.join(
            self.window.core.config.get_user_dir("tmp"),
            "runtime_artifacts",
        )
        return (
            "The built-in runtime uses a separate uv-managed virtual environment at "
            f"{self.venv_root}. Its working directory is {data_dir}. Relative paths "
            "are resolved from that directory. The process can access the host "
            "filesystem according to the permissions of the PyGPT process; the "
            "built-in backend does not enforce filesystem access restrictions. "
            f"Provider/tool generated runtime artifacts are copied under {runtime_artifacts}; "
            "if an exact artifact path was not returned, inspect that directory recursively before using it."
        )
