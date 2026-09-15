#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from pygpt_net.core.context_manager.store import ContextMemoryStore


DDL = """
CREATE TABLE memory_ctx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_id INTEGER NOT NULL UNIQUE,
    updated_at INTEGER NOT NULL DEFAULT 0,
    last_item_id INTEGER NOT NULL DEFAULT 0,
    generation INTEGER NOT NULL DEFAULT 0,
    revision INTEGER NOT NULL DEFAULT 0,
    content TEXT NOT NULL DEFAULT ''
)
"""


def make_store():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(DDL))
    db = SimpleNamespace(init=MagicMock(), get_db=MagicMock(return_value=engine))
    window = SimpleNamespace(core=SimpleNamespace(db=db))
    return ContextMemoryStore(window), engine, db


def test_meta_id_requires_positive_integer():
    for value in (None, "", 0, -1, "bad"):
        with pytest.raises(ValueError, match="Conversation meta id is required"):
            ContextMemoryStore._meta_id(value)

    assert ContextMemoryStore._meta_id("7") == 7


def test_get_returns_empty_state_for_missing_row_and_initializes_db():
    store, _, db = make_store()

    state = store.get(5)

    assert state == {
        "id": None,
        "meta_id": 5,
        "updated_at": 0,
        "last_item_id": 0,
        "generation": 0,
        "revision": 0,
        "content": "",
    }
    db.init.assert_called()


def test_replace_inserts_then_updates_and_increments_revision():
    store, _, _ = make_store()

    assert store.replace(1, "first") == "first"
    first = store.get(1)
    assert first["revision"] == 1
    assert first["generation"] == 0

    assert store.replace(1, "second") == "second"
    second = store.get(1)
    assert second["revision"] == 2
    assert second["content"] == "second"


def test_add_appends_on_new_line_and_empty_addition_is_noop():
    store, _, _ = make_store()
    store.replace(1, "one")

    assert store.add(1, "  two  ") == "one\ntwo"
    revision = store.get(1)["revision"]
    assert store.add(1, "   ") == "one\ntwo"
    assert store.get(1)["revision"] == revision


def test_runtime_summary_insert_tracks_floor_and_generation():
    store, _, _ = make_store()

    saved = store.runtime_summary(1, "summary", expected_revision=0, last_item_id=10)

    assert saved["content"] == "summary"
    assert saved["last_item_id"] == 10
    assert saved["generation"] == 1
    assert saved["revision"] == 1


def test_runtime_summary_is_optimistic_and_only_advances_generation_with_floor():
    store, _, _ = make_store()
    first = store.runtime_summary(1, "one", expected_revision=0, last_item_id=10)

    assert store.runtime_summary(1, "stale", expected_revision=0, last_item_id=20) is None

    same_floor = store.runtime_summary(
        1, "two", expected_revision=first["revision"], last_item_id=5,
    )
    assert same_floor["last_item_id"] == 10
    assert same_floor["generation"] == 1

    advanced = store.runtime_summary(
        1, "three", expected_revision=same_floor["revision"], last_item_id=20,
    )
    assert advanced["last_item_id"] == 20
    assert advanced["generation"] == 2


def test_runtime_summary_rejects_nonzero_revision_for_missing_row():
    store, _, _ = make_store()

    assert store.runtime_summary(1, "x", expected_revision=2, last_item_id=1) is None
    assert store.get(1)["id"] is None


def test_checkpoint_insert_and_update_increment_generation_and_revision():
    store, _, _ = make_store()

    first = store.checkpoint(1, "one", last_item_id=4, expected_revision=0)
    assert first["generation"] == 1
    assert first["revision"] == 1
    assert first["last_item_id"] == 4

    assert store.checkpoint(1, "stale", last_item_id=5, expected_revision=0) is None

    second = store.checkpoint(1, "two", last_item_id=8, expected_revision=1)
    assert second["generation"] == 2
    assert second["revision"] == 2
    assert second["last_item_id"] == 8
    assert second["content"] == "two"


def test_checkpoint_rejects_nonzero_revision_for_missing_row():
    store, _, _ = make_store()

    assert store.checkpoint(9, "x", last_item_id=1, expected_revision=3) is None
