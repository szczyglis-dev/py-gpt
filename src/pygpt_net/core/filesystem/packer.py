#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.02.05 03:00:00                  #
# ================================================== #

import os
import shutil

from uuid import uuid4
from typing import List

class Packer:
    def __init__(self, window=None):
        """
        Archive packer/unpacker

        :param window: Window instance
        """
        self.window = window
        self.zip_ext = [".zip"]
        self.tar_ext = [".tar", ".gz", ".bz2"]

    def is_archive(self, path: str) -> bool:
        """
        Check if path is archive

        :param path: Path to file
        :return: True if archive
        """
        ext = os.path.splitext(path)[1]
        return ext in self.zip_ext or ext in self.tar_ext

    def unpack(self, path: str) -> str:
        """
        Unpack archive

        :param path: path to archive
        :return: path to unpacked directory
        """
        uuid = str(uuid4())
        tmp_dir = os.path.join(self.window.core.config.get_user_dir("tmp"), uuid)
        os.makedirs(tmp_dir, exist_ok=True)
        ext = os.path.splitext(path)[1]
        if ext in self.zip_ext:
            return self.unpack_zip(path, tmp_dir)
        elif ext in self.tar_ext:
            return self.unpack_tar(path, tmp_dir)

    def unpack_zip(self, path: str, dir: str) -> str:
        """
        Unpack archive to temporary directory

        :param path: path to archive
        :param dir: temporary directory
        :return: path to unpacked directory
        """
        import zipfile
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(dir)
        return dir

    def unpack_tar(self, path: str, dir: str) -> str:
        """
        Unpack archive to temporary directory

        :param path: path to archive
        :param dir: temporary directory
        :return: path to unpacked directory
        """
        import tarfile
        with tarfile.open(path, 'r') as tar_ref:
            tar_ref.extractall(dir)
        return dir

    def remove_tmp(self, path: str):
        """
        Remove temporary directory

        :param path: path to directory
        """
        if os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path)

    # ===== New high-level pack/unpack API (non-breaking) =====

    def can_unpack(self, path: str) -> bool:
        """
        Check using stdlib detectors whether given file is a supported archive.
        """
        if not (path and os.path.isfile(path)):
            return False
        try:
            import zipfile, tarfile
            return zipfile.is_zipfile(path) or tarfile.is_tarfile(path)
        except Exception:
            return False

    def _detect_kind(self, path: str) -> str:
        """
        Detect archive kind: 'zip' or 'tar'. Returns '' if unknown.
        """
        try:
            import zipfile, tarfile
            if zipfile.is_zipfile(path):
                return 'zip'
            if tarfile.is_tarfile(path):
                return 'tar'
        except Exception:
            pass
        return ''

    def pack_paths(self, paths: list, fmt: str, dest_dir: str = None, base_name: str = None) -> str:
        """
        Pack given paths into a single archive.

        :param paths: list of files/dirs to include
        :param fmt: 'zip' or 'tar.gz'
        :param dest_dir: output directory (default: common parent of paths)
        :param base_name: output archive base name without extension (optional)
        :return: created archive path or empty string on error
        """
        if not paths:
            return ""
        fs = self.window.core.filesystem
        paths = [os.path.abspath(p) for p in paths if p]
        dest_dir = dest_dir or fs.common_parent_dir(paths)

        if base_name is None:
            if len(paths) == 1:
                name = os.path.basename(paths[0].rstrip(os.sep))
                if os.path.isfile(paths[0]):
                    root, _ = os.path.splitext(name)
                    base_name = root or name
                else:
                    base_name = name
            else:
                base_name = "archive"

        fmt = (fmt or "").lower()
        if fmt == 'zip':
            ext = ".zip"
            out_path = fs.unique_path(dest_dir, base_name, ext)
            try:
                self._pack_zip(paths, out_path)
                return out_path
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass
                return ""
        elif fmt in ('tar.gz', 'tgz'):
            ext = ".tar.gz"
            out_path = fs.unique_path(dest_dir, base_name, ext)
            try:
                self._pack_tar_gz(paths, out_path)
                return out_path
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass
                return ""
        else:
            return ""

    def _pack_zip(self, paths: list, out_path: str):
        """
        Create ZIP archive with selected paths, preserving top-level names.
        """
        import zipfile
        with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for src in paths:
                top = os.path.basename(src.rstrip(os.sep))
                if os.path.isdir(src):
                    for root, dirs, files in os.walk(src):
                        rel = os.path.relpath(root, src)
                        arc_root = top if rel == "." else os.path.join(top, rel)
                        # Add empty directories explicitly
                        if not files and not dirs:
                            zinfo = zipfile.ZipInfo(arc_root + "/")
                            zf.writestr(zinfo, "")
                        for f in files:
                            absf = os.path.join(root, f)
                            arcf = os.path.join(arc_root, f)
                            zf.write(absf, arcf)
                else:
                    zf.write(src, top)

    def _pack_tar_gz(self, paths: list, out_path: str):
        """
        Create TAR.GZ archive with selected paths, preserving top-level names.
        """
        import tarfile
        with tarfile.open(out_path, 'w:gz') as tf:
            for src in paths:
                top = os.path.basename(src.rstrip(os.sep))
                tf.add(src, arcname=top, recursive=True)

    def unpack_to_dir(self, path: str, dest_dir: str) -> str:
        """
        Unpack archive at 'path' into 'dest_dir'.

        :param path: archive file path
        :param dest_dir: destination directory to extract into
        :return: dest_dir on success, empty string otherwise
        """
        if not self.can_unpack(path):
            return ""
        try:
            import zipfile, tarfile
            os.makedirs(dest_dir, exist_ok=True)
            kind = self._detect_kind(path)
            if kind == 'zip':
                with zipfile.ZipFile(path, 'r') as zf:
                    zf.extractall(dest_dir)
            elif kind == 'tar':
                with tarfile.open(path, 'r:*') as tf:
                    tf.extractall(dest_dir)
            else:
                return ""
            return dest_dir
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass
            return ""

    def unpack_to_sibling_dir(self, path: str) -> str:
        """
        Unpack archive into directory placed next to the archive, named after archive base name.

        :param path: archive file path
        :return: created directory path or empty string
        """
        if not (path and os.path.isfile(path)):
            return ""
        parent = os.path.dirname(path)
        base = self.window.core.filesystem.strip_archive_name(os.path.basename(path))
        out_dir = self.window.core.filesystem.unique_dir(parent, base)
        return self.unpack_to_dir(path, out_dir)

    def unpack_here(self, path: str) -> List[str]:
        """
        Extract archive content next to the archive, preserving the archive's own top-level structure.
        - If the archive contains a single top-level directory, that directory is created next to the archive
          (renamed with ' (n)' suffix if needed).
        - Otherwise, each top-level entry (file/dir) is placed next to the archive.
        - Name collisions are resolved using Filesystem.unique_path/unique_dir, producing ' (n)' suffixes.
        Returns a list of created paths.
        """
        created: List[str] = []
        if not self.can_unpack(path):
            return created

        parent_dir = os.path.dirname(path)
        tmp_dir = self.unpack(path)
        if not tmp_dir or not os.path.isdir(tmp_dir):
            return created

        fs = self.window.core.filesystem
        try:
            try:
                entries = os.listdir(tmp_dir)
            except Exception:
                entries = []

            if len(entries) == 1:
                name = entries[0]
                src = os.path.join(tmp_dir, name)
                if os.path.isdir(src):
                    dst = fs.unique_dir(parent_dir, name)
                else:
                    root, ext = os.path.splitext(name)
                    dst = fs.unique_path(parent_dir, root, ext)
                shutil.move(src, dst)
                created.append(dst)
            else:
                for name in entries:
                    src = os.path.join(tmp_dir, name)
                    if os.path.isdir(src):
                        dst = fs.unique_dir(parent_dir, name)
                    else:
                        root, ext = os.path.splitext(name)
                        dst = fs.unique_path(parent_dir, root, ext)
                    shutil.move(src, dst)
                    created.append(dst)
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass
        finally:
            self.remove_tmp(tmp_dir)

        return created