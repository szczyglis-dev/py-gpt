"""Cached, cancellable workdir discovery with no filesystem walk on the UI thread."""
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.core.text.mentions import KIND_FILE_CONTEXT, KIND_CONVERSATION
from .mention import MentionEntry


@dataclass(frozen=True, slots=True)
class ScanSpec:
    root: str
    mapper: object
    excluded_extensions: frozenset[str] = frozenset()
    excluded_paths: frozenset[str] = frozenset()
    limit: int = 5000


class ScanSignals(QObject):
    ready = Signal(object, object, bool)
    error = Signal(object, object)


class WorkdirScan(QRunnable):
    def __init__(self, spec):
        super().__init__()
        self.spec = spec
        self.signals = ScanSignals()
        self.cancelled = Event()

    def cancel(self):
        self.cancelled.set()

    @Slot()
    def run(self):
        spec = self.spec
        entries, seen = [], set()
        pending = [spec.root]
        last_update = time.monotonic()
        while pending and len(entries) < spec.limit:
            if self.cancelled.is_set():
                return
            directory = pending.pop()
            directories, files = [], []
            try:
                with os.scandir(directory) as iterator:
                    for item in iterator:
                        if self.cancelled.is_set():
                            return
                        try:
                            if item.is_symlink():
                                continue
                            if item.is_dir(follow_symlinks=False):
                                directories.append(item.path)
                            elif (os.path.splitext(item.name)[1].lower().lstrip('.') not in spec.excluded_extensions
                                  and item.path not in spec.excluded_paths
                                  and item.is_file(follow_symlinks=False)):
                                files.append(item.path)
                        except OSError:
                            continue
            except OSError:
                continue
            pending.extend(sorted(directories, key=str.casefold, reverse=True))
            for path in sorted(files, key=str.casefold):
                if self.cancelled.is_set():
                    return
                rel = os.path.relpath(path, spec.root).replace(os.sep, '/')
                if any(ch in rel for ch in '\r\n\t'):
                    continue
                value = spec.mapper(path).replace('\\', '/')
                key = value.casefold()
                if key in seen:
                    continue
                seen.add(key)
                entries.append(MentionEntry(KIND_FILE_CONTEXT, rel, value))
                if len(entries) % 250 == 0 and time.monotonic() - last_update >= 0.15:
                    safe_emit(self.signals, 'ready', self, list(entries), False)
                    last_update = time.monotonic()
                if len(entries) >= spec.limit:
                    break
        if not self.cancelled.is_set():
            safe_emit(self.signals, 'ready', self, entries, True)


class WorkdirMentionDiscovery(QObject):
    updated = Signal()
    failed = Signal(object)
    CACHE_SECONDS = 30
    CACHE_ROOTS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = OrderedDict()
        self._worker = None
        self._pool = QThreadPool.globalInstance()

    def entries(self, spec):
        cached = self._cache.get(spec)
        if cached is not None:
            self._cache.move_to_end(spec)
        # Reuse the same in-flight scan, even before its first batch arrives.
        if self._worker is not None and self._worker.spec == spec:
            return list(cached[1]) if cached else []
        if self._worker is not None:
            self._worker.cancel()
            self.destroyed.disconnect(self._worker.cancel)
            self._worker = None
        if cached is not None and time.monotonic() - cached[0] < self.CACHE_SECONDS:
            return list(cached[1])
        worker = self._new_worker(spec)
        self._worker = worker
        worker.signals.ready.connect(self._on_ready, Qt.QueuedConnection)
        worker.signals.error.connect(self._on_error, Qt.QueuedConnection)
        # Cancel without waiting for filesystem I/O when the editor is destroyed.
        self.destroyed.connect(worker.cancel)
        self._pool.start(worker)
        return list(cached[1]) if cached else []

    @Slot(object, object)
    def _on_error(self, worker, error):
        if worker is self._worker:
            self.failed.emit(error)

    def _new_worker(self, spec):
        return WorkdirScan(spec)

    @Slot(object, object, bool)
    def _on_ready(self, worker, entries, complete):
        if worker is not self._worker:
            return  # A project/workdir change made these results obsolete.
        self._cache[worker.spec] = (time.monotonic() if complete else float('-inf'), entries)
        self._cache.move_to_end(worker.spec)
        while len(self._cache) > self.CACHE_ROOTS:
            self._cache.popitem(last=False)
        if complete:
            self._worker = None
            self.destroyed.disconnect(worker.cancel)
        self.updated.emit()


class ConversationTitleScan(QRunnable):
    """Build a Unicode-searchable title index off the UI thread."""

    def __init__(self, db):
        super().__init__()
        self.spec = db
        self.signals = ScanSignals()
        self.cancelled = Event()

    def cancel(self):
        self.cancelled.set()

    @Slot()
    def run(self):
        from pygpt_net.provider.core.ctx.db_sqlite.storage import Storage
        entries = []
        last_update = time.monotonic()
        try:
            for ctx_id, title in Storage.iter_meta_titles(self.spec):
                if self.cancelled.is_set():
                    return
                title = str(title or '').strip()
                if not title or any(ch in title for ch in '\r\n\t'):
                    continue
                entry = MentionEntry(KIND_CONVERSATION, title, str(ctx_id))
                entries.append((entry, title.casefold()))
                if len(entries) % 1000 == 0 and time.monotonic() - last_update >= 0.15:
                    safe_emit(self.signals, 'ready', self, list(entries), False)
                    last_update = time.monotonic()
        except Exception as e:
            safe_emit(self.signals, 'error', self, e)
            # DB shutdown/profile switching must not leave a scan in flight.
            entries = []
        if not self.cancelled.is_set():
            safe_emit(self.signals, 'ready', self, entries, True)


class ConversationTitleDiscovery(WorkdirMentionDiscovery):
    def _new_worker(self, db):
        return ConversationTitleScan(db)
