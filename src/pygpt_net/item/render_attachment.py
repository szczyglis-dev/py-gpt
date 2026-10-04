"""Presentation provenance without changing the runtime path-list API."""


class AttachmentPath(str):
    """A normal string path carrying the origin used only by chat rendering."""

    def __new__(cls, path, type=None):
        if isinstance(path, dict):
            type = type or path.get('type')
            path = path.get('path', '')
        origin = type or getattr(path, 'type', 'output')
        value = super().__new__(cls, path)
        value.type = origin if origin in ('user', 'output') else 'output'
        return value


def attachment_paths(values, type=None):
    """Read legacy strings and typed records; legacy strings default to output."""
    return [AttachmentPath(value, type) for value in (values or [])
            if isinstance(value, (str, dict)) and (not isinstance(value, dict) or value.get('path'))]


def attachment_records(values):
    """Write the two-field presentation records without mutating runtime lists."""
    return [{'path': str(path), 'type': path.type} for path in attachment_paths(values)]


def attachment_type(value):
    return AttachmentPath(value).type
