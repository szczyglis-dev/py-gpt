#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import builtins
import importlib.util
import multiprocessing
from pathlib import Path
from unittest.mock import MagicMock

import pytest


PRELOAD_PATH = Path(__file__).resolve().parents[1] / "src" / "pygpt_net" / "preload.py"


def _load_preload_module():
    spec = importlib.util.spec_from_file_location("pygpt_net._test_preload", PRELOAD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def preload_module():
    return _load_preload_module()


def test_preloader_set_message_sends_string_and_swallows_errors(preload_module):
    conn = MagicMock()
    preloader = preload_module._Preloader(proc=None, conn=conn)
    preloader.set_message(123)
    conn.send.assert_called_once_with({"type": "msg", "text": "123"})

    conn.reset_mock()
    conn.send.side_effect = OSError("closed")
    preloader.set_message("hello")
    conn.send.assert_called_once()


def test_preloader_close_waits_terminates_and_clears_handles(preload_module):
    conn = MagicMock()
    proc = MagicMock()
    proc.is_alive.return_value = True
    preloader = preload_module._Preloader(proc=proc, conn=conn)

    preloader.close(wait=True, timeout=0.25)

    conn.send.assert_called_once_with({"type": "quit"})
    proc.join.assert_called_once_with(timeout=0.25)
    proc.terminate.assert_called_once_with()
    assert preloader._conn is None
    assert preloader._proc is None


def test_preloader_close_without_wait_is_non_blocking(preload_module):
    conn = MagicMock()
    conn.send.side_effect = OSError("closed")
    proc = MagicMock()
    proc.is_alive.return_value = False
    preloader = preload_module._Preloader(proc=proc, conn=conn)

    preloader.close(wait=False)

    proc.join.assert_not_called()
    proc.terminate.assert_not_called()
    assert preloader._conn is None
    assert preloader._proc is None


def test_start_preloader_uses_spawn_context(preload_module, monkeypatch):
    parent_conn = MagicMock()
    child_conn = MagicMock()
    proc = MagicMock()
    ctx = MagicMock()
    ctx.Pipe.return_value = (parent_conn, child_conn)
    ctx.Process.return_value = proc
    get_context = MagicMock(return_value=ctx)
    monkeypatch.setattr(multiprocessing, "get_context", get_context)

    result = preload_module._start_preloader(title="Title", message="Message")

    get_context.assert_called_once_with("spawn")
    ctx.Pipe.assert_called_once_with(duplex=True)
    ctx.Process.assert_called_once_with(
        target=preload_module._splash_main,
        args=(child_conn, "Title", "Message"),
        daemon=True,
    )
    proc.start.assert_called_once_with()
    child_conn.close.assert_called_once_with()
    assert result._proc is proc
    assert result._conn is parent_conn


def test_start_preloader_falls_back_and_handles_setup_failure(preload_module, monkeypatch):
    parent_conn = MagicMock()
    child_conn = MagicMock()
    proc = MagicMock()
    monkeypatch.setattr(multiprocessing, "get_context", MagicMock(side_effect=ValueError("no spawn")))
    monkeypatch.setattr(multiprocessing, "Pipe", MagicMock(return_value=(parent_conn, child_conn)))
    monkeypatch.setattr(multiprocessing, "Process", MagicMock(return_value=proc))

    assert preload_module._start_preloader() is not None
    proc.start.assert_called_once_with()

    monkeypatch.setattr(multiprocessing, "Pipe", MagicMock(side_effect=OSError("pipe failed")))
    assert preload_module._start_preloader() is None


def test_splash_main_returns_cleanly_when_qt_import_fails(preload_module, monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PySide6":
            raise ImportError("no Qt")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert preload_module._splash_main(MagicMock()) is None
