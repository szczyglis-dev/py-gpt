#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 20:00:00                  #
# ================================================== #


from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from pygpt_net.core.auto_updater.base import UpdateContext, UpdateError


TraceCallback = Optional[Callable[[str], None]]


def _trace(cb: TraceCallback, message: str):
    try:
        if cb is not None:
            cb(f"[helper] {message}")
    except Exception:
        pass


def _sh_debug_line(message: str, enabled: bool) -> str:
    if not enabled:
        return ""
    return f"printf '%s\\n' {shlex.quote('[AUTO-UPDATER] helper: ' + message)}"


def current_restart_command() -> List[str]:
    """Return a command that launches the current PyGPT entry point again."""
    argv = list(sys.argv)
    extra = argv[1:]
    if getattr(sys, "frozen", False):
        return [sys.executable] + extra

    entry = os.path.abspath(argv[0]) if argv and argv[0] else ""
    if entry and os.path.exists(entry):
        if entry.lower().endswith((".py", ".pyw")):
            return [sys.executable, entry] + extra
        if os.name == "nt" and entry.lower().endswith(".exe"):
            return [entry] + extra
        # Console scripts are plain Python files on POSIX and can be safely
        # launched via the current interpreter after a package upgrade.
        return [sys.executable, entry] + extra

    return [sys.executable] + argv


def appimage_arch(machine: str) -> str:
    value = (machine or "").lower()
    if value in ("x86_64", "amd64"):
        return "x86_64"
    if value in ("aarch64", "arm64"):
        return "aarch64"
    return machine or "x86_64"


def find_git_root(start: str) -> Optional[str]:
    path = Path(start).resolve()
    for candidate in [path] + list(path.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return None


def is_path_inside(path: str, roots: Iterable[str]) -> bool:
    try:
        resolved = Path(path).resolve()
    except Exception:
        return False
    for root in roots:
        if not root:
            continue
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except Exception:
            continue
    return False


def safe_extract_zip(path: str, target: str, context: UpdateContext):
    root = os.path.abspath(target)
    context.log(f"[archive] Opening ZIP: path={path!r}, target={root!r}.")
    with zipfile.ZipFile(path, "r") as archive:
        members = archive.infolist()
        count = max(len(members), 1)
        context.log(f"[archive] ZIP contains {len(members)} member(s).")
        for idx, member in enumerate(members, 1):
            context.check_cancelled()
            destination = os.path.abspath(os.path.join(root, member.filename))
            if os.path.commonpath([root, destination]) != root:
                context.log(f"[archive] Unsafe ZIP member rejected: {member.filename!r}.")
                raise UpdateError(f"Unsafe ZIP member: {member.filename}")
            archive.extract(member, root)
            context.progress("update.auto.status.extracting", int(idx * 100 / count))
    context.log("[archive] ZIP extraction completed.")


def safe_extract_tar(path: str, target: str, context: UpdateContext):
    root = os.path.abspath(target)
    context.log(f"[archive] Opening TAR archive: path={path!r}, target={root!r}.")
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        count = max(len(members), 1)
        context.log(f"[archive] TAR contains {len(members)} member(s).")
        for idx, member in enumerate(members, 1):
            context.check_cancelled()
            destination = os.path.abspath(os.path.join(root, member.name))
            if os.path.commonpath([root, destination]) != root:
                context.log(f"[archive] Unsafe TAR member rejected: {member.name!r}.")
                raise UpdateError(f"Unsafe TAR member: {member.name}")
            if member.issym():
                link_target = os.path.abspath(os.path.join(os.path.dirname(destination), member.linkname))
                if os.path.commonpath([root, link_target]) != root:
                    context.log(f"[archive] Unsafe TAR symlink rejected: {member.name!r} -> {member.linkname!r}.")
                    raise UpdateError(f"Unsafe TAR symlink: {member.name}")
            elif member.islnk():
                link_target = os.path.abspath(os.path.join(root, member.linkname))
                if os.path.commonpath([root, link_target]) != root:
                    context.log(f"[archive] Unsafe TAR hard link rejected: {member.name!r} -> {member.linkname!r}.")
                    raise UpdateError(f"Unsafe TAR hard link: {member.name}")
            archive.extract(member, root)
            context.progress("update.auto.status.extracting", int(idx * 100 / count))
    context.log("[archive] TAR extraction completed.")


def extract_update_archive(path: str, target: str, context: UpdateContext):
    """Extract ZIP/TAR and transparently unpack nested tarballs."""
    os.makedirs(target, exist_ok=True)
    lower = path.lower()
    context.log(f"[archive] Extract update archive: path={path!r}, target={target!r}.")
    if lower.endswith(".zip"):
        safe_extract_zip(path, target, context)
    elif lower.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".tar")):
        safe_extract_tar(path, target, context)
    else:
        raise UpdateError(f"Unsupported update archive: {os.path.basename(path)}")

    # Release ZIPs may contain the actual Linux tarball. Unpack any nested
    # tar archive into an adjacent directory and search both trees later.
    nested = []
    for root, _, files in os.walk(target):
        for name in files:
            lower_name = name.lower()
            if lower_name.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2", ".tar")):
                nested.append(os.path.join(root, name))
    context.log(f"[archive] Nested TAR archive count: {len(nested)}.")
    for archive in nested:
        context.check_cancelled()
        nested_target = archive + ".unpacked"
        context.log(f"[archive] Extracting nested archive: {archive!r} -> {nested_target!r}.")
        os.makedirs(nested_target, exist_ok=True)
        safe_extract_tar(archive, nested_target, context)


def find_linux_payload(root: str, context: Optional[UpdateContext] = None) -> str:
    candidates = []
    if context is not None:
        context.log(f"[linux] Searching extracted tree for 'pygpt' executable: root={root!r}.")
    for dirpath, _, files in os.walk(root):
        if "pygpt" in files:
            exe = os.path.join(dirpath, "pygpt")
            score = 0
            names = set(os.listdir(dirpath))
            if "internal" in names or "_internal" in names:
                score += 10
            score -= len(Path(dirpath).parts)
            candidates.append((score, dirpath, exe))
            if context is not None:
                context.log(f"[linux] Payload candidate: dir={dirpath!r}, exe={exe!r}, score={score}.")
    if not candidates:
        raise UpdateError("Downloaded Linux package does not contain a 'pygpt' executable")
    candidates.sort(reverse=True)
    score, payload_root, exe = candidates[0]
    mode = os.stat(exe).st_mode
    os.chmod(exe, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if context is not None:
        context.log(
            f"[linux] Selected payload root={payload_root!r}, exe={exe!r}, score={score}; chmod +x applied."
        )
    return payload_root


def clear_path(path: str, context: Optional[UpdateContext] = None):
    if context is not None:
        context.log(f"[filesystem] Removing path: {path!r}.")
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def stage_payload_with_update_suffix(payload_root: str, install_dir: str, context: UpdateContext) -> List[str]:
    names = [name for name in os.listdir(payload_root) if name not in (".", "..")]
    if not names:
        raise UpdateError("Update package is empty")

    context.log(
        f"[staging] Staging {len(names)} top-level payload item(s) from {payload_root!r} "
        f"to {install_dir!r} using '.update' suffix."
    )
    staged = []
    count = len(names)
    for idx, name in enumerate(names, 1):
        context.check_cancelled()
        src = os.path.join(payload_root, name)
        dst = os.path.join(install_dir, name + ".update")
        context.log(f"[staging] {idx}/{count}: {src!r} -> {dst!r}.")
        if os.path.exists(dst) or os.path.islink(dst):
            context.log(f"[staging] Removing previous staged item: {dst!r}.")
            clear_path(dst, context)
        if os.path.isdir(src) and not os.path.islink(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
        staged.append(name)
        context.progress("update.auto.status.staging", int(idx * 100 / count))
    context.log(f"[staging] Staging complete; staged_names={staged!r}.")
    return staged


def _write_temp_script(suffix: str, content: str) -> str:
    path = os.path.join(tempfile.gettempdir(), f"pygpt-update-{uuid.uuid4().hex}{suffix}")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    if os.name != "nt":
        os.chmod(path, 0o700)
    return path


def launch_posix_script(content: str, debug: bool = False, trace: TraceCallback = None) -> str:
    script = _write_temp_script(".sh", content)
    _trace(trace, f"Created POSIX post-exit helper script: {script!r}; debug_console={debug}.")
    proc = subprocess.Popen(
        ["/bin/sh", script],
        stdin=subprocess.DEVNULL,
        stdout=None if debug else subprocess.DEVNULL,
        stderr=None if debug else subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    _trace(trace, f"Started POSIX helper process: pid={proc.pid}, script={script!r}.")
    return script


def launch_windows_python_helper(
        content: str,
        debug: bool = False,
        trace: TraceCallback = None,
        visible_console: bool = False,
) -> str:
    # Source/pip/git installs have a Python interpreter available. A tiny
    # stdlib-only helper is more reliable than cmd.exe/tasklist/find/ping.
    # Most helpers are intentionally hidden, but the Windows pip updater uses
    # a visible console so the user can see live installation progress.
    script = _write_temp_script(".py", content)
    if visible_console:
        flags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        )
        stdout = None
        stderr = None
        log_handle = None
        log_path = None
    else:
        flags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        log_handle = None
        log_path = None
        if debug:
            log_path = script + ".log"
            log_handle = open(log_path, "ab")
            stdout = log_handle
            stderr = subprocess.STDOUT
        else:
            stdout = subprocess.DEVNULL
            stderr = subprocess.DEVNULL

    _trace(
        trace,
        f"Created Windows Python post-exit helper: {script!r}; "
        f"visible_console={visible_console}; debug_log={log_path!r}.",
    )
    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            stdin=None if visible_console else subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=flags,
            close_fds=True,
        )
    finally:
        if log_handle is not None:
            log_handle.close()
    _trace(
        trace,
        f"Started Windows Python helper: pid={proc.pid}, script={script!r}, "
        f"visible_console={visible_console}, debug_log={log_path!r}.",
    )
    return script



def launch_windows_powershell_helper(
        content: str,
        args: Optional[List[str]] = None,
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    """Launch a hidden PowerShell helper for frozen Windows builds."""
    script = os.path.join(
        tempfile.gettempdir(),
        f"pygpt-update-{uuid.uuid4().hex}.ps1",
    )
    # Windows PowerShell 5.1 reliably detects UTF-8 when a BOM is present.
    with open(script, "w", encoding="utf-8-sig", newline="\r\n") as handle:
        handle.write(content)

    flags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-WindowStyle", "Hidden",
        "-File", script,
    ] + list(args or [])

    log_handle = None
    log_path = None
    if debug:
        log_path = script + ".log"
        log_handle = open(log_path, "ab")
        stdout = log_handle
        stderr = subprocess.STDOUT
    else:
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL

    _trace(
        trace,
        f"Created Windows PowerShell post-exit helper: {script!r}; "
        f"hidden_console=True; debug_log={log_path!r}.",
    )
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=flags,
            close_fds=True,
        )
    finally:
        if log_handle is not None:
            log_handle.close()

    _trace(
        trace,
        f"Started Windows PowerShell helper: pid={proc.pid}, script={script!r}, "
        f"debug_log={log_path!r}.",
    )
    return script

def _windows_wait_helper_source(
        pid: int,
        body: str,
        debug: bool,
        timeout_seconds: int = 30,
) -> str:
    # OpenProcess + WaitForSingleObject waits on the exact process object.
    # This avoids PID text matching, localization issues and PID-reuse races.
    return f"""import ctypes
import os
import subprocess
import sys
import time

PARENT_PID = {int(pid)!r}
WAIT_TIMEOUT_SECONDS = {int(timeout_seconds)!r}
DEBUG = {bool(debug)!r}


def log(message):
    if DEBUG:
        print("[AUTO-UPDATER] helper: " + str(message), flush=True)


def wait_for_parent():
    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, PARENT_PID)
    if not handle:
        log("Parent process already exited.")
        return True
    try:
        result = kernel32.WaitForSingleObject(handle, WAIT_TIMEOUT_SECONDS * 1000)
        if result == WAIT_OBJECT_0:
            log("Parent PyGPT process exited.")
            return True
        if result == WAIT_TIMEOUT:
            log(f"Timed out waiting for PyGPT PID {{PARENT_PID}}; aborting helper.")
            return False
        log(f"WaitForSingleObject failed with result={{result}}; aborting helper.")
        return False
    finally:
        kernel32.CloseHandle(handle)


def hidden_creation_flags():
    return (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


def launch(command):
    log(f"Launching: {{command!r}}")
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=hidden_creation_flags(),
        close_fds=True,
    )


def remove_path(path):
    import shutil
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def cleanup_self():
    try:
        os.remove(__file__)
    except OSError:
        pass


try:
    if not wait_for_parent():
        sys.exit(2)
{body}
finally:
    cleanup_self()
"""



def schedule_windows_msi_install_after_exit(
        msi_path: str,
        restart_executable: str,
        debug: bool = False,
        trace: TraceCallback = None,
        timeout_seconds: int = 60,
) -> str:
    """Install an MSI after PyGPT exits, then restart the installed app."""
    if os.name != "nt":
        raise UpdateError("Windows MSI post-exit helper can only run on Windows")

    pid = os.getpid()
    payload = {
        "parent_pid": pid,
        "wait_timeout_ms": max(1, int(timeout_seconds)) * 1000,
        "msi_path": os.path.abspath(msi_path),
        "restart_executable": os.path.abspath(restart_executable),
        "debug": bool(debug),
    }
    payload_arg = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    _trace(
        trace,
        f"Scheduling Windows MSI install after pid={pid} exits; "
        f"msi={payload['msi_path']!r}, restart={payload['restart_executable']!r}, "
        f"timeout={timeout_seconds}s.",
    )

    content = r'''param(
    [Parameter(Mandatory=$true)]
    [string]$PayloadBase64
)

$ErrorActionPreference = "Stop"
$cfgJson = [System.Text.Encoding]::UTF8.GetString(
    [System.Convert]::FromBase64String($PayloadBase64)
)
$cfg = $cfgJson | ConvertFrom-Json
$debugEnabled = [bool]$cfg.debug

function Write-UpdateLog([string]$Message) {
    if ($debugEnabled) {
        Write-Output ("[AUTO-UPDATER] helper: " + $Message)
    }
}

try {
    $parentPid = [int]$cfg.parent_pid
    $timeoutMs = [int]$cfg.wait_timeout_ms
    Write-UpdateLog ("Waiting for PyGPT PID {0} to exit." -f $parentPid)
    try {
        $parent = [System.Diagnostics.Process]::GetProcessById($parentPid)
        if (-not $parent.WaitForExit($timeoutMs)) {
            Write-UpdateLog ("Timed out waiting for PyGPT PID {0}; aborting MSI update." -f $parentPid)
            exit 2
        }
    }
    catch [System.ArgumentException] {
        Write-UpdateLog "PyGPT process already exited."
    }

    $msiPath = [string]$cfg.msi_path
    $installerArgs = '/i "' + $msiPath + '" /passive /norestart'
    Write-UpdateLog ("Launching passive MSI installer: {0}" -f $msiPath)
    $installer = Start-Process `
        -FilePath "$env:SystemRoot\System32\msiexec.exe" `
        -ArgumentList $installerArgs `
        -PassThru `
        -Wait

    $exitCode = [int]$installer.ExitCode
    Write-UpdateLog ("MSI installer finished with exit code {0}." -f $exitCode)
    if (@(0, 3010, 1641) -notcontains $exitCode) {
        Write-UpdateLog "MSI installation failed; PyGPT will not be restarted."
        exit 3
    }

    $restartExe = [string]$cfg.restart_executable
    if (-not [string]::IsNullOrWhiteSpace($restartExe)) {
        Write-UpdateLog ("Launching updated PyGPT: {0}" -f $restartExe)
        Start-Process -FilePath $restartExe | Out-Null
    }
    Write-UpdateLog "Windows MSI update helper completed successfully."
}
catch {
    Write-UpdateLog ("Helper failed: " + $_.Exception.GetType().Name + ": " + $_.Exception.Message)
    exit 4
}
finally {
    try {
        Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
    }
    catch {}
}
'''
    return launch_windows_powershell_helper(
        content,
        args=[payload_arg],
        debug=debug,
        trace=trace,
    )

def schedule_windows_pip_update_after_exit(
        update_command: List[str],
        restart_command: List[str],
        debug: bool = False,
        trace: TraceCallback = None,
        timeout_seconds: int = 30,
) -> str:
    """Run pip after PyGPT exits, show live progress, then restart PyGPT.

    Windows locks ``Scripts/pygpt.exe`` while the app is running, so pip must
    update only after PyGPT exits. Unlike the other post-exit helpers this one
    intentionally owns a visible console window. That gives the user immediate
    feedback during a potentially long dependency update and also leaves a
    readable error on screen if pip or the automatic restart fails.
    """
    if os.name != "nt":
        raise UpdateError("Windows pip post-exit helper can only run on Windows")

    pid = os.getpid()
    _trace(
        trace,
        f"Scheduling visible Windows pip update after pid={pid} exits; "
        f"update_command={update_command!r}, restart_command={restart_command!r}.",
    )

    body = (
        "    try:\n"
        "        ctypes.windll.kernel32.SetConsoleTitleW(\"PyGPT Update\")\n"
        "    except Exception:\n"
        "        pass\n"
        "    update_command = " + repr(list(update_command)) + "\n"
        "    restart_command = " + repr(list(restart_command)) + "\n"
        "    print(\"\", flush=True)\n"
        "    print(\"============================================================\", flush=True)\n"
        "    print(\" PyGPT automatic update\", flush=True)\n"
        "    print(\"============================================================\", flush=True)\n"
        "    print(\"Updating PyGPT via pip... please wait.\", flush=True)\n"
        "    print(\"Do not close this window until the update is complete.\", flush=True)\n"
        "    print(\"\", flush=True)\n"
        "    log(f\"Running pip update after PyGPT exit: {update_command!r}\")\n"
        "    completed = subprocess.Popen(\n"
        "        update_command,\n"
        "        stdin=subprocess.DEVNULL,\n"
        "        stdout=subprocess.PIPE,\n"
        "        stderr=subprocess.STDOUT,\n"
        "        text=True,\n"
        "        encoding=\"utf-8\",\n"
        "        errors=\"replace\",\n"
        "        creationflags=0,\n"
        "        close_fds=True,\n"
        "    )\n"
        "    if completed.stdout is not None:\n"
        "        for line in completed.stdout:\n"
        "            print(line, end=\"\", flush=True)\n"
        "    returncode = completed.wait()\n"
        "    print(\"\", flush=True)\n"
        "    log(f\"pip finished with return code {returncode}.\")\n"
        "    if returncode != 0:\n"
        "        print(\"UPDATE FAILED. PyGPT was not restarted.\", flush=True)\n"
        "        print(\"Press Enter to close this window.\", flush=True)\n"
        "        try:\n"
        "            input()\n"
        "        except EOFError:\n"
        "            time.sleep(10)\n"
        "        sys.exit(returncode or 3)\n"
        "\n"
        "    print(\"Update completed successfully.\", flush=True)\n"
        "    print(\"Restarting PyGPT...\", flush=True)\n"
        "\n"
        "    restart_candidates = []\n"
        "    if restart_command:\n"
        "        restart_candidates.append(restart_command)\n"
        "\n"
        "    # The pip console-script launcher is recreated during upgrade. In\n"
        "    # rare cases Windows/AV may still delay the fresh launcher. Keep a\n"
        "    # direct pythonw fallback that starts PyGPT from the installed\n"
        "    # package without relying on Scripts\\pygpt.exe.\n"
        "    python_exe = update_command[0] if update_command else sys.executable\n"
        "    python_dir = os.path.dirname(os.path.abspath(python_exe))\n"
        "    pythonw = os.path.join(python_dir, \"pythonw.exe\")\n"
        "    fallback_python = pythonw if os.path.isfile(pythonw) else python_exe\n"
        "    fallback_command = [\n"
        "        fallback_python,\n"
        "        \"-c\",\n"
        "        \"from pygpt_net.app import run; run()\",\n"
        "    ]\n"
        "    if fallback_command not in restart_candidates:\n"
        "        restart_candidates.append(fallback_command)\n"
        "\n"
        "    restarted = False\n"
        "    last_error = None\n"
        "    for idx, command in enumerate(restart_candidates, 1):\n"
        "        # The freshly installed console launcher can appear a fraction\n"
        "        # of a second after pip returns on some Windows setups.\n"
        "        target = command[0] if command else \"\"\n"
        "        if target and target.lower().endswith(\".exe\"):\n"
        "            for _ in range(20):\n"
        "                if os.path.exists(target):\n"
        "                    break\n"
        "                time.sleep(0.25)\n"
        "        try:\n"
        "            log(f\"Restart attempt {idx}: {command!r}\")\n"
        "            proc = launch(command)\n"
        "            time.sleep(2.0)\n"
        "            code = proc.poll()\n"
        "            if code is None:\n"
        "                log(f\"PyGPT restart succeeded with pid={proc.pid}.\")\n"
        "                restarted = True\n"
        "                break\n"
        "            last_error = RuntimeError(\n"
        "                f\"restart command exited immediately with code {code}\"\n"
        "            )\n"
        "            log(str(last_error))\n"
        "        except Exception as exc:\n"
        "            last_error = exc\n"
        "            log(f\"Restart attempt failed: {type(exc).__name__}: {exc}\")\n"
        "\n"
        "    if not restarted:\n"
        "        print(\"\", flush=True)\n"
        "        print(\"UPDATE SUCCEEDED, BUT PyGPT COULD NOT BE RESTARTED AUTOMATICALLY.\", flush=True)\n"
        "        if last_error is not None:\n"
        "            print(f\"Reason: {type(last_error).__name__}: {last_error}\", flush=True)\n"
        "        print(\"Start PyGPT manually, then press Enter to close this window.\", flush=True)\n"
        "        try:\n"
        "            input()\n"
        "        except EOFError:\n"
        "            time.sleep(15)\n"
        "        sys.exit(4)\n"
        "\n"
        "    print(\"PyGPT restarted successfully.\", flush=True)\n"
        "    print(\"This update window will close automatically.\", flush=True)\n"
        "    time.sleep(1.5)\n"
    )
    content = _windows_wait_helper_source(
        pid,
        body,
        debug,
        timeout_seconds=timeout_seconds,
    )
    return launch_windows_python_helper(
        content,
        debug=debug,
        trace=trace,
        visible_console=True,
    )


def schedule_restart_after_exit(
        command: List[str],
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    pid = os.getpid()
    _trace(trace, f"Scheduling restart after pid={pid} exits; command={command!r}.")
    if os.name == "nt":
        body = f"""    command = {command!r}
    proc = launch(command)
    log(f"Restart command launched successfully; pid={{proc.pid}}.")
"""
        content = _windows_wait_helper_source(pid, body, debug, timeout_seconds=30)
        return launch_windows_python_helper(content, debug=debug, trace=trace)

    cmdline = " ".join(shlex.quote(part) for part in command)
    content = f"""#!/bin/sh
{_sh_debug_line(f'Waiting for PyGPT PID {pid} to exit.', debug)}
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
{_sh_debug_line('PyGPT exited; launching restart command.', debug)}
{cmdline} >/dev/null 2>&1 &
{_sh_debug_line('Restart command launched; deleting helper script.', debug)}
rm -f -- "$0"
"""
    return launch_posix_script(content, debug=debug, trace=trace)


def schedule_linux_swap_after_exit(
        install_dir: str,
        names: List[str],
        executable_name: str = "pygpt",
        args: Optional[List[str]] = None,
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    pid = os.getpid()
    quoted_dir = shlex.quote(os.path.abspath(install_dir))
    quoted_names = " ".join(shlex.quote(name) for name in names)
    exe = shlex.quote(os.path.join(os.path.abspath(install_dir), executable_name))
    argline = " ".join(shlex.quote(part) for part in (args or []))
    _trace(
        trace,
        f"Scheduling Linux payload swap after pid={pid} exits; install_dir={install_dir!r}, "
        f"names={names!r}, executable={executable_name!r}, args={(args or [])!r}.",
    )
    content = f"""#!/bin/sh
set -u
trap 'rm -f -- "$0"' EXIT
{_sh_debug_line(f'Waiting for PyGPT PID {pid} to exit before Linux payload swap.', debug)}
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
{_sh_debug_line('PyGPT exited; entering install directory.', debug)}
cd {quoted_dir} || exit 1
set -- {quoted_names}

# Phase 1: move every existing installation item out of the way before
# installing anything. This makes rollback safe even when a later rename
# fails: untouched originals are never deleted.
{_sh_debug_line('Phase 1: backing up current payload to .old.', debug)}
backup_failed=0
for name in "$@"; do
  {('echo "[AUTO-UPDATER] helper: backup: $name -> $name.old"' if debug else '')}
  rm -rf -- "$name.old"
  if [ -e "$name" ] || [ -L "$name" ]; then
    mv -- "$name" "$name.old" || {{ backup_failed=1; break; }}
  fi
done
if [ $backup_failed -ne 0 ]; then
  {_sh_debug_line('Backup phase failed; restoring any moved originals.', debug)}
  for name in "$@"; do
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then
      if [ ! -e "$name" ] && [ ! -L "$name" ]; then mv -- "$name.old" "$name"; fi
    fi
  done
  exit 1
fi

# Phase 2: all originals are backed up now, so an install failure can safely
# remove partially installed new files and restore the complete old payload.
{_sh_debug_line('Phase 2: promoting .update payload into place.', debug)}
install_failed=0
for name in "$@"; do
  {('echo "[AUTO-UPDATER] helper: install: $name.update -> $name"' if debug else '')}
  mv -- "$name.update" "$name" || {{ install_failed=1; break; }}
done
if [ $install_failed -ne 0 ]; then
  {_sh_debug_line('Install phase failed; rolling back old payload.', debug)}
  for name in "$@"; do
    rm -rf -- "$name"
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then mv -- "$name.old" "$name"; fi
  done
  exit 1
fi
{_sh_debug_line('Applying executable permission to pygpt binary.', debug)}
if ! chmod +x -- {exe}; then
  {_sh_debug_line('chmod failed; rolling back old payload.', debug)}
  for name in "$@"; do
    rm -rf -- "$name"
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then mv -- "$name.old" "$name"; fi
  done
  exit 1
fi
{_sh_debug_line('Launching updated PyGPT for startup verification.', debug)}
{exe} {argline} >/dev/null 2>&1 &
new_pid=$!
{('echo "[AUTO-UPDATER] helper: new PyGPT PID: $new_pid"' if debug else '')}
sleep 1
if ! kill -0 "$new_pid" 2>/dev/null; then
  {_sh_debug_line('Updated PyGPT exited immediately; restoring old payload.', debug)}
  for name in "$@"; do
    rm -rf -- "$name"
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then mv -- "$name.old" "$name"; fi
  done
  {_sh_debug_line('Launching restored old PyGPT.', debug)}
  {exe} {argline} >/dev/null 2>&1 &
  exit 1
fi
{_sh_debug_line('Updated PyGPT is alive; removing .old backups.', debug)}
for name in "$@"; do rm -rf -- "$name.old"; done
{_sh_debug_line('Linux payload swap completed successfully.', debug)}
"""
    return launch_posix_script(content, debug=debug, trace=trace)



def schedule_source_package_swap_after_exit(
        current_package: str,
        staged_package: str,
        restart_command: List[str],
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    """Atomically replace a source package after PyGPT exits, then restart."""
    pid = os.getpid()
    current = shlex.quote(os.path.abspath(current_package))
    staged = shlex.quote(os.path.abspath(staged_package))
    old = shlex.quote(os.path.abspath(current_package) + ".old")
    restart = " ".join(shlex.quote(part) for part in restart_command)
    _trace(
        trace,
        f"Scheduling source-package swap after pid={pid} exits; "
        f"current={current_package!r}, staged={staged_package!r}, restart={restart_command!r}.",
    )

    if os.name == "nt":
        current_abs = os.path.abspath(current_package)
        staged_abs = os.path.abspath(staged_package)
        old_abs = current_abs + ".old"
        body = f"""    current = {current_abs!r}
    staged = {staged_abs!r}
    old = {old_abs!r}
    restart = {restart_command!r}
    backed_up = False
    promoted = False
    try:
        log(f"Removing stale backup: {{old!r}}")
        if os.path.exists(old) or os.path.islink(old):
            remove_path(old)
        if os.path.exists(current) or os.path.islink(current):
            log(f"Backing up current package: {{current!r}} -> {{old!r}}")
            os.rename(current, old)
            backed_up = True
        log(f"Promoting staged package: {{staged!r}} -> {{current!r}}")
        os.rename(staged, current)
        promoted = True
    except Exception as exc:
        log(f"Package swap failed: {{type(exc).__name__}}: {{exc}}; rolling back.")
        try:
            if promoted and (os.path.exists(current) or os.path.islink(current)):
                remove_path(current)
            if backed_up and (os.path.exists(old) or os.path.islink(old)):
                os.rename(old, current)
        finally:
            raise

    try:
        proc = launch(restart)
        log(f"Updated PyGPT launched; pid={{proc.pid}}. Verifying startup.")
    except Exception as exc:
        log(f"Unable to launch updated PyGPT: {{type(exc).__name__}}: {{exc}}; rolling back.")
        if os.path.exists(current) or os.path.islink(current):
            remove_path(current)
        if backed_up and (os.path.exists(old) or os.path.islink(old)):
            os.rename(old, current)
            try:
                restored = launch(restart)
                log(f"Restored PyGPT launched; pid={{restored.pid}}.")
            except Exception as restore_exc:
                log(f"Unable to launch restored PyGPT: {{restore_exc}}")
        raise

    time.sleep(2.0)
    exit_code = proc.poll()
    if exit_code is not None:
        log(f"Updated PyGPT exited during startup verification with code={{exit_code}}; rolling back.")
        if os.path.exists(current) or os.path.islink(current):
            remove_path(current)
        if backed_up and (os.path.exists(old) or os.path.islink(old)):
            os.rename(old, current)
            try:
                restored = launch(restart)
                log(f"Restored PyGPT launched; pid={{restored.pid}}.")
            except Exception as restore_exc:
                log(f"Unable to launch restored PyGPT: {{restore_exc}}")
        sys.exit(3)

    log("Updated PyGPT is still running; removing old package backup.")
    if backed_up and (os.path.exists(old) or os.path.islink(old)):
        remove_path(old)
"""
        content = _windows_wait_helper_source(pid, body, debug, timeout_seconds=30)
        return launch_windows_python_helper(content, debug=debug, trace=trace)

    content = f"""#!/bin/sh
set -u
trap 'rm -f -- "$0"' EXIT
{_sh_debug_line(f'Waiting for PyGPT PID {pid} to exit before source package swap.', debug)}
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
{_sh_debug_line('PyGPT exited; removing stale source-package backup.', debug)}
rm -rf -- {old}
{_sh_debug_line('Backing up current source package.', debug)}
if [ -e {current} ] || [ -L {current} ]; then mv -- {current} {old} || exit 1; fi
{_sh_debug_line('Promoting staged source package.', debug)}
if ! mv -- {staged} {current}; then
  {_sh_debug_line('Source package promotion failed; restoring backup.', debug)}
  [ -e {old} ] && mv -- {old} {current}
  exit 1
fi
{_sh_debug_line('Launching updated source installation for startup verification.', debug)}
{restart} >/dev/null 2>&1 &
new_pid=$!
{('echo "[AUTO-UPDATER] helper: new source PyGPT PID: $new_pid"' if debug else '')}
sleep 1
if ! kill -0 "$new_pid" 2>/dev/null; then
  {_sh_debug_line('Updated source PyGPT exited immediately; rolling back package.', debug)}
  rm -rf -- {current}
  if [ -e {old} ]; then
    mv -- {old} {current}
    {_sh_debug_line('Launching restored source package.', debug)}
    {restart} >/dev/null 2>&1 &
  fi
  exit 1
fi
{_sh_debug_line('Updated source PyGPT is alive; deleting package backup.', debug)}
rm -rf -- {old}
{_sh_debug_line('Source package swap completed successfully.', debug)}
"""
    return launch_posix_script(content, debug=debug, trace=trace)

def schedule_appimage_swap_after_exit(
        current_path: str,
        staged_path: str,
        args: List[str],
        target_path: Optional[str] = None,
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    pid = os.getpid()
    current_abs = os.path.abspath(current_path)
    staged_abs = os.path.abspath(staged_path)
    target_abs = os.path.abspath(target_path or current_path)
    old_abs = current_abs + ".old"

    current = shlex.quote(current_abs)
    staged = shlex.quote(staged_abs)
    target = shlex.quote(target_abs)
    old = shlex.quote(old_abs)
    argline = " ".join(shlex.quote(part) for part in args)
    _trace(
        trace,
        f"Scheduling AppImage swap after pid={pid} exits; current={current_abs!r}, "
        f"staged={staged_abs!r}, target={target_abs!r}, backup={old_abs!r}, "
        f"args={args!r}.",
    )
    content = f"""#!/bin/sh
set -u
trap 'rm -f -- "$0"' EXIT
{_sh_debug_line(f'Waiting for PyGPT PID {pid} to exit before AppImage swap.', debug)}
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
{_sh_debug_line('PyGPT exited; removing stale .old AppImage.', debug)}
rm -f -- {old}
{_sh_debug_line('Moving current AppImage to temporary .old backup.', debug)}
if [ -e {current} ]; then mv -- {current} {old} || exit 1; fi
{_sh_debug_line('Promoting .update AppImage to target-version filename.', debug)}
if ! mv -f -- {staged} {target}; then
  {_sh_debug_line('Promotion failed; restoring old AppImage.', debug)}
  [ -e {old} ] && mv -- {old} {current}
  exit 1
fi
{_sh_debug_line('Applying executable permission to new AppImage.', debug)}
if ! chmod +x -- {target}; then
  {_sh_debug_line('chmod failed; rolling back AppImage.', debug)}
  rm -f -- {target}
  [ -e {old} ] && mv -- {old} {current}
  exit 1
fi
{_sh_debug_line('Launching updated AppImage for startup verification.', debug)}
{target} {argline} >/dev/null 2>&1 &
new_pid=$!
{('echo "[AUTO-UPDATER] helper: new AppImage PID: $new_pid"' if debug else '')}
sleep 1
if ! kill -0 "$new_pid" 2>/dev/null; then
  {_sh_debug_line('Updated AppImage exited immediately; rolling back.', debug)}
  rm -f -- {target}
  if [ -e {old} ]; then
    mv -- {old} {current}
    {_sh_debug_line('Launching restored old AppImage.', debug)}
    {current} {argline} >/dev/null 2>&1 &
  fi
  exit 1
fi
{_sh_debug_line('Updated AppImage is alive; deleting temporary old-version backup.', debug)}
rm -f -- {old}
{_sh_debug_line('AppImage swap completed successfully.', debug)}
"""
    return launch_posix_script(content, debug=debug, trace=trace)
