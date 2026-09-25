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


def _cmd_debug_line(message: str, enabled: bool) -> str:
    if not enabled:
        return ""
    safe = str(message).replace("%", "%%")
    return f"echo [AUTO-UPDATER] helper: {safe}"


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


def launch_windows_script(content: str, debug: bool = False, trace: TraceCallback = None) -> str:
    script = _write_temp_script(".cmd", content.replace("\n", "\r\n"))
    if debug:
        # In explicit updater-debug mode keep stdout/stderr attached when a
        # console exists; from a windowed build cmd.exe may open a temporary
        # console, which is useful for observing the post-exit handoff.
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        stdout = None
        stderr = None
    else:
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
    _trace(trace, f"Created Windows post-exit helper script: {script!r}; debug_console={debug}.")
    proc = subprocess.Popen(
        ["cmd.exe", "/d", "/c", script],
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=stderr,
        creationflags=flags,
        close_fds=True,
    )
    _trace(trace, f"Started Windows helper process: pid={proc.pid}, script={script!r}.")
    return script


def schedule_restart_after_exit(
        command: List[str],
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    pid = os.getpid()
    _trace(trace, f"Scheduling restart after pid={pid} exits; command={command!r}.")
    if os.name == "nt":
        cmdline = subprocess.list2cmdline(command)
        content = f"""@echo off
{_cmd_debug_line(f'Waiting for PyGPT PID {pid} to exit.', debug)}
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  ping 127.0.0.1 -n 2 >NUL
  goto wait_loop
)
{_cmd_debug_line('PyGPT exited; launching restart command.', debug)}
start "" {cmdline}
{_cmd_debug_line('Restart command launched; deleting helper script.', debug)}
del "%~f0"
"""
        return launch_windows_script(content, debug=debug, trace=trace)

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
        current_win = subprocess.list2cmdline([os.path.abspath(current_package)])
        staged_win = subprocess.list2cmdline([os.path.abspath(staged_package)])
        old_win = subprocess.list2cmdline([os.path.abspath(current_package) + ".old"])
        restart_win = subprocess.list2cmdline(restart_command)
        content = f"""@echo off
{_cmd_debug_line(f'Waiting for PyGPT PID {pid} to exit before source package swap.', debug)}
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  ping 127.0.0.1 -n 2 >NUL
  goto wait_loop
)
{_cmd_debug_line('PyGPT exited; backing up current source package.', debug)}
if exist {old_win} rmdir /s /q {old_win}
if exist {current_win} move /y {current_win} {old_win} >NUL || goto rollback
{_cmd_debug_line('Promoting staged source package.', debug)}
move /y {staged_win} {current_win} >NUL || goto rollback
{_cmd_debug_line('Launching updated source installation.', debug)}
start "" {restart_win}
ping 127.0.0.1 -n 3 >NUL
rem Windows cannot reliably probe an arbitrary detached GUI child here; a
rem successful rename + launch is considered handoff success.
if exist {old_win} rmdir /s /q {old_win}
goto cleanup
:rollback
{_cmd_debug_line('Source package swap failed; restoring backup.', debug)}
if exist {current_win} rmdir /s /q {current_win}
if exist {old_win} move /y {old_win} {current_win} >NUL
:cleanup
del "%~f0"
"""
        return launch_windows_script(content, debug=debug, trace=trace)

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


def schedule_windows_msi_after_exit(
        msi_path: str,
        restart_command: List[str],
        debug: bool = False,
        trace: TraceCallback = None,
) -> str:
    pid = os.getpid()
    msi = subprocess.list2cmdline([os.path.abspath(msi_path)])
    restart = subprocess.list2cmdline(restart_command)
    _trace(
        trace,
        f"Scheduling MSI install after pid={pid} exits; msi={msi_path!r}, restart={restart_command!r}.",
    )
    content = f"""@echo off
{_cmd_debug_line(f'Waiting for PyGPT PID {pid} to exit before MSI install.', debug)}
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  ping 127.0.0.1 -n 2 >NUL
  goto wait_loop
)
{_cmd_debug_line('PyGPT exited; starting MSI installer.', debug)}
start /wait "" msiexec.exe /i {msi}
set "MSI_RC=%ERRORLEVEL%"
{('echo [AUTO-UPDATER] helper: MSI exit code: %MSI_RC%' if debug else '')}
if "%MSI_RC%"=="0" goto restart_app
if "%MSI_RC%"=="3010" goto restart_app
goto cleanup
:restart_app
{_cmd_debug_line('MSI succeeded; restarting PyGPT.', debug)}
start "" {restart}
:cleanup
{_cmd_debug_line('Cleaning downloaded MSI and helper script.', debug)}
del /q {msi} >NUL 2>NUL
del "%~f0"
"""
    return launch_windows_script(content, debug=debug, trace=trace)
