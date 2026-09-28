"""Background search retaining matches, their ancestors and matched subtrees."""
import fnmatch
import os
import threading
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer
from pygpt_net.utils import trans


def matches_path(path, root, pattern):
    pattern = pattern.casefold()
    candidate = os.path.relpath(path, root).replace(os.sep, '/') if '/' in pattern else os.path.basename(path)
    candidate = candidate.casefold()
    return fnmatch.fnmatchcase(candidate, pattern) if any(c in pattern for c in '*?[') else pattern in candidate


def find_paths(root, pattern, cancelled=None):
    root = os.path.abspath(root)
    accepted = {root}
    directories = {root}
    # Visibility and automatic expansion are separate: expose a matched
    # directory's entire subtree, but expand only paths leading to matches.
    exposed = set()
    for parent, dirs, files in os.walk(root, followlinks=False):
        if cancelled is not None and cancelled.is_set():
            return None
        if parent in exposed:
            accepted.update(os.path.join(parent, name) for name in dirs + files)
            exposed.update(os.path.join(parent, name) for name in dirs)
        for name in dirs + files:
            path = os.path.join(parent, name)
            if not matches_path(path, root, pattern):
                continue
            accepted.add(path)
            if name in dirs:
                directories.add(path)
                exposed.add(path)
                # Include immediate entries even for symlinks, which os.walk
                # deliberately does not follow.
                try:
                    with os.scandir(path) as children:
                        accepted.update(os.path.join(path, child.name) for child in children)
                except OSError:
                    pass
            ancestor = parent
            while ancestor not in directories:
                accepted.add(ancestor)
                directories.add(ancestor)
                ancestor = os.path.dirname(ancestor)
    return accepted, directories


class SearchSignals(QObject):
    finished = Signal(int, object)


class SearchTask(QRunnable):
    def __init__(self, root, pattern, generation, signals, cancelled):
        super().__init__()
        self.root, self.pattern = root, pattern
        self.generation, self.signals, self.cancelled = generation, signals, cancelled

    def run(self):
        result = find_paths(self.root, self.pattern, self.cancelled)
        if not self.cancelled.is_set():
            self.signals.finished.emit(self.generation, result)


class TreeSearch(QObject):
    def __init__(self, explorer):
        super().__init__(explorer)
        self.explorer = explorer
        self.generation = 0
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
        explorer.search.textChanged.connect(self.changed)
        explorer.model.directoryLoaded.connect(lambda *_: self.apply_timer.start(0))
        explorer.model.rowsInserted.connect(self.files_changed)
        explorer.model.rowsRemoved.connect(self.files_changed)
        explorer.model.fileRenamed.connect(self.files_changed)
        explorer.model.layoutChanged.connect(lambda *_: self.apply_timer.start(0))
        # Stop any outstanding scan when the explorer is destroyed.
        explorer.destroyed.connect(lambda *_: self.cancelled.set())

    def files_changed(self, *_):
        self.apply_timer.start(0)
        if self.explorer.search.text().strip():
            self.changed()

    def changed(self, *_):
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
        self.accepted, self.directories = result
        root = self.explorer.directory
        pattern = self.explorer.search.text().strip()
        count = sum(matches_path(path, root, pattern) for path in self.accepted if path != root)
        self.explorer.search_status.setText(str(count) if count else trans('files.search.empty'))
        self.apply()

    def apply(self):
        if self.pending:
            return
        model = self.explorer.model
        tree = self.explorer.treeView
        root = model.index(self.explorer.directory)

        def visit(parent):
            for row in range(model.rowCount(parent)):
                index = model.index(row, 0, parent)
                path = model.filePath(index)
                visible = self.accepted is None or path in self.accepted
                tree.setRowHidden(row, parent, not visible)
                if model.isDir(index) and visible:
                    depth = len(os.path.relpath(path, self.explorer.directory).split(os.sep))
                    within_depth = self.expansion_depth is None or depth <= self.expansion_depth
                    if (self.expand_all_requested or (self.auto_expand and within_depth and self.accepted is not None and path in self.directories)) and not os.path.islink(path):
                        if model.canFetchMore(index):
                            model.fetchMore(index)
                        tree.expand(index)
                    # Do not collapse manually opened descendants when lazy
                    # loading or a filesystem notification reapplies the filter.
                    visit(index)
        updates_enabled = tree.updatesEnabled()
        tree.setUpdatesEnabled(False)
        try:
            if self.collapse_on_apply:
                tree.collapseAll()
                self.collapse_on_apply = False
            if root.isValid():
                visit(root)
        finally:
            tree.setUpdatesEnabled(updates_enabled)
