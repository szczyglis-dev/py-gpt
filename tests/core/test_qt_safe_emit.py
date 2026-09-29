from types import SimpleNamespace

import pytest

from pygpt_net.core.qt import is_deleted_qt_object_error, safe_emit


def test_qt_safe_emit_recognizes_only_deleted_qobject_runtime_errors():
    messages = [
        "Signal source has been deleted",
        "Internal C++ object (X) already deleted",
        "wrapped C/C++ object of type X has been deleted",
        "wrapped C/C++ object already deleted",
    ]
    assert all(is_deleted_qt_object_error(RuntimeError(msg)) for msg in messages)
    assert is_deleted_qt_object_error(RuntimeError("other runtime error")) is False
    assert is_deleted_qt_object_error(ValueError("has been deleted")) is False


def test_qt_safe_emit_returns_false_for_missing_source_or_signal():
    assert safe_emit(None, "response") is False
    assert safe_emit(SimpleNamespace(), "response") is False
    assert safe_emit(SimpleNamespace(response=object()), "response") is False


def test_qt_safe_emit_forwards_arguments_and_returns_true():
    calls = []
    source = SimpleNamespace(response=SimpleNamespace(emit=lambda *args: calls.append(args)))

    assert safe_emit(source, "response", 1, "x") is True
    assert calls == [(1, "x")]


def test_qt_safe_emit_suppresses_deleted_object_race_but_not_other_runtime_errors():
    deleted = SimpleNamespace(response=SimpleNamespace(emit=lambda *args: (_ for _ in ()).throw(RuntimeError("Signal source has been deleted"))))
    broken = SimpleNamespace(response=SimpleNamespace(emit=lambda *args: (_ for _ in ()).throw(RuntimeError("boom"))))

    assert safe_emit(deleted, "response", 1) is False
    with pytest.raises(RuntimeError, match="boom"):
        safe_emit(broken, "response", 1)
