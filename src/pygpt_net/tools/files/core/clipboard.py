#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import os
import shutil
import struct

from PySide6.QtCore import QUrl, QMimeData
from PySide6.QtGui import QGuiApplication, QClipboard


class Clipboard:
    """Files clipboard for one explorer frontend."""

    def __init__(self, explorer):
        self.explorer = explorer
        self.paths = []
        self.mode = None

    def copy(self):
        """Copy currently selected files/dirs to system clipboard and internal buffer."""
        explorer = self.explorer
        paths = explorer.selected_paths()
        if not paths:
            return
        self.set_files(paths, mode='copy')

    def cut(self):
        """Cut currently selected files/dirs to system clipboard and internal buffer (virtual until paste)."""
        explorer = self.explorer
        paths = explorer.selected_paths()
        if not paths:
            return
        self.set_files(paths, mode='cut')

    def paste(self, target_dir: str):
        """Paste clipboard files into given directory and expand/scroll to them."""
        explorer = self.explorer
        if not target_dir:
            target_dir = explorer.directory
        paths, mode = self.files()
        if not paths:
            return

        dest_paths = []
        try:
            if mode == 'cut':
                dest_paths = self.move_paths(paths, target_dir)
            else:
                dest_paths = self.copy_paths(paths, target_dir)
        finally:
            self.paths = []
            self.mode = None

        if os.path.isdir(target_dir):
            explorer.expand_directory(target_dir, center=False)

        try:
            explorer.tool.refresh()
        except Exception:
            explorer.update_view()

        if dest_paths:
            explorer.reveal(dest_paths, select_first=True)

    def paste_current(self):
        """Paste into directory derived from current selection or root when none."""
        explorer = self.explorer
        try:
            sel = explorer.treeView.selectionModel()
            indexes = sel.selectedRows(0) if sel is not None else []
        except Exception:
            indexes = []
        if indexes:
            path = explorer.model.filePath(indexes[0])
            target = path if os.path.isdir(path) else os.path.dirname(path)
        else:
            target = explorer.directory
        self.paste(target)

    def can_paste(self) -> bool:
        """Check if there are files to paste either from system clipboard or internal."""
        explorer = self.explorer
        try:
            md = QGuiApplication.clipboard().mimeData()
            if md and md.hasUrls():
                for url in md.urls():
                    if url.isLocalFile():
                        return True
        except Exception:
            pass
        return bool(self.paths)

    def copy_paths(self, paths: list, target_dir: str):
        """Copy each path into target_dir, directories are copied recursively. Returns list of new destinations."""
        explorer = self.explorer
        dests = []
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        for src in paths:
            try:
                if not os.path.exists(src):
                    continue
                base_name = os.path.basename(src.rstrip(os.sep))
                dst = self.unique_dest(target_dir, base_name)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, copy_function=shutil.copy2)
                else:
                    shutil.copy2(src, dst)
                dests.append(dst)
            except Exception as e:
                try:
                    explorer.window.core.debug.log(e)
                except Exception:
                    pass
        return dests

    def move_paths(self, paths: list, target_dir: str):
        """Move each path into target_dir. Skips invalid moves (into itself). Returns list of new destinations."""
        explorer = self.explorer
        dests = []
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        for src in paths:
            try:
                if not os.path.exists(src):
                    continue
                if os.path.isdir(src):
                    try:
                        sp = os.path.abspath(src)
                        tp = os.path.abspath(target_dir)
                        if os.path.commonpath([sp]) == os.path.commonpath([sp, tp]):
                            continue
                    except Exception:
                        pass
                base_name = os.path.basename(src.rstrip(os.sep))
                dst = os.path.join(target_dir, base_name)
                if os.path.abspath(dst) == os.path.abspath(src):
                    continue
                if os.path.exists(dst):
                    dst = self.unique_dest(target_dir, base_name)
                shutil.move(src, dst)
                dests.append(dst)
            except Exception as e:
                try:
                    explorer.window.core.debug.log(e)
                except Exception:
                    pass
        return dests

    def unique_dest(self, target_dir: str, name: str) -> str:
        """Return a unique destination path in target_dir based on name."""
        explorer = self.explorer
        root, ext = os.path.splitext(name)
        candidate = os.path.join(target_dir, name)
        if not os.path.exists(candidate):
            return candidate
        i = 1
        while True:
            suffix = " - Copy" if i == 1 else f" - Copy ({i})"
            cand = os.path.join(target_dir, f"{root}{suffix}{ext}")
            if not os.path.exists(cand):
                return cand
            i += 1

    def uri_list(self, urls):
        """
        Build RFC compliant text/uri-list payload (CRLF separated).
        """
        explorer = self.explorer
        parts = []
        for u in urls:
            try:
                parts.append(u.toString(QUrl.FullyEncoded))
            except Exception:
                parts.append(u.toString())
        data = ("\r\n".join(parts) + "\r\n").encode("utf-8")
        return data

    def gnome_payload(self, urls, verb: str):
        """
        Build x-special/gnome-copied-files payload:
        copy|cut + newline + list of file:// URLs + trailing newline.
        """
        explorer = self.explorer
        lines = [verb]
        for u in urls:
            try:
                lines.append(u.toString(QUrl.FullyEncoded))
            except Exception:
                lines.append(u.toString())
        return ("\n".join(lines) + "\n").encode("utf-8")

    def set_files(self, paths: list, mode: str = 'copy'):
        """
        Set system clipboard with file urls and cut/copy semantics; keep internal buffer.
        Designed to work across Linux (GNOME/KDE), Windows, and macOS as far as OS allows.
        """
        explorer = self.explorer
        self.paths = [os.path.abspath(p) for p in paths if p]
        self.mode = 'cut' if mode == 'cut' else 'copy'

        try:
            urls = [QUrl.fromLocalFile(p) for p in self.paths]
            md = QMimeData()

            md.setData("text/uri-list", self.uri_list(urls))
            md.setUrls(urls)

            try:
                md.setData("application/x-kde-cutselection", b"1" if self.mode == 'cut' else b"0")
            except Exception:
                pass

            try:
                verb = "cut" if self.mode == 'cut' else "copy"
                payload = self.gnome_payload(urls, verb)
                md.setData("x-special/gnome-copied-files", payload)
                md.setData("x-special/nautilus-clipboard", payload)
            except Exception:
                pass

            try:
                effect = 2 if self.mode == 'cut' else 1
                data = struct.pack("<I", effect)
                md.setData('application/x-qt-windows-mime;value="Preferred DropEffect"', data)
                md.setData("application/x-qt-windows-mime;value=Preferred DropEffect", data)
                md.setData("Preferred DropEffect", data)
            except Exception:
                pass

            cb = QGuiApplication.clipboard()
            cb.setMimeData(md, QClipboard.Clipboard)
            try:
                cb.setMimeData(md, QClipboard.Selection)
            except Exception:
                pass
        except Exception as e:
            try:
                explorer.window.core.debug.log(e)
            except Exception:
                pass

    def files(self):
        """
        Read file urls and cut/copy mode from system clipboard.
        Returns tuple (paths, mode) where mode in {'copy','cut'}.
        Falls back to internal buffer if system clipboard does not provide file urls.
        """
        explorer = self.explorer
        paths = []
        mode = 'copy'
        try:
            md = QGuiApplication.clipboard().mimeData()
        except Exception:
            md = None

        try:
            if md:
                urls = []
                if md.hasUrls():
                    urls = md.urls()
                elif md.hasFormat("text/uri-list"):
                    try:
                        raw = bytes(md.data("text/uri-list")).decode("utf-8", "ignore")
                        for line in raw.splitlines():
                            line = line.strip()
                            if line and not line.startswith("#"):
                                u = QUrl(line)
                                if u.isLocalFile():
                                    urls.append(u)
                    except Exception:
                        pass

                for u in urls:
                    try:
                        if u.isLocalFile():
                            lf = u.toLocalFile()
                            if lf:
                                paths.append(lf)
                    except Exception:
                        continue

                try:
                    if md.hasFormat("application/x-kde-cutselection"):
                        data = bytes(md.data("application/x-kde-cutselection"))
                        if data and (data.startswith(b'1') or data == b"\x01"):
                            mode = 'cut'
                except Exception:
                    pass
                try:
                    if md.hasFormat("x-special/gnome-copied-files"):
                        data = bytes(md.data("x-special/gnome-copied-files")).decode("utf-8", "ignore")
                        if data.splitlines()[0].strip().lower().startswith("cut"):
                            mode = 'cut'
                    elif md.hasFormat("x-special/nautilus-clipboard"):
                        data = bytes(md.data("x-special/nautilus-clipboard")).decode("utf-8", "ignore")
                        if data.splitlines()[0].strip().lower().startswith("cut"):
                            mode = 'cut'
                except Exception:
                    pass
                try:
                    for key in ('application/x-qt-windows-mime;value="Preferred DropEffect"',
                                "application/x-qt-windows-mime;value=Preferred DropEffect",
                                "Preferred DropEffect"):
                        if md.hasFormat(key):
                            data = bytes(md.data(key))
                            if data and len(data) >= 4:
                                value = struct.unpack("<I", data[:4])[0]
                                if value & 2:
                                    mode = 'cut'
                                    break
                except Exception:
                    pass
        except Exception:
            paths = []

        if not paths and self.paths:
            paths = list(self.paths)
            mode = self.mode or 'copy'

        return paths, mode

