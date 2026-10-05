#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 17:30:00
# ================================================== #

import os
import platform
import shutil
import sys

from PySide6 import QtCore, __version__ as pyside_version
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.core.qt import safe_emit
from pygpt_net.ui.widget.dialog.info import InfoDialog
from pygpt_net.utils import trans


class WorkdirSizeSignals(QObject):
    result = Signal(str, object)


class WorkdirSizeWorker(QRunnable):
    def __init__(self, path: str, sandbox_path: str, packages_path: str):
        super().__init__()
        self.path = path
        self.sandbox_path = sandbox_path
        self.packages_path = packages_path
        self.signals = WorkdirSizeSignals()

    @staticmethod
    def _tree_size(root: str, prune_top_level=(), exclude_paths=()) -> int:
        total = 0
        root = os.path.abspath(root)
        excluded = {os.path.realpath(path) for path in exclude_paths}
        if os.path.realpath(root) in excluded:
            return 0
        if not os.path.isdir(root):
            return 0
        for dirpath, dirnames, filenames in os.walk(root):
            abs_dir = os.path.abspath(dirpath)
            dirnames[:] = [name for name in dirnames
                           if os.path.realpath(os.path.join(dirpath, name)) not in excluded]
            if abs_dir == root and prune_top_level:
                blocked = set(prune_top_level)
                dirnames[:] = [name for name in dirnames if name not in blocked]
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    if os.path.islink(path):
                        continue
                    total += os.path.getsize(path)
                except OSError:
                    # Runtime/cache files may disappear while being scanned.
                    continue
        return total

    @Slot()
    def run(self):
        sizes = []
        for index, (path, excluded) in enumerate((
            (self.path, ("sandbox", "extra_packages", "addons")),
            (self.sandbox_path, ()),
            (self.packages_path, ()),
        )):
            try:
                sizes.append(self._tree_size(
                    path, prune_top_level=excluded,
                    exclude_paths=(self.sandbox_path, self.packages_path) if index == 0 else ()))
            except OSError:
                sizes.append(None)
        safe_emit(self.signals, "result", self.path, tuple(sizes))


class SystemInfo(QObject):
    FIELDS = (
        ("app_version", "dialog.system_info.app_version"),
        ("app_type", "dialog.system_info.app_type"),
        ("python", "dialog.system_info.python"),
        ("python_executable", "dialog.system_info.python_executable"),
        ("os", "dialog.system_info.os"),
        ("architecture", "dialog.system_info.architecture"),
        ("cpu", "dialog.system_info.cpu"),
        ("qt", "dialog.system_info.qt"),
        ("ram", "dialog.system_info.ram"),
        ("workdir_size", "dialog.system_info.workdir_size"),
        ("sandbox_size", "dialog.system_info.sandbox_size"),
        ("extra_packages_size", "dialog.system_info.extra_packages_size"),
        ("db_size", "dialog.system_info.db_size"),
        ("disk_free", "dialog.system_info.disk_free"),
        ("workdir", "dialog.system_info.workdir"),
        ("app_path", "dialog.system_info.app_path"),
    )

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.values = {}
        self._workers = {}
        self._value_nodes = {}

    def setup(self):
        """Setup System Info dialog."""
        dialog_id = "system_info"

        content = QWidget()
        form = QFormLayout(content)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setContentsMargins(4, 4, 4, 4)
        form.setSpacing(8)

        for field_id, label_key in self.FIELDS:
            label = QLabel(trans(label_key) + ":")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            value = QLabel("-")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            value.setMinimumWidth(300)

            self._value_nodes[field_id] = value
            self.window.ui.nodes[f"dialog.system_info.{field_id}"] = value
            form.addRow(label, value)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        btn_copy = QPushButton(QIcon(":/icons/copy.svg"), trans("dialog.system_info.copy"))
        btn_copy.clicked.connect(self.copy)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("dialog.system_info.refresh"))
        btn_refresh.clicked.connect(self.prepare)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(btn_copy)
        buttons.addWidget(btn_refresh)

        layout = QVBoxLayout()
        layout.addWidget(scroll)
        layout.addLayout(buttons)

        self.window.ui.dialog["info." + dialog_id] = InfoDialog(self.window, dialog_id)
        self.window.ui.dialog["info." + dialog_id].setLayout(layout)
        self.window.ui.dialog["info." + dialog_id].setWindowTitle(trans("dialog.system_info.title"))

    def prepare(self):
        """Refresh dynamic system information."""
        workdir = self.window.core.config.get_path()
        fs = self.window.core.filesystem

        version = self.window.meta.get("version", "-")
        build = self.window.meta.get("build", "-")
        build_label = trans("dialog.about.build").lower()

        app_type = self.window.core.platforms.get_app_type()
        if app_type == "standalone":
            app_type = "compiled"

        self.values = {
            "app_version": f"{version} ({build_label} {build})",
            "app_type": app_type,
            "python": f"{platform.python_version()} ({platform.python_implementation()})",
            "python_executable": sys.executable or "-",
            "os": self._get_os_string(),
            "architecture": platform.machine() or self.window.core.platforms.get_architecture() or "-",
            "cpu": self._get_cpu_string(),
            "qt": f"PySide {pyside_version} / Qt {QtCore.qVersion()}",
            "ram": self._get_ram_string(fs),
            "workdir_size": trans("dialog.system_info.calculating"),
            "sandbox_size": trans("dialog.system_info.calculating"),
            "extra_packages_size": trans("dialog.system_info.calculating"),
            "db_size": fs.sizeof_fmt(self._get_db_size(workdir)),
            "disk_free": self._get_disk_free(workdir, fs),
            "workdir": workdir or "-",
            "app_path": self.window.core.config.get_app_path() or "-",
        }
        self._render()
        self._start_workdir_size(workdir)

    def copy(self):
        """Copy current system information to clipboard."""
        lines = []
        for field_id, label_key in self.FIELDS:
            lines.append(f"{trans(label_key)}: {self.values.get(field_id, '-')}")
        QGuiApplication.clipboard().setText("\n".join(lines))

    def _render(self):
        for field_id, _ in self.FIELDS:
            node = self._value_nodes.get(field_id)
            if node is not None:
                node.setText(str(self.values.get(field_id, "-")))

    def _start_workdir_size(self, workdir: str):
        if not workdir or not os.path.isdir(workdir):
            for field in ("workdir_size", "sandbox_size", "extra_packages_size"):
                self.values[field] = "-"
            self._render()
            return

        if workdir in self._workers:
            return

        from pygpt_net.core.sandbox.builtin import BuiltinSandboxRuntime
        plugin = self.window.core.plugins.get('filesystem')
        sandbox_path = BuiltinSandboxRuntime(
            self.window, 'python',
            sandbox_path_provider=(lambda: plugin.get_option_value('custom_sandbox_path'))
            if plugin is not None else None,
        ).sandbox_root
        packages_path = os.path.join(self.window.core.config.get_base_workdir(), "extra_packages")
        worker = WorkdirSizeWorker(workdir, sandbox_path, packages_path)
        self._workers[workdir] = worker
        worker.signals.result.connect(self._on_workdir_size)
        QThreadPool.globalInstance().start(worker)

    @Slot(str, object)
    def _on_workdir_size(self, path: str, size):
        self._workers.pop(path, None)

        # Ignore a result from an older scan if the workdir changed meanwhile.
        if path != self.window.core.config.get_path():
            return

        if not isinstance(size, (tuple, list)) or len(size) != 3:
            size = (None, None, None)
        fs = self.window.core.filesystem
        for field, total in zip(("workdir_size", "sandbox_size", "extra_packages_size"), size):
            self.values[field] = fs.sizeof_fmt(total) if total is not None else "-"
        self._render()

    @staticmethod
    def _get_os_string() -> str:
        system = platform.system()
        release = platform.release()

        if system == "Linux":
            try:
                info = platform.freedesktop_os_release()
                name = info.get("PRETTY_NAME") or info.get("NAME")
                if name:
                    return f"{name} / Linux {release}"
            except (AttributeError, OSError):
                pass
        elif system == "Darwin":
            mac_ver = platform.mac_ver()[0]
            if mac_ver:
                return f"macOS {mac_ver}"
        elif system == "Windows":
            win_ver = platform.win32_ver()
            if win_ver and win_ver[0]:
                build = win_ver[1]
                if build:
                    return f"Windows {win_ver[0]} ({build})"
                return f"Windows {win_ver[0]}"

        value = " ".join(part for part in (system, release) if part)
        return value or "-"

    @staticmethod
    def _get_cpu_string() -> str:
        import psutil

        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        if physical and logical:
            return f"{physical} / {logical}"
        if logical:
            return str(logical)
        return str(os.cpu_count() or "-")

    @staticmethod
    def _get_ram_string(fs) -> str:
        import psutil

        try:
            process = psutil.Process(os.getpid())
            used = process.memory_info().rss
            used_with_web = used
            web_processes = 0

            # QtWebEngine runs renderer/GPU/utility work in helper processes.
            # Add only QtWebEngineProcess descendants here; unrelated plugin,
            # sandbox or user subprocesses must not inflate this figure.
            for child in process.children(recursive=True):
                try:
                    name = (child.name() or "").lower()
                    exe = os.path.basename(child.exe() or "").lower()
                    if "qtwebengineprocess" not in name and "qtwebengineprocess" not in exe:
                        continue
                    used_with_web += child.memory_info().rss
                    web_processes += 1
                except (psutil.Error, OSError):
                    continue

            total = psutil.virtual_memory().total
            process_label = "WebProcess" if web_processes == 1 else "WebProcesses"
            return (
                f"{fs.sizeof_fmt(used)} "
                f"({fs.sizeof_fmt(used_with_web)} with {web_processes} {process_label}) / "
                f"{fs.sizeof_fmt(total)}"
            )
        except (psutil.Error, OSError):
            return "-"

    def _get_db_size(self, workdir: str) -> int:
        db_path = getattr(self.window.core.db, "db_path", None)
        if not db_path:
            db_path = os.path.join(workdir, "db.sqlite")

        total = 0
        # Include SQLite WAL/SHM files because they are part of the live DB
        # footprint while the application is running.
        for path in (db_path, db_path + "-wal", db_path + "-shm"):
            try:
                if os.path.isfile(path):
                    total += os.path.getsize(path)
            except OSError:
                continue
        return total

    @staticmethod
    def _get_disk_free(workdir: str, fs) -> str:
        try:
            return fs.sizeof_fmt(shutil.disk_usage(workdir).free)
        except (OSError, FileNotFoundError):
            return "-"
