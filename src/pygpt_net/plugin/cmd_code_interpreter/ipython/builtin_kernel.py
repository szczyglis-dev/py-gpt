#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 14:30:00                  #
# ================================================== #

from __future__ import annotations

import os
import time

from .local_kernel import LocalKernel


class BuiltinKernel(LocalKernel):
    """Persistent IPython kernel running inside the Built-in sandbox venv."""

    def __init__(self, plugin=None, runtime=None):
        super().__init__(plugin)
        self.runtime = runtime
        self._ctx = None
        self._data_dir = None
        self._job = None

    def _connection_file(self) -> str:
        self.runtime._ensure_private_dirs()
        return os.path.join(self.runtime.state_root, "ipython-kernel.json")

    def _close_job(self):
        if self._job is None:
            return
        try:
            self.runtime.close_process_job(self._job)
        finally:
            self._job = None

    def _shutdown_current(self):
        try:
            if self.client is not None:
                self.client.stop_channels()
        except Exception:
            pass
        try:
            if self.manager is not None:
                self.manager.shutdown_kernel(now=True)
        except Exception as exc:
            self.log(f"Error shutting down Built-in IPython kernel: {exc}")
        finally:
            self._close_job()
            try:
                connection_file = self._connection_file()
                if os.path.isfile(connection_file):
                    os.unlink(connection_file)
            except OSError:
                pass
            self.client = None
            self.manager = None
            self.initialized = False

    def init(self, force: bool = False):
        """Start ipykernel using the sandbox Python and OS isolation wrapper."""
        from jupyter_client import KernelManager

        ctx = self._ctx
        data_dir = self.runtime.get_data_dir(ctx=ctx)
        if self.initialized and not force:
            if self._data_dir == data_dir and self.check_ready():
                return
            self.log("Built-in IPython sandbox mapping changed or kernel died; reinitializing...")
            self._shutdown_current()
        elif force and (self.manager is not None or self.client is not None):
            self._shutdown_current()

        self.runtime.ensure_ready(ctx=ctx)
        connection_file = self._connection_file()
        try:
            if os.path.isfile(connection_file):
                os.unlink(connection_file)
        except OSError:
            pass

        kernel_argv = [
            self.runtime.python_bin,
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]
        command, cwd, env = self.runtime.prepare_process(kernel_argv, ctx=ctx)

        manager = KernelManager(connection_file=connection_file)
        # Do not use the application's kernelspec: it would rewrite `python` to
        # sys.executable and start the PyGPT environment. Keep the full sandbox
        # launcher command, including Landlock/Seatbelt where available.
        manager.kernel_spec.argv = command
        manager.start_kernel(cwd=cwd, env=env)

        self.manager = manager
        process = getattr(getattr(manager, "provisioner", None), "process", None)
        if process is not None:
            self._job = self.runtime.attach_process_job(process)

        self.client = manager.client()
        self.client.start_channels()
        try:
            self.client.wait_for_ready(timeout=30)
        except Exception:
            self._shutdown_current()
            raise

        self.initialized = True
        self._data_dir = cwd
        self._configure_noninteractive_shell()
        self.log(f"Connected to Built-in IPython kernel: {self.runtime.python_bin}")
        self.log(f"Built-in IPython CWD: {cwd}")
        self.log("IPython kernel is ready.")

    def execute(
        self,
        code: str,
        current: bool = False,
        auto_init: bool = False,
        ctx=None,
    ) -> str:
        """Execute code while keeping the kernel bound to the active data dir."""
        self._ctx = ctx
        requested_data_dir = self.runtime.get_data_dir(ctx=ctx)
        if self.initialized and self._data_dir != requested_data_dir:
            self.log("Built-in IPython workdir changed; restarting kernel in the new data directory.")
            self._shutdown_current()
        return super().execute(code, current=current, auto_init=auto_init)

    def restart_kernel(self, ctx=None) -> bool:
        """Restart the sandbox kernel without falling back to the host kernel."""
        if ctx is not None:
            self._ctx = ctx
        if not self._restart_lock.acquire(blocking=False):
            self.log("Built-in IPython kernel is already restarting; duplicate request ignored.")
            return False

        self.restarting = True
        try:
            if (
                self.last_restart_at > 0
                and time.monotonic() - self.last_restart_at < self.RESTART_COOLDOWN
                and self.check_ready()
            ):
                self.log("Built-in IPython kernel was restarted recently; duplicate restart skipped.")
                return True

            self._shutdown_current()
            self.init(force=True)
            ready = bool(self.initialized and self.check_ready())
            if ready:
                self.last_restart_at = time.monotonic()
                self.log("Built-in IPython kernel restarted.")
            return ready
        except Exception as exc:
            self.initialized = False
            self.log(f"Error restarting Built-in IPython kernel: {exc}")
            return False
        finally:
            self.restarting = False
            self._restart_lock.release()

    def shutdown_kernel(self):
        """Shutdown the Built-in kernel and release platform isolation handles."""
        self._shutdown_current()

    def end(self, all: bool = False):
        self._shutdown_current()
