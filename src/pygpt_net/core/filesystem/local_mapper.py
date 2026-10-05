"""Immutable path mapping snapshot suitable for filesystem worker threads."""
import os
from dataclasses import dataclass


def normalized_root(path):
    return os.path.normcase(os.path.abspath(path))


@dataclass(frozen=True, slots=True)
class LocalPathMapper:
    base: str
    data: str
    shared: str
    global_roots: tuple[str, ...]
    placeholder: str = '%workdir%'

    @staticmethod
    def _contains(path, root):
        return path == root or path.startswith(root.rstrip(os.sep) + os.sep)

    def __call__(self, path):
        if not path:
            return path
        native = os.path.normpath(path)
        absolute = normalized_root(native)
        if self.data != self.shared and any(self._contains(absolute, root)
                                           for root in (*self.global_roots, self.shared)):
            if self._contains(absolute, self.shared):
                return path
            rel = os.path.relpath(native, self.base)
            return self.placeholder if rel == '.' else os.path.join(self.placeholder, rel)
        if self._contains(absolute, self.data):
            rel = os.path.relpath(native, self.data)
            prefix = os.path.join(self.placeholder, 'data')
            return prefix if rel == '.' else os.path.join(prefix, rel)
        if self._contains(absolute, self.base):
            rel = os.path.relpath(native, self.base)
            return self.placeholder if rel == '.' else os.path.join(self.placeholder, rel)
        return path
