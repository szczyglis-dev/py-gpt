#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 13:00:00                  #
# ================================================== #

import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4


class ProfileExportError(Exception):
    """Base profile import/export error."""


class ProfileExportCancelled(ProfileExportError):
    """Raised when a profile import/export operation is cancelled."""


class InvalidProfileArchive(ProfileExportError):
    """Raised when an import archive is not a supported PyGPT profile export."""


class InsufficientDiskSpace(ProfileExportError):
    """Raised when an operation cannot fit on the target filesystem."""

    def __init__(self, required: int, free: int):
        super().__init__(f"Not enough free disk space: required={required}, free={free}")
        self.required = int(required)
        self.free = int(free)


class ProfileExporter:
    """Core implementation for portable profile ZIP import/export."""

    META_FILE = "export_meta.json"

    SECTION_DATABASE = "db"
    SECTION_CONFIG = "config"
    SECTION_FILES = "files"
    SECTION_DATA = "data"
    SECTIONS = (
        SECTION_DATABASE,
        SECTION_CONFIG,
        SECTION_FILES,
        SECTION_DATA,
    )

    ARCHIVE_PREFIX = {
        SECTION_DATABASE: "database",
        SECTION_CONFIG: "config",
        SECTION_FILES: "files",
        SECTION_DATA: "workdir_data",
    }

    CONFIG_DIRS = {"presets", "css", "locale", "fonts"}
    RUNTIME_DIRS = {"tmp", "cache", "__pycache__"}
    EXCLUDED_ROOT_FILES = {
        "app.log",
        "path.cfg",
        "profile.json",
        "profile.json.lock",
        "db.sqlite.backup",
        "db.sqlite-wal",
        "db.sqlite-shm",
    }
    COPY_CHUNK = 1024 * 1024
    SPACE_RESERVE = 64 * 1024 * 1024
    SPACE_MARGIN = 1.15

    def __init__(self, window=None):
        self.window = window

    # ------------------------------------------------------------------
    # Discovery / sizes
    # ------------------------------------------------------------------

    def get_workdir(self) -> str:
        return os.path.abspath(self.window.core.config.get_user_path())

    def get_section_sizes(
            self,
            workdir: Optional[str] = None,
            cancelled: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, int]:
        root = os.path.abspath(workdir or self.get_workdir())
        result = {}
        for section in self.SECTIONS:
            self._check_cancel(cancelled)
            result[section] = self._section_size(root, section, cancelled)
        return result

    def _section_size(
            self,
            workdir: str,
            section: str,
            cancelled: Optional[Callable[[], bool]] = None,
    ) -> int:
        total = 0
        for path, _relative in self._section_paths(workdir, section):
            self._check_cancel(cancelled)
            total += self._path_size(path, cancelled)
        return total

    def _section_paths(
            self,
            workdir: str,
            section: str,
            excluded: Optional[Iterable[str]] = None,
    ) -> List[Tuple[str, str]]:
        root = Path(workdir)
        if not root.exists():
            return []

        excluded_paths = self._normalized_paths(excluded)

        def is_excluded(path: Path) -> bool:
            return self._path_is_excluded(str(path), excluded_paths)

        if section == self.SECTION_DATABASE:
            path = root / "db.sqlite"
            return [(str(path), "db.sqlite")] if path.is_file() and not is_excluded(path) else []

        if section == self.SECTION_DATA:
            path = root / "data"
            return [(str(path), "data")] \
                if path.is_dir() and not path.is_symlink() and not is_excluded(path) else []

        result: List[Tuple[str, str]] = []
        try:
            children = list(root.iterdir())
        except OSError:
            return result

        for child in children:
            name = child.name
            if child.is_symlink() or is_excluded(child):
                continue
            if child.is_file():
                if name in self.EXCLUDED_ROOT_FILES or name == "db.sqlite":
                    continue
                is_config = child.suffix.lower() == ".json"
                if section == self.SECTION_CONFIG and is_config:
                    result.append((str(child), name))
                elif section == self.SECTION_FILES and not is_config:
                    result.append((str(child), name))
                continue

            if not child.is_dir():
                continue
            if name == "data" or name in self.RUNTIME_DIRS:
                continue
            if section == self.SECTION_CONFIG and name in self.CONFIG_DIRS:
                result.append((str(child), name))
            elif section == self.SECTION_FILES and name not in self.CONFIG_DIRS:
                result.append((str(child), name))

        result.sort(key=lambda item: item[1].lower())
        return result

    def _path_size(
            self,
            path: str,
            cancelled: Optional[Callable[[], bool]] = None,
            excluded: Optional[Iterable[str]] = None,
    ) -> int:
        excluded_paths = self._normalized_paths(excluded)
        if self._path_is_excluded(path, excluded_paths) or os.path.islink(path):
            return 0
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)
        except OSError:
            return 0

        total = 0
        if not os.path.isdir(path):
            return 0
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            self._check_cancel(cancelled)
            dirnames[:] = [
                name for name in dirnames
                if not os.path.islink(os.path.join(dirpath, name))
                and not self._path_is_excluded(
                    os.path.join(dirpath, name), excluded_paths
                )
            ]
            for filename in filenames:
                self._check_cancel(cancelled)
                file_path = os.path.join(dirpath, filename)
                if os.path.islink(file_path) or self._path_is_excluded(
                        file_path, excluded_paths):
                    continue
                try:
                    total += os.path.getsize(file_path)
                except OSError:
                    pass
        return total

    @staticmethod
    def format_size(size: int) -> str:
        """Use explicit MB/GB units for compact dialog size hints."""
        size = max(0, int(size or 0))
        mb = size / (1024 * 1024)
        if mb < 1024:
            if mb == 0:
                return "0 MB"
            if mb >= 10:
                return f"{mb:.0f} MB"
            return f"{mb:.1f} MB"
        gb = mb / 1024
        if gb >= 10:
            return f"{gb:.0f} GB"
        return f"{gb:.1f} GB"

    def estimate_export_required(self, sizes: Dict[str, int], selected: Iterable[str]) -> int:
        selected = set(selected)
        raw = sum(int(sizes.get(section, 0) or 0) for section in selected)
        db_snapshot = int(sizes.get(self.SECTION_DATABASE, 0) or 0) \
            if self.SECTION_DATABASE in selected else 0
        return int(raw * self.SPACE_MARGIN) + db_snapshot + self.SPACE_RESERVE

    def estimate_import_required(
            self,
            zip_path: str,
            selected: Iterable[str],
    ) -> int:
        selected = set(selected)
        sizes = self.get_archive_section_sizes(zip_path)
        raw = sum(int(sizes.get(section, 0) or 0) for section in selected)
        return int(raw * self.SPACE_MARGIN) + self.SPACE_RESERVE

    @staticmethod
    def get_free_space(path: str) -> int:
        probe = os.path.abspath(path)
        while not os.path.exists(probe):
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        return int(shutil.disk_usage(probe).free)

    def ensure_space(self, path: str, required: int):
        free = self.get_free_space(path)
        if free < int(required):
            raise InsufficientDiskSpace(required=required, free=free)

    # ------------------------------------------------------------------
    # Archive metadata / validation
    # ------------------------------------------------------------------

    def read_meta(self, zip_path: str) -> Dict:
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                try:
                    raw = archive.read(self.META_FILE)
                except KeyError as exc:
                    raise InvalidProfileArchive("Missing export_meta.json") from exc
        except (zipfile.BadZipFile, OSError) as exc:
            raise InvalidProfileArchive(str(exc)) from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            raise InvalidProfileArchive("Invalid export_meta.json") from exc

        if not isinstance(data, dict):
            raise InvalidProfileArchive("Invalid export metadata")
        if not isinstance(data.get("app_version"), str) or not data.get("app_version"):
            raise InvalidProfileArchive("Missing app_version")
        if not isinstance(data.get("exported"), list) or not data.get("exported"):
            raise InvalidProfileArchive("Missing exported sections")
        exported = data.get("exported")
        if any(section not in self.SECTIONS for section in exported):
            raise InvalidProfileArchive("Unsupported export section")
        if len(set(exported)) != len(exported):
            raise InvalidProfileArchive("Duplicated export section")
        if not isinstance(data.get("exported_at"), str) or not data.get("exported_at"):
            raise InvalidProfileArchive("Missing exported_at")
        return data

    def get_archive_section_sizes(self, zip_path: str) -> Dict[str, int]:
        result = {section: 0 for section in self.SECTIONS}
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                for info in archive.infolist():
                    if info.is_dir() or info.filename == self.META_FILE:
                        continue
                    self._validate_member(info)
                    normalized = info.filename.replace("\\", "/")
                    for section, prefix in self.ARCHIVE_PREFIX.items():
                        if normalized.startswith(prefix + "/"):
                            result[section] += int(info.file_size)
                            break
        except (zipfile.BadZipFile, OSError, InvalidProfileArchive):
            raise
        return result

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_profile(
            self,
            destination: str,
            selected: Iterable[str],
            app_version: str,
            exported_at: Optional[str] = None,
            cancelled: Optional[Callable[[], bool]] = None,
            status: Optional[Callable[[str], None]] = None,
    ) -> str:
        selected = [section for section in self.SECTIONS if section in set(selected)]
        if not selected:
            raise ProfileExportError("No export sections selected")

        workdir = self.get_workdir()
        destination = os.path.abspath(destination)
        parent = os.path.dirname(destination) or os.getcwd()
        os.makedirs(parent, exist_ok=True)

        part_path = destination + ".part"
        db_snapshot = None
        if os.path.exists(part_path):
            os.remove(part_path)

        # Resolve the export payload before creating the temporary ZIP. This
        # prevents a destination placed inside the active profile workdir from
        # being picked up by the Files section (including an existing export
        # with the same name or the growing .part file itself).
        excluded = {destination, part_path}
        section_paths = {
            section: self._section_paths(workdir, section, excluded=excluded)
            for section in self.SECTIONS
        }
        sizes = {}
        for section, paths in section_paths.items():
            self._check_cancel(cancelled)
            sizes[section] = sum(
                self._path_size(path, cancelled, excluded=excluded)
                for path, _relative in paths
            )
        self.ensure_space(parent, self.estimate_export_required(sizes, selected))

        meta = {
            "app_version": str(app_version),
            "exported": selected,
            "exported_at": exported_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        }

        try:
            self._emit_status(status, "profile.export.status.preparing")
            with zipfile.ZipFile(
                    part_path,
                    mode="w",
                    compression=zipfile.ZIP_DEFLATED,
                    allowZip64=True,
            ) as archive:
                archive.writestr(
                    self.META_FILE,
                    json.dumps(meta, indent=4, ensure_ascii=False).encode("utf-8"),
                )

                for section in selected:
                    self._check_cancel(cancelled)
                    self._emit_status(status, f"profile.export.status.{section}")
                    prefix = self.ARCHIVE_PREFIX[section]

                    if section == self.SECTION_DATABASE:
                        source_db = os.path.join(workdir, "db.sqlite")
                        if not os.path.isfile(source_db):
                            raise ProfileExportError("Database file not found")
                        fd, db_snapshot = tempfile.mkstemp(
                            prefix=".pygpt-export-db-",
                            suffix=".sqlite",
                            dir=parent,
                        )
                        os.close(fd)
                        self._snapshot_database(source_db, db_snapshot, cancelled)
                        self._write_file(
                            archive,
                            db_snapshot,
                            f"{prefix}/db.sqlite",
                            cancelled,
                        )
                        os.remove(db_snapshot)
                        db_snapshot = None
                        continue

                    for source, relative in section_paths.get(section, []):
                        self._check_cancel(cancelled)
                        if os.path.isdir(source):
                            self._write_directory(
                                archive,
                                source,
                                f"{prefix}/{relative}",
                                cancelled,
                                excluded=excluded,
                            )
                        elif os.path.isfile(source):
                            self._write_file(
                                archive,
                                source,
                                f"{prefix}/{relative}",
                                cancelled,
                            )

            self._check_cancel(cancelled)
            self._emit_status(status, "profile.export.status.finalizing")
            os.replace(part_path, destination)
            return destination

        except Exception:
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    pass
            raise
        finally:
            if db_snapshot and os.path.exists(db_snapshot):
                try:
                    os.remove(db_snapshot)
                except OSError:
                    pass

    def _snapshot_database(
            self,
            source: str,
            destination: str,
            cancelled: Optional[Callable[[], bool]] = None,
    ):
        source_conn = sqlite3.connect(source, timeout=30)
        destination_conn = sqlite3.connect(destination, timeout=30)
        try:
            def progress(_status, _remaining, _total):
                self._check_cancel(cancelled)

            source_conn.backup(destination_conn, pages=256, progress=progress, sleep=0.01)
        finally:
            destination_conn.close()
            source_conn.close()

    def _write_directory(
            self,
            archive: zipfile.ZipFile,
            directory: str,
            archive_root: str,
            cancelled: Optional[Callable[[], bool]] = None,
            excluded: Optional[Iterable[str]] = None,
    ):
        excluded_paths = self._normalized_paths(excluded)
        wrote_any = False
        for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
            self._check_cancel(cancelled)
            dirnames[:] = [
                name for name in dirnames
                if not os.path.islink(os.path.join(dirpath, name))
                and not self._path_is_excluded(
                    os.path.join(dirpath, name), excluded_paths
                )
            ]
            rel_dir = os.path.relpath(dirpath, directory)
            arc_dir = archive_root if rel_dir == "." else \
                f"{archive_root}/{rel_dir.replace(os.sep, '/')}"

            if not filenames and not dirnames:
                archive.writestr(arc_dir.rstrip("/") + "/", b"")
                wrote_any = True

            for filename in filenames:
                self._check_cancel(cancelled)
                source = os.path.join(dirpath, filename)
                if (
                        os.path.islink(source)
                        or not os.path.isfile(source)
                        or self._path_is_excluded(source, excluded_paths)
                ):
                    continue
                arcname = f"{arc_dir.rstrip('/')}/{filename}"
                self._write_file(archive, source, arcname, cancelled)
                wrote_any = True

        if not wrote_any:
            archive.writestr(archive_root.rstrip("/") + "/", b"")

    def _write_file(
            self,
            archive: zipfile.ZipFile,
            source: str,
            arcname: str,
            cancelled: Optional[Callable[[], bool]] = None,
    ):
        self._check_cancel(cancelled)
        info = zipfile.ZipInfo.from_file(source, arcname.replace("\\", "/"))
        info.compress_type = zipfile.ZIP_DEFLATED
        with open(source, "rb") as src, archive.open(info, "w", force_zip64=True) as dst:
            while True:
                self._check_cancel(cancelled)
                chunk = src.read(self.COPY_CHUNK)
                if not chunk:
                    break
                dst.write(chunk)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_profile(
            self,
            zip_path: str,
            target_dir: str,
            selected: Iterable[str],
            cancelled: Optional[Callable[[], bool]] = None,
            status: Optional[Callable[[str], None]] = None,
            commit_started: Optional[Callable[[], None]] = None,
    ) -> str:
        meta = self.read_meta(zip_path)
        available = set(meta["exported"])
        selected = [
            section for section in self.SECTIONS
            if section in set(selected) and section in available
        ]

        target_dir = os.path.abspath(os.path.expanduser(target_dir))
        if os.path.islink(target_dir):
            raise ProfileExportError("Import target cannot be a symbolic link")
        valid_target, _reason = self.validate_target_directory(target_dir)
        if not valid_target:
            raise ProfileExportError("Unsafe import target directory")

        parent = os.path.dirname(target_dir.rstrip(os.sep)) or os.path.dirname(target_dir)
        if not parent:
            parent = os.getcwd()
        os.makedirs(parent, exist_ok=True)

        required = self.estimate_import_required(zip_path, selected)
        self.ensure_space(parent, required)

        staging = tempfile.mkdtemp(prefix=".pygpt-import-", dir=parent)
        backup = None
        committed = False

        try:
            self._emit_status(status, "profile.import.status.preparing")
            with zipfile.ZipFile(zip_path, "r") as archive:
                members_by_section = {section: [] for section in self.SECTIONS}
                for info in archive.infolist():
                    if info.filename == self.META_FILE:
                        continue
                    self._validate_member(info)
                    normalized = info.filename.replace("\\", "/")
                    for section, prefix in self.ARCHIVE_PREFIX.items():
                        if normalized == prefix or normalized.startswith(prefix + "/"):
                            members_by_section[section].append(info)
                            break

                for section in selected:
                    self._check_cancel(cancelled)
                    self._emit_status(status, f"profile.import.status.{section}")
                    prefix = self.ARCHIVE_PREFIX[section]
                    for info in members_by_section.get(section, []):
                        self._check_cancel(cancelled)
                        normalized = info.filename.replace("\\", "/")
                        relative = normalized[len(prefix):].lstrip("/")
                        if not relative:
                            continue
                        self._extract_member(archive, info, staging, relative, cancelled)

            self._check_cancel(cancelled)
            self._emit_status(status, "profile.import.status.defaults")
            self._prepare_defaults(staging)
            self._check_cancel(cancelled)

            self._emit_status(status, "profile.import.status.finalizing")
            if callable(commit_started):
                commit_started()

            if os.path.lexists(target_dir):
                backup = os.path.join(
                    parent,
                    f".{os.path.basename(target_dir.rstrip(os.sep))}.pygpt-backup-{uuid4().hex}",
                )
                os.replace(target_dir, backup)

            os.replace(staging, target_dir)
            committed = True
            staging = None

            if backup and os.path.exists(backup):
                # The imported directory is already committed. Backup cleanup
                # is best-effort and must not turn a successful import into a
                # destructive rollback merely because cleanup failed.
                shutil.rmtree(backup, ignore_errors=True)
                backup = None

            return target_dir

        except Exception:
            # If the destination had already been moved aside, always restore
            # it, even when the failure happened between the two os.replace()
            # calls and the new staging directory was never committed.
            if backup and os.path.exists(backup):
                try:
                    if os.path.lexists(target_dir):
                        if os.path.isdir(target_dir) and not os.path.islink(target_dir):
                            shutil.rmtree(target_dir)
                        else:
                            os.remove(target_dir)
                    os.replace(backup, target_dir)
                    backup = None
                except OSError:
                    pass
            raise
        finally:
            if staging and os.path.exists(staging):
                shutil.rmtree(staging, ignore_errors=True)
            if backup and os.path.exists(backup) and committed:
                shutil.rmtree(backup, ignore_errors=True)

    def _extract_member(
            self,
            archive: zipfile.ZipFile,
            info: zipfile.ZipInfo,
            root: str,
            relative: str,
            cancelled: Optional[Callable[[], bool]] = None,
    ):
        parts = [part for part in relative.replace("\\", "/").split("/") if part]
        if not parts or any(part in (".", "..") for part in parts):
            raise InvalidProfileArchive("Unsafe archive path")
        destination = os.path.abspath(os.path.join(root, *parts))
        root_abs = os.path.abspath(root)
        if os.path.commonpath([root_abs, destination]) != root_abs:
            raise InvalidProfileArchive("Unsafe archive path")

        if info.is_dir():
            os.makedirs(destination, exist_ok=True)
            return

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with archive.open(info, "r") as src, open(destination, "wb") as dst:
            while True:
                self._check_cancel(cancelled)
                chunk = src.read(self.COPY_CHUNK)
                if not chunk:
                    break
                dst.write(chunk)

    def _prepare_defaults(self, root: str):
        """Create startup-compatible defaults for sections omitted from import."""
        os.makedirs(root, exist_ok=True)

        # Database: create the same bootstrap config table Database.install()
        # expects. Normal profile switching then applies all current migrations.
        db_path = os.path.join(root, "db.sqlite")
        if not os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        config_key TEXT PRIMARY KEY,
                        config_value TEXT,
                        created_ts INTEGER,
                        updated_ts INTEGER
                    );
                """)
                conn.commit()
            finally:
                conn.close()

        app_path = self.window.core.config.get_app_path()
        base_config = os.path.join(app_path, "data", "config")
        for filename in ("config.json", "models.json"):
            src = os.path.join(base_config, filename)
            dst = os.path.join(root, filename)
            if not os.path.exists(dst) and os.path.isfile(src):
                shutil.copy2(src, dst)

        presets_src = os.path.join(base_config, "presets")
        presets_dir = self.window.core.config.dirs.get("presets", "presets")
        presets_dst = os.path.join(root, presets_dir)
        if os.path.isdir(presets_src):
            if not os.path.exists(presets_dst):
                shutil.copytree(presets_src, presets_dst)
            else:
                # Match the normal preset provider install path: when an
                # imported preset directory exists but lacks a current bundled
                # preset, add only the missing defaults and keep user files.
                for filename in os.listdir(presets_src):
                    src = os.path.join(presets_src, filename)
                    dst = os.path.join(presets_dst, filename)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)

        # Fresh profiles also receive a default base index on startup. Create
        # the same minimal indexes.json here so a profile is complete even if
        # the user chooses not to switch to it immediately after import.
        indexes_path = os.path.join(root, "indexes.json")
        if not os.path.exists(indexes_path):
            meta = self.window.core.config.append_meta()
            data = {
                "__meta__": meta,
                "items": {
                    "store": {
                        "SimpleVectorStore": {
                            "base": {
                                "id": "base",
                                "name": "base",
                                "store": None,
                                "items": {},
                            },
                        },
                    },
                },
            }
            with open(indexes_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=4)

        # Directories created by Installer.install() for a fresh workdir.
        # Other runtime directories (indexes/history/video/etc.) are created
        # lazily by their owning components exactly as on normal startup.
        for name in ("tmp", "data", "upload", "img", "capture"):
            relative = self.window.core.config.dirs.get(name, name)
            os.makedirs(os.path.join(root, relative), exist_ok=True)

    # ------------------------------------------------------------------
    # Safety helpers
    # ------------------------------------------------------------------

    def validate_target_directory(self, target_dir: str) -> Tuple[bool, Optional[str]]:
        """Reject locations overlapping PyGPT's registry or existing profiles."""
        try:
            target = os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(target_dir))))
        except OSError:
            return False, "invalid"
        if not target:
            return False, "invalid"

        path_obj = Path(target)
        if path_obj.parent == path_obj:
            return False, "root"
        home = os.path.normcase(os.path.realpath(str(Path.home())))
        if target == home:
            return False, "home"

        protected = [self.window.core.config.get_base_workdir()]
        profiles = self.window.core.config.profile.get_all()
        for profile in profiles.values():
            raw = str(profile.get("workdir") or "").replace("%HOME%", str(Path.home()))
            if raw:
                protected.append(os.path.expanduser(raw))

        for item in protected:
            try:
                protected_path = os.path.normcase(os.path.realpath(os.path.abspath(item)))
                common = os.path.commonpath([target, protected_path])
            except (OSError, ValueError):
                continue
            if common == target or common == protected_path:
                return False, "profile"
        return True, None

    @staticmethod
    def _validate_member(info: zipfile.ZipInfo):
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or name.startswith("../") or "/../" in name:
            raise InvalidProfileArchive("Unsafe archive path")
        parts = [part for part in name.split("/") if part]
        if any(part in (".", "..") for part in parts):
            raise InvalidProfileArchive("Unsafe archive path")

        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise InvalidProfileArchive("Symbolic links are not supported")

    @staticmethod
    def _normalized_paths(paths: Optional[Iterable[str]] = None) -> set:
        return {
            os.path.normcase(os.path.realpath(os.path.abspath(path)))
            for path in (paths or [])
            if path
        }

    @staticmethod
    def _path_is_excluded(path: str, excluded_paths: set) -> bool:
        if not excluded_paths:
            return False
        try:
            normalized = os.path.normcase(os.path.realpath(os.path.abspath(path)))
        except OSError:
            return False
        return normalized in excluded_paths

    @staticmethod
    def _check_cancel(cancelled: Optional[Callable[[], bool]] = None):
        if callable(cancelled) and cancelled():
            raise ProfileExportCancelled("Cancelled")

    @staticmethod
    def _emit_status(callback: Optional[Callable[[str], None]], key: str):
        if callable(callback):
            callback(key)
