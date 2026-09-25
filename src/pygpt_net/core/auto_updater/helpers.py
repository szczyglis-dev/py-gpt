#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from typing import Iterable, List, Optional

from pygpt_net.core.auto_updater.base import UpdateContext, UpdateError


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
    with zipfile.ZipFile(path, "r") as archive:
        members = archive.infolist()
        count = max(len(members), 1)
        for idx, member in enumerate(members, 1):
            context.check_cancelled()
            destination = os.path.abspath(os.path.join(root, member.filename))
            if os.path.commonpath([root, destination]) != root:
                raise UpdateError(f"Unsafe ZIP member: {member.filename}")
            archive.extract(member, root)
            context.progress("update.auto.status.extracting", int(idx * 100 / count))


def safe_extract_tar(path: str, target: str, context: UpdateContext):
    root = os.path.abspath(target)
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        count = max(len(members), 1)
        for idx, member in enumerate(members, 1):
            context.check_cancelled()
            destination = os.path.abspath(os.path.join(root, member.name))
            if os.path.commonpath([root, destination]) != root:
                raise UpdateError(f"Unsafe TAR member: {member.name}")
            if member.issym():
                link_target = os.path.abspath(os.path.join(os.path.dirname(destination), member.linkname))
                if os.path.commonpath([root, link_target]) != root:
                    raise UpdateError(f"Unsafe TAR symlink: {member.name}")
            elif member.islnk():
                link_target = os.path.abspath(os.path.join(root, member.linkname))
                if os.path.commonpath([root, link_target]) != root:
                    raise UpdateError(f"Unsafe TAR hard link: {member.name}")
            archive.extract(member, root)
            context.progress("update.auto.status.extracting", int(idx * 100 / count))


def extract_update_archive(path: str, target: str, context: UpdateContext):
    """Extract ZIP/TAR and transparently unpack nested tarballs."""
    os.makedirs(target, exist_ok=True)
    lower = path.lower()
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
    for idx, archive in enumerate(nested):
        context.check_cancelled()
        nested_target = archive + ".unpacked"
        os.makedirs(nested_target, exist_ok=True)
        safe_extract_tar(archive, nested_target, context)


def find_linux_payload(root: str) -> str:
    candidates = []
    for dirpath, _, files in os.walk(root):
        if "pygpt" in files:
            exe = os.path.join(dirpath, "pygpt")
            score = 0
            names = set(os.listdir(dirpath))
            if "internal" in names or "_internal" in names:
                score += 10
            score -= len(Path(dirpath).parts)
            candidates.append((score, dirpath, exe))
    if not candidates:
        raise UpdateError("Downloaded Linux package does not contain a 'pygpt' executable")
    candidates.sort(reverse=True)
    _, payload_root, exe = candidates[0]
    mode = os.stat(exe).st_mode
    os.chmod(exe, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return payload_root


def clear_path(path: str):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def stage_payload_with_update_suffix(payload_root: str, install_dir: str, context: UpdateContext) -> List[str]:
    names = [name for name in os.listdir(payload_root) if name not in (".", "..")]
    if not names:
        raise UpdateError("Update package is empty")

    staged = []
    count = len(names)
    for idx, name in enumerate(names, 1):
        context.check_cancelled()
        src = os.path.join(payload_root, name)
        dst = os.path.join(install_dir, name + ".update")
        if os.path.exists(dst) or os.path.islink(dst):
            clear_path(dst)
        if os.path.isdir(src) and not os.path.islink(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
        staged.append(name)
        context.progress("update.auto.status.staging", int(idx * 100 / count))
    return staged


def _write_temp_script(suffix: str, content: str) -> str:
    path = os.path.join(tempfile.gettempdir(), f"pygpt-update-{uuid.uuid4().hex}{suffix}")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    if os.name != "nt":
        os.chmod(path, 0o700)
    return path


def launch_posix_script(content: str) -> str:
    script = _write_temp_script(".sh", content)
    subprocess.Popen(
        ["/bin/sh", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return script


def launch_windows_script(content: str) -> str:
    script = _write_temp_script(".cmd", content.replace("\n", "\r\n"))
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        ["cmd.exe", "/d", "/c", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    return script


def schedule_restart_after_exit(command: List[str]) -> str:
    pid = os.getpid()
    if os.name == "nt":
        cmdline = subprocess.list2cmdline(command)
        content = f"""@echo off
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  ping 127.0.0.1 -n 2 >NUL
  goto wait_loop
)
start "" {cmdline}
del "%~f0"
"""
        return launch_windows_script(content)

    cmdline = " ".join(shlex.quote(part) for part in command)
    content = f"""#!/bin/sh
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
{cmdline} >/dev/null 2>&1 &
rm -f -- "$0"
"""
    return launch_posix_script(content)


def schedule_linux_swap_after_exit(
        install_dir: str,
        names: List[str],
        executable_name: str = "pygpt",
        args: Optional[List[str]] = None,
) -> str:
    pid = os.getpid()
    quoted_dir = shlex.quote(os.path.abspath(install_dir))
    quoted_names = " ".join(shlex.quote(name) for name in names)
    exe = shlex.quote(os.path.join(os.path.abspath(install_dir), executable_name))
    argline = " ".join(shlex.quote(part) for part in (args or []))
    content = f"""#!/bin/sh
set -u
trap 'rm -f -- "$0"' EXIT
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
cd {quoted_dir} || exit 1
set -- {quoted_names}

# Phase 1: move every existing installation item out of the way before
# installing anything. This makes rollback safe even when a later rename
# fails: untouched originals are never deleted.
backup_failed=0
for name in "$@"; do
  rm -rf -- "$name.old"
  if [ -e "$name" ] || [ -L "$name" ]; then
    mv -- "$name" "$name.old" || {{ backup_failed=1; break; }}
  fi
done
if [ $backup_failed -ne 0 ]; then
  for name in "$@"; do
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then
      if [ ! -e "$name" ] && [ ! -L "$name" ]; then mv -- "$name.old" "$name"; fi
    fi
  done
  exit 1
fi

# Phase 2: all originals are backed up now, so an install failure can safely
# remove partially installed new files and restore the complete old payload.
install_failed=0
for name in "$@"; do
  mv -- "$name.update" "$name" || {{ install_failed=1; break; }}
done
if [ $install_failed -ne 0 ]; then
  for name in "$@"; do
    rm -rf -- "$name"
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then mv -- "$name.old" "$name"; fi
  done
  exit 1
fi
if ! chmod +x -- {exe}; then
  for name in "$@"; do
    rm -rf -- "$name"
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then mv -- "$name.old" "$name"; fi
  done
  exit 1
fi
{exe} {argline} >/dev/null 2>&1 &
new_pid=$!
sleep 1
if ! kill -0 "$new_pid" 2>/dev/null; then
  for name in "$@"; do
    rm -rf -- "$name"
    if [ -e "$name.old" ] || [ -L "$name.old" ]; then mv -- "$name.old" "$name"; fi
  done
  {exe} {argline} >/dev/null 2>&1 &
  exit 1
fi
for name in "$@"; do rm -rf -- "$name.old"; done
"""
    return launch_posix_script(content)


def schedule_appimage_swap_after_exit(current_path: str, staged_path: str, args: List[str]) -> str:
    pid = os.getpid()
    current = shlex.quote(os.path.abspath(current_path))
    staged = shlex.quote(os.path.abspath(staged_path))
    old = shlex.quote(os.path.abspath(current_path) + ".old")
    argline = " ".join(shlex.quote(part) for part in args)
    content = f"""#!/bin/sh
set -u
trap 'rm -f -- "$0"' EXIT
while kill -0 {pid} 2>/dev/null; do sleep 0.25; done
rm -f -- {old}
if [ -e {current} ]; then mv -- {current} {old} || exit 1; fi
if ! mv -- {staged} {current}; then
  [ -e {old} ] && mv -- {old} {current}
  exit 1
fi
if ! chmod +x -- {current}; then
  rm -f -- {current}
  [ -e {old} ] && mv -- {old} {current}
  exit 1
fi
{current} {argline} >/dev/null 2>&1 &
new_pid=$!
sleep 1
if ! kill -0 "$new_pid" 2>/dev/null; then
  rm -f -- {current}
  if [ -e {old} ]; then
    mv -- {old} {current}
    {current} {argline} >/dev/null 2>&1 &
  fi
  exit 1
fi
rm -f -- {old}
"""
    return launch_posix_script(content)


def schedule_windows_msi_after_exit(msi_path: str, restart_command: List[str]) -> str:
    pid = os.getpid()
    msi = subprocess.list2cmdline([os.path.abspath(msi_path)])
    restart = subprocess.list2cmdline(restart_command)
    content = f"""@echo off
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  ping 127.0.0.1 -n 2 >NUL
  goto wait_loop
)
start /wait "" msiexec.exe /i {msi}
set "MSI_RC=%ERRORLEVEL%"
if "%MSI_RC%"=="0" goto restart_app
if "%MSI_RC%"=="3010" goto restart_app
goto cleanup
:restart_app
start "" {restart}
:cleanup
del /q {msi} >NUL 2>NUL
del "%~f0"
"""
    return launch_windows_script(content)
