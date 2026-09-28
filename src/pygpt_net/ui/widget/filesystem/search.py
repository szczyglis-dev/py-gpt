"""Background search retaining matches, their ancestors and matched subtrees."""
import fnmatch
import os
import threading
import time
import re
from collections import deque
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer, QPersistentModelIndex, QModelIndex
from pygpt_net.utils import trans


def matches_path(path, root, pattern):
    pattern = pattern.casefold()
    candidate = os.path.relpath(path, root).replace(os.sep, '/') if '/' in pattern else os.path.basename(path)
    candidate = candidate.casefold()
    return fnmatch.fnmatchcase(candidate, pattern) if any(c in pattern for c in '*?[') else pattern in candidate


def find_paths(root, pattern, cancelled=None, include_count=False):
    root = os.path.abspath(root)
    pattern = pattern.casefold()
    relative = '/' in pattern
    wildcard = re.compile(fnmatch.translate(pattern)).match if any(c in pattern for c in '*?[') else None

    def matches(candidate):
        candidate = candidate.casefold()
        return bool(wildcard(candidate)) if wildcard else pattern in candidate

    accepted = {root}
    directories = {root}
    exposed = set()
    count = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        if cancelled is not None and cancelled.is_set():
            return None
        prefix = os.path.relpath(parent, root).replace(os.sep, '/') if relative else ''
        prefix = prefix + '/' if prefix and prefix != '.' else ''
        expose = parent in exposed
        dir_names = set(dirs)
        for name in dirs + files:
            if cancelled is not None and cancelled.is_set():
                return None
            path = os.path.join(parent, name)
            is_dir = name in dir_names
            if expose:
                accepted.add(path)
                if is_dir:
                    exposed.add(path)
            if not matches(prefix + name):
                continue
            count += 1
            accepted.add(path)
            if is_dir:
                directories.add(path)
                exposed.add(path)
                # Normal directories are read once by os.walk. Only matched
                # symlinks need a separate immediate listing (never recurse).
                if os.path.islink(path):
                    try:
                        with os.scandir(path) as children:
                            for child in children:
                                if cancelled is not None and cancelled.is_set():
                                    return None
                                accepted.add(child.path)
                                count += bool(matches(prefix + name + '/' + child.name if relative else child.name))
                    except OSError:
                        pass
            ancestor = parent
            while ancestor not in directories:
                accepted.add(ancestor)
                directories.add(ancestor)
                ancestor = os.path.dirname(ancestor)
    return (accepted, directories, count) if include_count else (accepted, directories)


class SearchSignals(QObject):
    finished = Signal(int, object)


class SearchTask(QRunnable):
    def __init__(self, root, pattern, generation, signals, cancelled):
        super().__init__()
        self.root, self.pattern = root, pattern
        self.generation, self.signals, self.cancelled = generation, signals, cancelled

    def run(self):
        result = find_paths(self.root, self.pattern, self.cancelled, include_count=True)
        if not self.cancelled.is_set():
            self.signals.finished.emit(self.generation, result)


class TreeSearch(QObject):
    def __init__(self, explorer):
        super().__init__(explorer)
        self.explorer = explorer
        self.generation = 0
        self.loaded_directories = set()
        self._apply_queue = deque()
        self._applying = False
        self._reapply = False
        self.previous_pattern = ""
        self.pending = False
        self.collapse_on_apply = False
        self.auto_expand = True
        self.expansion_depth = None
        self.expand_all_requested = False
        self.accepted = None
        self.directories = set()
        self.cancelled = threading.Event()
        self.signals = SearchSignals()
        self.signals.finished.connect(self.finished)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(220)
        self.timer.timeout.connect(self.start)
        self.apply_timer = QTimer(self)
        self.apply_timer.setSingleShot(True)
        self.apply_timer.timeout.connect(self.apply)
        self.batch_timer = QTimer(self)
        self.batch_timer.setSingleShot(True)
        self.batch_timer.timeout.connect(self.apply_batch)
        explorer.search.textChanged.connect(self.changed)
        explorer.model.directoryLoaded.connect(self.directory_loaded)
        explorer.model.rowsInserted.connect(self.rows_inserted)
        explorer.model.rowsRemoved.connect(self.files_changed)
        explorer.model.fileRenamed.connect(self.files_changed)
        explorer.model.layoutChanged.connect(lambda *_: self.apply_timer.start(0))
        explorer.model.modelReset.connect(self.model_reset)
        # Stop any outstanding scan when the explorer is destroyed.
        explorer.destroyed.connect(lambda *_: self.cancelled.set())

    def directory_loaded(self, path):
        self.loaded_directories.add(path)
        self.apply_timer.start(0)

    def rows_inserted(self, parent, *_):
        # QFileSystemModel emits rowsInserted while lazily populating folders.
        # Those rows were already scanned; restarting here causes scan loops.
        if self.explorer.model.filePath(parent) in self.loaded_directories:
            self.files_changed()
        else:
            self.apply_timer.start(0)

    def model_reset(self):
        self.loaded_directories.clear()
        self.stop_applying()

    def stop_applying(self):
        self.batch_timer.stop()
        self._apply_queue.clear()
        self._applying = False
        self._reapply = False

    def files_changed(self, *_):
        self.apply_timer.start(0)
        if self.explorer.search.text().strip():
            self.changed()

    def changed(self, *_):
        self.stop_applying()
        self.pending = True
        self.cancelled.set()
        self.generation += 1
        pattern = self.explorer.search.text().strip()
        if pattern != self.previous_pattern:
            removed = len(self.previous_pattern) - len(pattern)
            self.expand_all_requested = False
            if removed > 0:
                depth = self.expansion_depth
                if depth is None:
                    root = self.explorer.directory
                    depth = max((len(os.path.relpath(path, root).split(os.sep))
                                 for path in self.directories if path != root), default=0)
                self.expansion_depth = max(0, depth - removed) if pattern else 0
                self.auto_expand = self.expansion_depth > 0
                self.collapse_on_apply = True
            else:
                self.expansion_depth = None
                self.auto_expand = True
            self.previous_pattern = pattern
        if not pattern:
            self.timer.stop()
            self.start()
        else:
            self.timer.start()

    def collapse_all(self):
        self.auto_expand = False
        self.expand_all_requested = False
        self.explorer.treeView.collapseAll()

    def expand_all(self):
        self.expand_all_requested = True
        self.apply()

    def start(self):
        self.stop_applying()
        pattern = self.explorer.search.text().strip()
        self.cancelled.set()
        self.generation += 1
        self.cancelled = threading.Event()
        if not pattern:
            self.pending = False
            self.accepted = None
            self.directories = set()
            self.apply()
            self.explorer.search_status.clear()
            return
        self.pending = True
        self.explorer.search_status.setText(self.explorer.searching_text)
        QThreadPool.globalInstance().start(SearchTask(
            self.explorer.directory, pattern, self.generation, self.signals, self.cancelled))

    def finished(self, generation, result):
        if generation != self.generation or result is None:
            return
        self.pending = False
        self.accepted, self.directories, count = result
        self.explorer.search_status.setText(str(count) if count else trans('files.search.empty'))
        self.apply()

    def apply(self):
        if self.pending:
            return
        if self._applying:
            self._reapply = True
            return
        tree = self.explorer.treeView
        root = self.explorer.model.index(self.explorer.directory)
        if self.collapse_on_apply:
            tree.collapseAll()
            self.collapse_on_apply = False
        if root.isValid():
            self._apply_queue.append((QPersistentModelIndex(root), 0, 1))
            self._applying = True
            self.apply_batch()

    def apply_batch(self):
        """Yield to typing/painting between short portions of tree filtering."""
        if self.pending:
            self.stop_applying()
            return
        model = self.explorer.model
        tree = self.explorer.treeView
        deadline = time.monotonic() + 0.006
        processed = 0
        updates_enabled = tree.updatesEnabled()
        tree.setUpdatesEnabled(False)
        try:
            while self._apply_queue:
                persistent, row, depth = self._apply_queue.popleft()
                parent = QModelIndex(persistent)
                if not parent.isValid():
                    continue
                while row < model.rowCount(parent):
                    index = model.index(row, 0, parent)
                    path = model.filePath(index)
                    visible = self.accepted is None or path in self.accepted
                    if tree.isRowHidden(row, parent) == visible:
                        tree.setRowHidden(row, parent, not visible)
                    if model.isDir(index) and visible:
                        within_depth = self.expansion_depth is None or depth <= self.expansion_depth
                        expand = self.expand_all_requested or (self.auto_expand and within_depth
                            and self.accepted is not None and path in self.directories)
                        if expand and not model.fileInfo(index).isSymLink():
                            if model.canFetchMore(index):
                                model.fetchMore(index)
                            if not tree.isExpanded(index):
                                tree.expand(index)
                        if model.rowCount(index):
                            self._apply_queue.append((QPersistentModelIndex(index), 0, depth + 1))
                    row += 1
                    processed += 1
                    if processed >= 200 or time.monotonic() >= deadline:
                        self._apply_queue.appendleft((persistent, row, depth))
                        self.batch_timer.start(1)
                        return
        finally:
            tree.setUpdatesEnabled(updates_enabled)
        self._applying = False
        if self._reapply:
            self._reapply = False
            self.apply_timer.start(0)
