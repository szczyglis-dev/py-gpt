#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.23 23:00:00                  #
# ================================================== #

import os
import shutil

from pathlib import PurePath
from typing import Tuple, Any, Union, List, Optional
from urllib.parse import unquote
from uuid import uuid4

from PySide6.QtCore import QUrl

from .actions import Actions
from .editor import Editor
from .packer import Packer
from .parser import Parser
from .types import Types
from .url import Url

class Filesystem:
    def __init__(self, window=None):
        """
        Filesystem core

        :param window: Window instance
        """
        self.window = window
        self.actions = Actions(window)
        self.editor = Editor(window)
        self.packer = Packer(window)
        self.parser = Parser(window)
        self.types = Types(window)
        self.url = Url(window)
        self.workdir_placeholder = "%workdir%"

    def get_shared_data_dir(self) -> str:
        """Return the global profile data directory.

        This is the historical ``<profile workdir>/data`` path and is never
        affected by a project override.
        """
        return self.window.core.config.get_user_dir("data")

    def is_data_storage_enabled(self) -> bool:
        """Return whether img/capture/upload are configured below ``data``."""
        config = self.window.core.config
        return bool(config.has("upload.data_dir") and config.get("upload.data_dir"))

    def get_runtime_dir(
            self,
            name: str,
            ctx=None,
            meta_id: Optional[int] = None,
            group_id: Optional[int] = None,
            create: bool = True,
    ) -> str:
        """Resolve a user directory with project-aware ``data`` semantics.

        Only ``data`` itself is always project-aware. ``img``, ``capture`` and
        ``upload`` follow the project data directory only when the existing
        ``upload.data_dir`` option is enabled. With that option disabled they
        remain rooted in the global profile workdir, exactly as before. All
        remaining application directories are always global.
        """
        config = self.window.core.config
        if name not in config.dirs:
            raise Exception(f"Unknown dir: {name}")

        if name == "data":
            return self.get_data_dir(
                ctx=ctx, meta_id=meta_id, group_id=group_id, create=create,
            )

        data_children = ("img", "capture", "upload")
        if name in data_children and self.is_data_storage_enabled():
            root = self.get_data_dir(
                ctx=ctx, meta_id=meta_id, group_id=group_id, create=create,
            )
            path = os.path.join(root, config.dirs[name])
        else:
            path = os.path.join(config.get_user_path(), config.dirs[name])

        if create:
            try:
                os.makedirs(path, exist_ok=True)
            except OSError:
                pass
        return path

    def _global_profile_roots(self) -> List[str]:
        """Return top-level profile directories that must never be remapped.

        This guard matters when a custom project workdir is the profile root or
        one of its parents. In that case a simple ``path is inside project``
        check would otherwise incorrectly classify e.g. global ``img`` or
        ``tmp`` as project data.
        """
        config = self.window.core.config
        data_children = {"img", "capture", "upload"}
        data_storage = self.is_data_storage_enabled()
        roots = []
        for name, rel in config.dirs.items():
            if name == "data":
                continue
            if data_storage and name in data_children:
                # These are intentionally children of the active data root.
                continue
            roots.append(os.path.join(config.get_user_path(), rel))
        return roots

    def is_global_profile_path(
            self,
            path: str,
            ctx=None,
            meta_id: Optional[int] = None,
            group_id: Optional[int] = None,
    ) -> bool:
        """Return True when ``path`` belongs to a non-project profile tree.

        This is primarily an overlap guard for custom project data roots that
        are equal to, or are parents of, the base PyGPT profile directory.
        ``tmp`` and all other ordinary profile roots always win over project
        data.  The shared/base ``data`` tree is also protected when a project
        override points somewhere else.
        """
        if not path:
            return False

        for root in self._global_profile_roots():
            if self._is_path_in(path, root):
                return True

        shared_data = self.get_shared_data_dir()
        active_data = self.get_data_dir(
            ctx=ctx, meta_id=meta_id, group_id=group_id, create=False,
        )
        if os.path.normcase(os.path.abspath(active_data)) != os.path.normcase(os.path.abspath(shared_data)):
            if self._is_path_in(path, shared_data):
                return True

        return False

    def _resolve_group_id(
            self,
            ctx=None,
            meta_id: Optional[int] = None,
            group_id: Optional[int] = None,
    ) -> Optional[int]:
        """Resolve a project/group ID for a runtime operation.

        An explicitly supplied context/meta is authoritative. In particular,
        a context that belongs to no project must resolve to the shared data
        workdir even if the user switches the UI to a project meanwhile.
        """
        if group_id is not None:
            try:
                value = int(group_id)
                return value if value > 0 else None
            except (TypeError, ValueError):
                return None

        if ctx is not None:
            meta = getattr(ctx, "meta", None)
            if meta is not None:
                value = getattr(meta, "group_id", None)
                try:
                    value = int(value)
                    return value if value > 0 else None
                except (TypeError, ValueError):
                    return None

            # Accept a CtxMeta-like object as well as a CtxItem. This keeps the
            # resolver useful for UI/provider paths that already own metadata
            # but do not wrap it in a message item.
            if hasattr(ctx, "group_id"):
                value = getattr(ctx, "group_id", None)
                try:
                    value = int(value)
                    return value if value > 0 else None
                except (TypeError, ValueError):
                    return None

            if meta_id is None:
                meta_id = getattr(ctx, "meta_id", None)

        if meta_id is not None:
            try:
                meta = self.window.core.ctx.get_meta_by_id(int(meta_id))
            except (TypeError, ValueError):
                meta = None
            if meta is None:
                return None
            value = getattr(meta, "group_id", None)
            try:
                value = int(value)
                return value if value > 0 else None
            except (TypeError, ValueError):
                return None

        # No concrete context was supplied (for example a UI path lookup), so
        # resolve against the conversation that is currently selected.
        try:
            meta = self.window.core.ctx.get_current_meta()
        except Exception:
            meta = None
        if meta is None:
            return None
        try:
            value = int(getattr(meta, "group_id", None))
            return value if value > 0 else None
        except (TypeError, ValueError):
            return None

    def get_data_dir(
            self,
            ctx=None,
            meta_id: Optional[int] = None,
            group_id: Optional[int] = None,
            create: bool = True,
    ) -> str:
        """Return the runtime ``data`` workdir for a context/project.

        Only the user-facing ``data`` directory can be overridden by a project.
        Every other profile directory continues to use ``Config.get_user_dir``.
        """
        shared = self.get_shared_data_dir()
        resolved_group_id = self._resolve_group_id(
            ctx=ctx, meta_id=meta_id, group_id=group_id,
        )
        if resolved_group_id is None:
            return shared

        try:
            group = self.window.core.ctx.get_group_by_id(resolved_group_id)
        except Exception:
            group = None
        if group is None:
            return shared

        extra = getattr(group, "extra", None)
        if not isinstance(extra, dict):
            return shared
        if bool(extra.get("use_shared_workdir", True)):
            return shared

        value = str(extra.get("workdir") or "").strip()
        if not value:
            return shared
        value = os.path.expandvars(os.path.expanduser(value))
        if not os.path.isabs(value):
            value = os.path.abspath(value)
        value = os.path.normpath(value)
        if create:
            try:
                os.makedirs(value, exist_ok=True)
            except OSError:
                # Keep the configured path. The actual file operation will
                # provide the useful permission/mount error to the caller.
                pass
        return value

    def from_sandbox_data_path(self, path: str, ctx=None) -> str:
        """Map a Docker ``/data`` path to the active host data workdir.

        This helper is intentionally explicit: host absolute paths are not
        globally reinterpreted. Call it only when a value is known to come
        from a sandbox/container namespace.
        """
        if not path:
            return path
        raw = unquote(str(path)).strip()
        if raw.lower().startswith("sandbox:"):
            raw = raw[len("sandbox:"):].strip()
        normalized = raw.replace("\\", "/")
        if normalized == "/data" or normalized.startswith("/data/"):
            tail = normalized[len("/data"):].lstrip("/")
            root = self.get_data_dir(ctx=ctx)
            if not tail:
                return root
            return os.path.join(root, *[part for part in tail.split("/") if part])
        return path

    def resolve_sandbox_path(self, path: str, ctx=None) -> str:
        """Resolve a model-facing ``sandbox:`` path to a host path.

        ``/data`` is the only sandbox root that follows the active project.
        ``/pygpt_tmp`` and all ordinary profile directories (notably ``tmp``)
        stay rooted in the base profile.  Absolute host paths emitted by a
        tool are preserved when they already point inside the base profile or
        the active project data root.
        """
        if not path:
            return path

        raw = unquote(str(path)).strip()
        if raw.lower().startswith("sandbox:"):
            raw = raw[len("sandbox:"):].strip()

        normalized = raw.replace("\\", "/")

        # sandbox:/C:/... is a common model-emitted spelling of an absolute
        # Windows host path. Drop only the synthetic leading slash; do not do
        # this for POSIX paths.
        try:
            is_windows = self.window.core.platforms.is_windows()
        except Exception:
            is_windows = os.name == "nt"
        if is_windows and len(normalized) >= 4 \
                and normalized[0] == "/" and normalized[1].isalpha() \
                and normalized[2] == ":" and normalized[3] == "/":
            raw = raw[1:]
            normalized = normalized[1:]

        # Docker/project data namespace.
        if normalized == "/data" or normalized.startswith("/data/"):
            return self.from_sandbox_data_path(normalized, ctx=ctx)

        # Internal interpreter temporary namespace is always global/base.
        if normalized == "/pygpt_tmp" or normalized.startswith("/pygpt_tmp/"):
            tail = normalized[len("/pygpt_tmp"):].lstrip("/")
            root = self.window.core.config.get_user_dir("tmp")
            return root if not tail else os.path.join(
                root, *[part for part in tail.split("/") if part]
            )

        # Some model/tool outputs wrap an already valid absolute host path in
        # sandbox:. Do not strip its leading slash and accidentally reinterpret
        # it relative to the project data directory.
        host_candidate = os.path.normpath(raw)
        if os.path.isabs(host_candidate):
            base = self.window.core.config.get_user_path()
            data = self.get_data_dir(ctx=ctx)
            if self._is_path_in(host_candidate, base) or self._is_path_in(host_candidate, data):
                return host_candidate

        # Virtual profile roots such as sandbox:/tmp/x or sandbox:/img/x.
        # Only img/capture/upload may follow project data, and only when the
        # existing single-data-directory option is enabled. tmp always stays
        # global because get_runtime_dir() deliberately never remaps it.
        for name, rel in self.window.core.config.dirs.items():
            if name == "data":
                continue
            rel_norm = str(rel).replace("\\", "/").strip("/")
            prefix = "/" + rel_norm
            if normalized == prefix or normalized.startswith(prefix + "/"):
                tail = normalized[len(prefix):].lstrip("/")
                root = self.get_runtime_dir(name, ctx=ctx)
                return root if not tail else os.path.join(
                    root, *[part for part in tail.split("/") if part]
                )

        # Historical sandbox links treated /foo as a workdir-relative path.
        # Keep that fallback for unknown virtual roots.
        return raw.lstrip("/\\")

    @staticmethod
    def _is_path_in(path: str, root: str) -> bool:
        try:
            path_abs = os.path.normcase(os.path.abspath(path))
            root_abs = os.path.normcase(os.path.abspath(root))
            return os.path.commonpath([path_abs, root_abs]) == root_abs
        except (TypeError, ValueError, OSError):
            return False

    def install(self):
        """Install provider data"""
        # data directory
        data_dir = self.get_shared_data_dir()
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        # upload directory
        upload_dir = self.window.core.config.get_user_dir('upload')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)

        self.install_css()  # install custom css styles

    def install_css(self, force: bool = False):
        """
        Install custom css styles

        :param force: force install
        """
        css_dir = os.path.join(self.window.core.config.path, 'css')
        if not os.path.exists(css_dir):
            os.mkdir(css_dir)

        src_dir = os.path.join(self.window.core.config.get_app_path(), 'data', 'css')
        dst_dir = os.path.join(self.window.core.config.path, 'css')
        app_styles = os.listdir(src_dir)
        try:
            for style in app_styles:
                src = os.path.join(src_dir, style)
                dst = os.path.join(dst_dir, style)
                if (not os.path.exists(dst) or force) and os.path.exists(src):
                    shutil.copyfile(src, dst)
        except Exception as e:
            print("Error while installing css files: ", e)

    def backup_custom_css(self):
        """Backup user custom css styles"""
        css_dir = os.path.join(self.window.core.config.path, 'css')
        backup_file_extension = '.backup'
        user_styles = os.listdir(css_dir)
        for style in user_styles:
            src = os.path.join(css_dir, style)
            dst = os.path.join(css_dir, style + backup_file_extension)
            if os.path.exists(src):
                shutil.copyfile(src, dst)

    def make_local(self, path: str, ctx=None, meta_id: Optional[int] = None, group_id: Optional[int] = None) -> str:
        """
        Make a portable placeholder path.

        Project workdirs are serialized through the historical
        ``%workdir%/data`` namespace so saved conversations remain portable and
        old paths continue to resolve after switching projects.
        """
        if not path:
            return path
        native = os.path.normpath(path)
        base = self.window.core.config.get_user_path()
        shared_data = self.get_shared_data_dir()
        data_dir = self.get_data_dir(ctx=ctx, meta_id=meta_id, group_id=group_id)

        # If the custom project data root overlaps the global profile root,
        # global application-owned directories must win. Otherwise e.g.
        # <profile>/img/foo.png could be serialized as %workdir%/data/img/foo
        # and later resolve inside the project. This is especially important
        # when upload.data_dir is disabled.
        if os.path.normcase(os.path.abspath(data_dir)) != os.path.normcase(os.path.abspath(shared_data)):
            if self.is_global_profile_path(
                    native, ctx=ctx, meta_id=meta_id, group_id=group_id,
            ):
                # Ordinary profile roots (tmp/img/capture/upload/etc.) keep
                # using %workdir% relative to the base profile.  The shared
                # data tree is the one exception: %workdir%/data intentionally
                # means the active project, so an explicit path into shared
                # data must remain absolute to preserve its original target.
                if self._is_path_in(native, shared_data):
                    return path
                rel = os.path.relpath(native, base)
                if rel == ".":
                    return self.workdir_placeholder
                return os.path.join(self.workdir_placeholder, rel)

        if self._is_path_in(native, data_dir):
            rel = os.path.relpath(native, data_dir)
            prefix = self.workdir_placeholder + os.sep + "data"
            if rel == ".":
                return prefix
            return os.path.join(prefix, rel)

        if self._is_path_in(native, base):
            rel = os.path.relpath(native, base)
            if rel == ".":
                return self.workdir_placeholder
            return os.path.join(self.workdir_placeholder, rel)
        return path

    def make_local_list(self, paths: list, ctx=None) -> list:
        """
        Make local placeholder paths

        :param paths: list with paths to prepare
        :return: local paths with working dir placeholder
        """
        return [self.make_local(path, ctx=ctx) for path in paths]

    def make_local_list_img(self, paths: List[str], ctx=None) -> List[str]:
        """
        Make local placeholder paths for images

        :param paths: list with paths to prepare
        :return: local paths with working dir placeholder
        """
        img_ext = self.types.get_img_ext()
        result = []
        for path in paths:
            if path.endswith(tuple(img_ext)):
                result.append(self.make_local(path, ctx=ctx))
        return result

    def get_url(self, url: str) -> QUrl:
        """
        Make current OS-specific URL to open file or directory.

        Always use QUrl.fromLocalFile() for filesystem paths.  In particular,
        manually prefixing a Windows path such as ``C:\\Users\\...`` with
        ``file:///`` leaves backslashes in the URL.  Qt then percent-encodes
        them as ``%5C`` when the link is clicked.

        :param url: URL or local path to prepare
        :return: URL to open file or directory
        """
        if self.is_schema(url):
            return QUrl(url, QUrl.TolerantMode)
        return QUrl.fromLocalFile(url)

    def normalize_local_path(
            self,
            path: str,
            auto_prefix: bool = True,
            ctx=None
    ) -> str:
        """
        Normalize a local path received directly or through a Qt URL.

        This also repairs legacy/malformed Windows links where backslashes
        were serialized as ``%5C`` (for example ``C:%5CUsers%5C...``).

        :param path: local path, file URL or workdir-relative path
        :param auto_prefix: add current workdir for relative paths
        :return: normalized local filesystem path
        """
        if not path:
            return path

        path = unquote(path)

        # Resolve the sandbox namespace before generic workdir handling.
        # In particular, preserve real absolute host paths and keep tmp rooted
        # in the base profile; only /data follows the active project.
        if path.lower().startswith('sandbox:'):
            path = self.resolve_sandbox_path(path, ctx=ctx)
            if os.path.isabs(path):
                return os.path.normpath(path)

        if path.startswith('file://'):
            # Legacy Windows links could contain backslashes inside file:///.
            # Normalize them before asking Qt to convert the URL to a path.
            file_url = path.replace('\\', '/')
            local = QUrl(file_url, QUrl.TolerantMode).toLocalFile()
            if local:
                path = unquote(local)
            else:
                # Fallback for malformed legacy file URLs.
                path = file_url.replace('file:///', '', 1).replace('file://', '', 1)
                path = unquote(path)

        return self.to_workdir(path, auto_prefix=auto_prefix, ctx=ctx)

    def get_local_url(self, path: str, ctx=None) -> str:
        """
        Convert a local/workdir path to a properly encoded file URL.

        :param path: local path or path containing the %workdir% placeholder
        :return: encoded file URL
        """
        path = self.normalize_local_path(path, ctx=ctx)
        return QUrl.fromLocalFile(path).toString(QUrl.FullyEncoded)

    def get_path(self, path: str) -> str:
        """
        Prepare current OS-specific path from given path

        :param path: path to prepare
        :return: prepared OS-specific path
        """
        parts = PurePath(path).parts
        if len(parts) > 1:
            return str(os.path.join(*parts))  # rebuild OS directory separators
        return path

    def to_workdir(
            self,
            path: str,
            auto_prefix: bool = True,
            ctx=None,
            meta_id: Optional[int] = None,
            group_id: Optional[int] = None,
    ) -> str:
        """Resolve placeholders while remapping only the ``data`` branch.

        ``%workdir%/data`` points at the active project data directory. Other
        paths under ``%workdir%`` keep using the global profile workdir.
        """
        if not path:
            return path

        path = self.get_path(path)
        base_workdir = self.window.core.config.get_user_path()
        data_workdir = self.get_data_dir(
            ctx=ctx, meta_id=meta_id, group_id=group_id,
        )

        if self.workdir_placeholder in path:
            before, after = path.split(self.workdir_placeholder, 1)
            normalized_after = after.replace("\\", "/")
            if normalized_after == "/data" or normalized_after.startswith("/data/"):
                tail = normalized_after[len("/data"):].lstrip("/")
                resolved = data_workdir if not tail else os.path.join(
                    data_workdir, *[part for part in tail.split("/") if part],
                )
                return before + resolved
            return path.replace(self.workdir_placeholder, base_workdir)

        if not auto_prefix:
            return path

        # A relative path explicitly rooted at data belongs to the runtime data
        # directory. This preserves legacy ``data/foo`` and sandbox:/data/foo.
        portable = path.replace("\\", "/")
        if portable == "data" or portable.startswith("data/"):
            tail = portable[len("data"):].lstrip("/")
            return data_workdir if not tail else os.path.join(
                data_workdir, *[part for part in tail.split("/") if part],
            )

        # Old versions compatibility, < 2.0.113. This intentionally targets the
        # global profile root; only its data child is project-remappable above.
        work_dir = base_workdir
        if work_dir.endswith('.config/pygpt-net'):
            work_dir = work_dir.rsplit('/.config/pygpt-net', 1)[0]
        elif work_dir.endswith('.config\\pygpt-net'):
            work_dir = work_dir.rsplit('\\.config\\pygpt-net', 1)[0]

        if self.window.core.platforms.is_windows():
            dir_index = path.find('\\.config\\pygpt-net\\') + 1
        else:
            dir_index = path.find('/.config/pygpt-net/') + 1

        parts = path[dir_index:]
        return os.path.join(work_dir, parts)

    def extract_local_url(self, path: str, ctx=None) -> Tuple[str, str]:
        """
        Extract a local URL and native filesystem path.

        :param path: local path or URL
        :return: URL, native path
        """
        if path.startswith('http://') or path.startswith('https://'):
            return path, path

        path = self.normalize_local_path(path, ctx=ctx)
        url = QUrl.fromLocalFile(path).toString(QUrl.FullyEncoded)
        return url, path

    def get_workdir_prefix(self) -> str:
        """
        Get a properly encoded file URL for the current workdir.

        :return: workdir file URL
        """
        return QUrl.fromLocalFile(
            self.window.core.config.get_user_path()
        ).toString(QUrl.FullyEncoded)

    def in_work_dir(self, path: str, ctx=None) -> bool:
        """Check if a path is inside the active runtime data directory."""
        return self._is_path_in(path, self.get_data_dir(ctx=ctx))

    def store_upload(self, path: str, ctx=None) -> str:
        """
        Store file in upload directory

        :param path: path to uploading file
        :return: path to stored uploaded file
        """
        upload_dir = self.get_runtime_dir("upload", ctx=ctx)
        file_name = os.path.basename(path)
        upload_path = os.path.join(upload_dir, file_name)
        # if file exists, store in UUID subdir
        if os.path.exists(upload_path):
            subdir = str(uuid4())
            os.makedirs(os.path.join(upload_dir, subdir), exist_ok=True)
            upload_path = os.path.join(upload_dir, subdir, file_name)
        shutil.copyfile(path, upload_path)
        return upload_path

    def remove_upload(self, path: str, ctx=None):
        """
        Delete uploaded file

        :param path: path to uploading file
        """
        upload_dir = self.get_runtime_dir("upload", ctx=ctx)
        if path.startswith(upload_dir):
            if os.path.exists(path):
                os.remove(path)

    def is_schema(self, path: str) -> bool:
        """
        Check if path has schema prefix (http, https, file)

        :param path: path to check
        :return: True if path has schema prefix
        """
        return path.startswith('file://') or path.startswith('http://') or path.startswith('https://')

    def sizeof_fmt(self, num: Any, suffix: str = 'B'):
        """
        Convert numbers to human-readable unit formats.

        :param num: number to convert
        :param suffix: suffix to add
        :return: human-readable format
        """
        if not isinstance(num, (int, float)):
            return '-'
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return f"{num:.1f} {unit}{suffix}".replace('.', ',')
            num /= 1024.0
        return f"{num:.1f} Yi{suffix}".replace('.', ',')

    def get_directory_size(
            self,
            directory: str,
            human_readable: bool = True
    ) -> Union[str, int]:
        """
        Calculate the total size of the given directory

        :param directory: directory path
        :param human_readable: return human-readable format
        :return: total size of the directory
        """
        total_size = 0
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)

        if human_readable:
            return self.sizeof_fmt(total_size)
        return total_size

    def get_datadir_size(
            self,
            path: str,
            human_readable: bool = True
    ) -> Union[str, int]:
        """
        Calculate the total size of the given data directory

        :param path: working directory path
        :param human_readable: return human-readable format
        :return: total size of the data directory
        """
        data_dir = os.path.join(path, 'data')
        return self.get_directory_size(data_dir, human_readable)

    def get_db_size(
            self,
            path: str,
            human_readable: bool = True
    ) -> Union[str, int]:
        """
        Calculate the total size of the given database

        :param path: working directory path
        :param human_readable: return human-readable format
        :return: total size of the database file
        """
        db_files = ["db.sqlite", "db.sqlite.backup"]
        total_size = 0
        for file in db_files:
            db_file = os.path.join(path, file)
            if os.path.exists(db_file):
                total_size += os.path.getsize(db_file)
        if human_readable:
            return self.sizeof_fmt(total_size)
        return total_size

    def get_free_disk_space(
            self,
            directory: str,
            human_readable: bool = True
    ) -> Union[str, int]:
        """
        Check free disk space in the given directory

        :param directory: directory path
        :param human_readable: return human-readable format
        :return: free disk space
        """
        total, used, free = shutil.disk_usage(os.path.dirname(directory))
        if human_readable:
            return self.sizeof_fmt(free)
        return free

    def copy_workdir(
            self,
            path: str,
            new_path: str,
            copy_db: bool = True,
            copy_datadir: bool = True
    ) -> bool:
        """
        Copy working directory

        :param path: current working directory
        :param new_path: new working directory
        :param copy_db: copy database file
        :param copy_datadir: copy data directory
        :return: True if working directory is copied
        """
        excluded_files = []
        excluded_dirs = []
        if not copy_db:
            excluded_files.append("db.sqlite")
            excluded_files.append("db.sqlite.backup")
        if not copy_datadir:
            excluded_dirs.append("data")
        if os.path.isdir(path):
            for item in os.listdir(path):
                s = os.path.join(path, item)
                d = os.path.join(new_path, item)
                if os.path.isdir(s):
                    if item not in excluded_dirs:
                        shutil.copytree(s, d, symlinks=False, ignore=None)
                else:
                    if item not in excluded_files:
                        shutil.copy2(s, d)

        # put empty "path.cfg"
        lock_file = os.path.join(new_path, 'path.cfg')
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write('')

        # remove "profile.json" if exists
        profile_file = os.path.join(new_path, 'profile.json')
        if os.path.exists(profile_file):
            os.remove(profile_file)
        return True

    def clear_workdir(
            self,
            path: str,
            remove_db: bool = True,
            remove_datadir: bool = True
    ) -> bool:
        """
        Clear working directory

        :param path: path to working directory
        :param remove_db: remove database file
        :param remove_datadir: remove data directory
        :return: True if working directory is cleared
        """
        excluded_files = ["app.log", "path.cfg", "profile.json"]
        excluded_dirs = []
        if not remove_datadir:
            excluded_dirs.append("data")
        if not remove_db:
            excluded_files.append("db.sqlite")
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path):
                if item not in excluded_files:
                    os.remove(item_path)
            else:
                if item not in excluded_dirs:
                    if os.path.exists(item_path) and os.path.isdir(item_path):
                        shutil.rmtree(item_path)

        return True

    def is_workdir_in_path(self, path: str) -> bool:
        """
        Check if workdir is in path

        :param path: path to check
        :return: True if workdir is in path
        """
        files = ["config.json", "db.sqlite"]
        for file in files:
            if not os.path.exists(os.path.join(path, file)):
                return False
        return True

    def is_directory_empty(self, path: str) -> bool:
        """
        Check if directory is empty

        :param path: directory path
        :return: True if directory is empty
        """
        return len(os.listdir(path)) == 0

    def get_files_from_dir(
            self,
            path: str,
            recursive: bool = True
    ) -> list:
        """
        Get files from directory

        :param path: directory path
        :param recursive: recursive search
        :return: list of files
        """
        files = []
        if not os.path.exists(path):
            return files
        if recursive:
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
                if not recursive:
                    break
        else:
            files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        return files

    # ===== Helpers for pack/unpack =====

    def common_parent_dir(self, paths: List[str]) -> str:
        """
        Return a sensible common parent directory for the given paths.
        For a single directory selection returns that directory; for a single file returns its parent.
        For multiple selections returns a common existing parent, if resolvable, otherwise the parent of the first path.
        """
        if not paths:
            return self.window.core.config.get_user_path()
        norm = []
        for p in paths:
            p = os.path.abspath(p)
            norm.append(p if os.path.isdir(p) else os.path.dirname(p))
        if len(norm) == 1:
            return norm[0]
        try:
            cp = os.path.commonpath(norm)
            if os.path.isdir(cp):
                return cp
            return os.path.dirname(cp)
        except Exception:
            return norm[0]

    def unique_path(self, directory: str, base_name: str, ext: str) -> str:
        """
        Return a unique file path within 'directory' for 'base_name' and 'ext' (ext should include dot or be empty).
        Uses 'name', 'name (1)', 'name (2)', ... scheme.
        """
        os.makedirs(directory, exist_ok=True)
        candidate = os.path.join(directory, f"{base_name}{ext}")
        if not os.path.exists(candidate):
            return candidate
        i = 1
        while True:
            cand = os.path.join(directory, f"{base_name} ({i}){ext}")
            if not os.path.exists(cand):
                return cand
            i += 1

    def unique_dir(self, directory: str, base_name: str) -> str:
        """
        Return a unique directory path 'directory/base_name', adding ' (n)' suffix when needed.
        """
        os.makedirs(directory, exist_ok=True)
        candidate = os.path.join(directory, base_name)
        if not os.path.exists(candidate):
            return candidate
        i = 1
        while True:
            cand = os.path.join(directory, f"{base_name} ({i})")
            if not os.path.exists(cand):
                return cand
            i += 1

    def strip_archive_name(self, filename: str) -> str:
        """
        Strip known archive extensions (.zip, .tar, .tar.gz, .tar.bz2, .tar.xz, .tgz, .tbz2, .txz) from a filename.
        Returns filename without extension(s).
        """
        combos = ['.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2', '.txz']
        lower = filename.lower()
        for suf in combos:
            if lower.endswith(suf):
                return filename[:-len(suf)]
        root, ext = os.path.splitext(filename)
        if ext.lower() in ('.zip', '.tar'):
            return root
        return root