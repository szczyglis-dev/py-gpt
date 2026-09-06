import sys
import typing
from types import SimpleNamespace

import pygpt_net.core.typing_compat as mod


def test_current_python_native_self_is_left_untouched(monkeypatch):
    before = getattr(typing, "Self", None)
    monkeypatch.setattr(mod.sys, "version_info", (3, 11, 0))
    mod.ensure_typing_self_compat()
    assert getattr(typing, "Self", None) is before


def test_python_310_installs_runtime_safe_self_and_handles_missing_extensions(monkeypatch):
    # Register the current attribute state with monkeypatch so the compatibility
    # shim cannot leak a replacement typing.Self into subsequent tests.
    monkeypatch.setattr(typing, "Self", getattr(typing, "Self", None), raising=False)
    monkeypatch.setattr(mod.sys, "version_info", (3, 10, 0))
    real_import = __import__
    def fake_import(name, *args, **kwargs):
        if name == "typing_extensions":
            raise ImportError
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr("builtins.__import__", fake_import)
    mod.ensure_typing_self_compat()
    assert typing.Self is mod._PYGPT_SELF_TYPE
    typing.Optional[typing.Self]
